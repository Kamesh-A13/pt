"""
llm_service.py — Ollama LLM integration (replaces Gemini).

Calls Ollama's HTTP API at OLLAMA_BASE_URL (default http://localhost:11434).
Uses OLLAMA_MODEL env var (default llama3.2).
No API keys required.
"""

import json
import logging
import os
import re
import traceback
import time
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException

from app.services.prompts import SYSTEM_PROMPT, build_prompt

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.3"))

# Max retries for JSON generation
MAX_JSON_RETRIES = 2


# ---------------------------------------------------------------------------
# Ollama health check
# ---------------------------------------------------------------------------

def check_ollama_health() -> dict:
    """Check if Ollama is reachable and the configured model is available."""
    try:
        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10)
        if resp.status_code != 200:
            return {
                "ollama_reachable": False,
                "error": f"Ollama returned status {resp.status_code}",
            }

        data = resp.json()
        models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]
        model_available = OLLAMA_MODEL in models or f"{OLLAMA_MODEL}:latest" in [
            m.get("name", "") for m in data.get("models", [])
        ]

        return {
            "ollama_reachable": True,
            "ollama_url": OLLAMA_BASE_URL,
            "model": OLLAMA_MODEL,
            "model_available": model_available,
            "available_models": models,
        }
    except httpx.ConnectError:
        return {
            "ollama_reachable": False,
            "error": f"Cannot connect to Ollama at {OLLAMA_BASE_URL}. "
                     "Is Ollama running? Start it with: ollama serve",
        }
    except Exception as exc:
        return {
            "ollama_reachable": False,
            "error": f"Ollama health check failed: {exc}",
        }


# ---------------------------------------------------------------------------
# JSON extraction helpers
# ---------------------------------------------------------------------------

def _extract_json(raw: str) -> Any:
    """
    Extract JSON from LLM output that may contain markdown fences,
    preamble text, or trailing content.
    """
    # Strip markdown code fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)

    # Try parsing the cleaned text directly
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object or array in the text
    for pattern in [
        r'\{[\s\S]*\}',  # JSON object
        r'\[[\s\S]*\]',  # JSON array
    ]:
        match = re.search(pattern, raw)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                continue

    raise ValueError(f"Could not extract valid JSON from LLM output: {raw[:500]}")


# ---------------------------------------------------------------------------
# RAG context retrieval
# ---------------------------------------------------------------------------

def _get_rag_context(doc_id: str | None, query: str) -> tuple[str | None, list]:
    """
    Retrieve context chunks for RAG.
    Returns (context_string, source_results) tuple.
    source_results contains SearchResult objects with source/page info.
    """
    if not doc_id:
        return None, []
    try:
        from app.services.retriever import retrieve
        from app.services.vector_store import VectorStore
        if not VectorStore.exists(doc_id):
            return None, []

        results = retrieve(doc_id, query, k=RAG_TOP_K)

        # Filter by similarity threshold
        strong_results = [r for r in results if r.score >= SIMILARITY_THRESHOLD]

        if not strong_results:
            return None, []

        # Build context string with source attribution
        parts = []
        total = 0
        max_chars = 6000
        for r in strong_results:
            label = f"[{r.source} p.{r.page}]" if r.page >= 0 else f"[{r.source}]"
            chunk = f"{label}\n{r.text}\n"
            if total + len(chunk) > max_chars:
                remaining = max_chars - total
                if remaining > 100:
                    parts.append(chunk[:remaining])
                break
            parts.append(chunk)
            total += len(chunk)

        return "\n".join(parts), strong_results
    except Exception as exc:
        logger.warning("RAG retrieval failed (%s) — falling back", exc)
        return None, []


# ---------------------------------------------------------------------------
# Core Ollama API call
# ---------------------------------------------------------------------------

def _call_ollama(prompt: str, json_mode: bool = False) -> str:
    """
    Send a prompt to Ollama and return the response text.
    Uses the /api/generate endpoint.
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "options": {
            "temperature": 0.4,
            "top_p": 0.95,
            "top_k": 40,
            "num_predict": 4096,
        },
    }

    if json_mode:
        payload["format"] = "json"

    try:
        logger.info(
            "Calling Ollama model=%s prompt_chars=%d json_mode=%s",
            OLLAMA_MODEL, len(prompt), json_mode,
        )
        start_time = time.time()

        resp = httpx.post(url, json=payload, timeout=OLLAMA_TIMEOUT)
        elapsed = time.time() - start_time

        if resp.status_code == 404:
            raise HTTPException(
                status_code=503,
                detail=f"Model '{OLLAMA_MODEL}' not found in Ollama. "
                       f"Pull it with: ollama pull {OLLAMA_MODEL}",
            )

        if resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Ollama returned status {resp.status_code}: {resp.text[:500]}",
            )

        data = resp.json()
        response_text = data.get("response", "")

        if not response_text.strip():
            raise HTTPException(
                status_code=422,
                detail="Ollama returned an empty response. The model may have "
                       "failed to generate output for this prompt.",
            )

        logger.info(
            "Ollama OK — response_chars=%d elapsed=%.1fs",
            len(response_text), elapsed,
        )
        return response_text

    except HTTPException:
        raise
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to Ollama at {OLLAMA_BASE_URL}. "
                   "Is Ollama running? Start it with: ollama serve",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"Ollama request timed out after {OLLAMA_TIMEOUT}s. "
                   "The model may be loading or the prompt may be too long. "
                   "Try again or increase OLLAMA_TIMEOUT.",
        )
    except Exception as exc:
        logger.error("Ollama API call failed:\n%s", traceback.format_exc())
        raise HTTPException(
            status_code=502,
            detail=f"Ollama API error [{type(exc).__name__}]: {exc}",
        )


# ---------------------------------------------------------------------------
# Public API — same signatures as original Gemini-based service
# ---------------------------------------------------------------------------

def generate_text(prompt: str) -> str:
    """Send a prompt to Ollama and return raw text."""
    return _call_ollama(prompt, json_mode=False)


def generate_json(prompt: str) -> Any:
    """
    Send a prompt to Ollama with JSON mode and return parsed JSON.
    Retries up to MAX_JSON_RETRIES times on malformed output.
    """
    last_error = None
    for attempt in range(1 + MAX_JSON_RETRIES):
        try:
            raw = _call_ollama(prompt, json_mode=True)
            return _extract_json(raw)
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            logger.warning(
                "JSON parse failed (attempt %d/%d): %s",
                attempt + 1, 1 + MAX_JSON_RETRIES, exc,
            )
            if attempt < MAX_JSON_RETRIES:
                continue

    raise HTTPException(
        status_code=500,
        detail=f"LLM returned invalid JSON after {1 + MAX_JSON_RETRIES} attempts. "
               f"Last error: {last_error}",
    )


def generate_summary(
    text: str,
    difficulty: str = "Intermediate",
    doc_id: str | None = None,
    mode: str = "medium",
) -> str:
    """Generate a summary. mode: short / medium / detailed"""
    ctx, _ = _get_rag_context(doc_id, "key concepts core ideas summary")
    source_text = ctx or text

    mode_instruction = {
        "short": "Keep the summary concise — maximum 3 paragraphs, bullet points preferred.",
        "medium": "Provide a balanced summary with key concepts, core ideas, and takeaways.",
        "detailed": "Provide an exhaustive, detailed summary covering all topics, sub-topics, examples, and nuances.",
    }.get(mode, "")

    prompt = build_prompt("summary", source_text, difficulty=difficulty)
    if mode_instruction:
        prompt = f"{mode_instruction}\n\n{prompt}"

    return generate_text(prompt)


def generate_flashcards(
    text: str,
    difficulty: str = "Intermediate",
    num_cards: int = 15,
    doc_id: str | None = None,
) -> dict:
    ctx, _ = _get_rag_context(doc_id, "key terms definitions concepts vocabulary")
    prompt = build_prompt(
        "flashcard", ctx or text,
        difficulty=difficulty, num_cards=num_cards,
    )
    return generate_json(prompt)


def generate_faqs(
    text: str,
    difficulty: str = "Intermediate",
    num_faqs: int = 10,
    doc_id: str | None = None,
) -> dict:
    ctx, _ = _get_rag_context(doc_id, "common questions student misconceptions how why")
    prompt = build_prompt(
        "faq", ctx or text,
        difficulty=difficulty, num_faqs=num_faqs,
    )
    return generate_json(prompt)


def generate_mock_quiz(
    text: str,
    difficulty: str = "Intermediate",
    question_type: str = "mcq",
    num_questions: int = 5,
    doc_id: str | None = None,
) -> dict:
    query_map = {
        "mcq":          "exam questions multiple choice test assessment",
        "short_answer": "short answer exam questions explain describe",
        "long_answer":  "essay questions analysis evaluation deep understanding",
    }
    ctx, _ = _get_rag_context(doc_id, query_map.get(question_type, "exam questions"))
    prompt = build_prompt(
        "mock_quiz", ctx or text,
        difficulty=difficulty,
        question_type=question_type,
        num_questions=num_questions,
    )
    return generate_json(prompt)


def generate_chat_response(
    message: str,
    context: str,
    history: str = "",
    mode: str = "medium",
    sources: list | None = None,
) -> dict:
    """
    Generate a chat response with source attribution.
    mode: short / medium / detailed
    """
    mode_instruction = {
        "short": "Keep your answer brief — 1-2 paragraphs max.",
        "medium": "Keep answers concise (2-4 paragraphs max) unless the student asks for a detailed explanation.",
        "detailed": "Provide a thorough, detailed explanation with examples where appropriate.",
    }.get(mode, "")

    prompt = f"""You are an expert tutor helping a student understand a document.

Document context:
<content>
{context}
</content>

Conversation history:
{history or 'No previous messages.'}

Student's question: {message}

{mode_instruction}

Answer clearly and helpfully based on the document content. If the answer isn't in the document context provided, say clearly: "This information was not found in the uploaded material."
"""

    response_text = generate_text(prompt)

    result = {"response": response_text}
    if sources:
        result["sources"] = [
            {"file": s.source, "page": s.page, "score": round(s.score, 3)}
            for s in sources
        ]

    return result


def generate_study_chat(message: str, subject: str = "general", history: str = "") -> str:
    """
    General study chat (non-document based) for subjects like
    Python, Java, Data Structures, Networks, AI, ML, Maths.
    """
    prompt = f"""You are an expert tutor for {subject}.

Conversation history:
{history or 'No previous messages.'}

Student's question: {message}

Provide a clear, educational answer. Use examples and analogies where helpful.
Structure your response with headings and bullet points when appropriate.
"""
    return generate_text(prompt)


def generate_study_plan(
    subjects: list[str],
    exam_dates: dict[str, str],
    daily_hours: float,
    topics: dict[str, list[str]],
) -> dict:
    """
    Generate a study plan using Ollama.
    Returns a structured plan labeled as AI-generated suggestion.
    """
    subjects_str = ", ".join(subjects)
    dates_str = "\n".join(f"  - {subj}: {date}" for subj, date in exam_dates.items())
    topics_str = "\n".join(
        f"  - {subj}: {', '.join(tops)}"
        for subj, tops in topics.items()
    )

    prompt = f"""Generate a realistic daily study schedule as a JSON object.

Student information:
- Subjects: {subjects_str}
- Exam dates:
{dates_str}
- Available study hours per day: {daily_hours}
- Topics to cover:
{topics_str}

Return ONLY valid JSON with this schema:
{{
  "plan": [
    {{
      "date": "YYYY-MM-DD",
      "sessions": [
        {{
          "subject": "subject name",
          "topic": "specific topic",
          "duration_minutes": 60,
          "priority": "high|medium|low",
          "notes": "brief study tip"
        }}
      ]
    }}
  ],
  "summary": "brief overview of the plan",
  "tips": ["study tip 1", "study tip 2"]
}}

Rules:
- Distribute study time proportionally based on exam proximity
- Include breaks between sessions
- Prioritize subjects with nearer exam dates
- Total daily study time should not exceed {daily_hours} hours
- Generate a plan for the next 14 days
"""
    result = generate_json(prompt)
    # Add AI disclaimer
    if isinstance(result, dict):
        result["disclaimer"] = (
            "This is an AI-generated suggestion based on your inputs. "
            "Adjust the plan based on your actual progress and comfort level."
        )
    return result


def generate_notes_summary(
    text: str,
    summary_type: str = "summary",
    difficulty: str = "Intermediate",
    doc_id: str | None = None,
) -> str:
    """
    Generate different types of notes summaries.
    summary_type: summary / key_points / definitions / important_terms / exam_revision
    """
    ctx, _ = _get_rag_context(doc_id, "key concepts definitions important terms")
    source_text = ctx or text

    type_prompts = {
        "summary": "Generate a comprehensive summary of the following content.",
        "key_points": (
            "Extract the key points from the following content. "
            "Present them as a numbered list with brief explanations."
        ),
        "definitions": (
            "Extract all important terms and their definitions from the following content. "
            "Present each as: **Term** — Definition."
        ),
        "important_terms": (
            "Identify the most important terms, concepts, and vocabulary from the following content. "
            "For each term, provide: the term, a brief definition, and why it's important."
        ),
        "exam_revision": (
            "Create exam revision notes from the following content. Include: "
            "1) Key concepts to remember, 2) Common exam questions, "
            "3) Important formulas/rules, 4) Mnemonics or memory aids where applicable."
        ),
    }

    type_instruction = type_prompts.get(summary_type, type_prompts["summary"])

    prompt = f"""{type_instruction}

Difficulty level: {difficulty}

Content:
<content>
{source_text}
</content>

Provide well-structured output using Markdown formatting.
"""
    return generate_text(prompt)