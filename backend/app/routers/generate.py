"""
generate.py — LLM-powered generation endpoints with rate limiting,
summarization modes, quiz generation (doc/topic), and algorithmic quiz scoring.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.rate_limit import LIMIT_GENERATE, limiter
from app.models import QuizResult
from app.services.llm_service import (
    generate_faqs,
    generate_flashcards,
    generate_json,
    generate_mock_quiz,
    generate_summary,
    generate_text,
)

router = APIRouter()

DOC_STORE: dict[str, str] = {}


def get_session_id(
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    session_id: Optional[str] = Query(None),
) -> str:
    sid = x_session_id or session_id or "default_session"
    return sid.strip() or "default_session"


def _get_text(doc_id: Optional[str] = None, fallback_text: Optional[str] = None) -> str:
    if doc_id:
        text = DOC_STORE.get(doc_id)
        if text:
            return text
    if fallback_text and fallback_text.strip():
        return fallback_text.strip()
    if doc_id:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{doc_id}' not found. Please upload it first or provide topic text.",
        )
    raise HTTPException(status_code=400, detail="Either doc_id or text/topic must be provided.")


class SummarizeRequest(BaseModel):
    doc_id: Optional[str] = None
    text: Optional[str] = None
    topic: Optional[str] = None
    difficulty: str = Field(default="Intermediate")
    mode: str = Field(
        default="medium",
        description="short, medium, detailed, key_points, definitions, important_terms, exam_revision",
    )


class FlashcardRequest(BaseModel):
    doc_id: Optional[str] = None
    text: Optional[str] = None
    difficulty: str = "Intermediate"
    num_cards: int = Field(default=15, ge=3, le=40)


class FAQRequest(BaseModel):
    doc_id: Optional[str] = None
    text: Optional[str] = None
    difficulty: str = "Intermediate"
    num_faqs: int = Field(default=10, ge=3, le=20)


class MockQuizRequest(BaseModel):
    doc_id: Optional[str] = None
    topic: Optional[str] = None
    text: Optional[str] = None
    difficulty: str = "Intermediate"
    question_type: str = Field(default="mcq")
    num_questions: int = Field(default=5, ge=1, le=20)


class QuizAnswerItem(BaseModel):
    question_id: int | str
    selected_option: str  # e.g. "A", "B", "C", "D"


class ScoreQuizRequest(BaseModel):
    doc_id: Optional[str] = None
    topic: Optional[str] = "General"
    difficulty: Optional[str] = "Intermediate"
    questions: List[Dict[str, Any]]
    answers: List[QuizAnswerItem]


@router.post("/summarize")
@limiter.limit(LIMIT_GENERATE)
async def summarize(request: Request, req: SummarizeRequest):
    """
    Generate notes summary with multiple selectable modes:
    short, medium, detailed, key_points, definitions, important_terms, exam_revision.
    """
    input_text = ""
    if req.doc_id:
        input_text = _get_text(req.doc_id, req.text)
    elif req.text:
        input_text = req.text
    elif req.topic:
        input_text = f"Subject / Topic: {req.topic}"
    else:
        raise HTTPException(status_code=400, detail="Provide doc_id, text, or topic.")

    mode = req.mode.lower().strip()

    # Specialized prompt additions based on mode
    mode_prompts = {
        "short": "Create a high-impact, brief summary (under 3 paragraphs or concise bullet points).",
        "medium": "Provide a well-rounded summary covering key concepts, core principles, and practical takeaways.",
        "detailed": "Provide an in-depth, thorough academic summary covering all concepts, nuances, and edge cases.",
        "key_points": "Extract all essential Key Points as an organized, numbered list of major concepts and takeaways.",
        "definitions": "Extract all definitions and core terminology into a clear Glossary format: Term: Definition.",
        "important_terms": "List all important technical terms, keywords, and domain concepts with brief 1-line explanations.",
        "exam_revision": "Generate high-yield Exam Revision Notes: critical formulas, core facts, must-remember concepts, and common pitfalls.",
    }

    instruction = mode_prompts.get(mode, mode_prompts["medium"])

    prompt = f"""{instruction}

Content to summarize:
<content>
{input_text}
</content>

Difficulty: {req.difficulty}

Summary:"""

    summary = generate_text(prompt)

    return {
        "doc_id": req.doc_id,
        "difficulty": req.difficulty,
        "mode": req.mode,
        "summary": summary,
    }


@router.post("/flashcards")
@limiter.limit(LIMIT_GENERATE)
async def flashcards(request: Request, req: FlashcardRequest):
    input_text = _get_text(req.doc_id, req.text)
    result = generate_flashcards(
        input_text,
        difficulty=req.difficulty,
        num_cards=req.num_cards,
        doc_id=req.doc_id,
    )
    return {"doc_id": req.doc_id, "difficulty": req.difficulty, **result}


@router.post("/faq")
@limiter.limit(LIMIT_GENERATE)
async def faq(request: Request, req: FAQRequest):
    input_text = _get_text(req.doc_id, req.text)
    result = generate_faqs(
        input_text,
        difficulty=req.difficulty,
        num_faqs=req.num_faqs,
        doc_id=req.doc_id,
    )
    return {"doc_id": req.doc_id, "difficulty": req.difficulty, **result}


@router.post("/mock-quiz")
@limiter.limit(LIMIT_GENERATE)
async def mock_quiz(request: Request, req: MockQuizRequest):
    """
    Generate an exam quiz (MCQs) from an uploaded document OR a typed topic.
    """
    valid_types = {"mcq", "short_answer", "long_answer"}
    if req.question_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid question_type. Must be one of: {valid_types}",
        )

    # Document-based or Topic-based
    if req.doc_id:
        text = _get_text(req.doc_id, req.text)
        result = generate_mock_quiz(
            text,
            difficulty=req.difficulty,
            question_type=req.question_type,
            num_questions=req.num_questions,
            doc_id=req.doc_id,
        )
    elif req.topic or req.text:
        topic_text = req.topic or req.text
        # Generate directly from topic prompt in JSON mode
        prompt = f"""Generate {req.num_questions} high-quality {req.question_type.upper()} questions about: {topic_text}
Difficulty level: {req.difficulty}

Return ONLY valid JSON with this exact schema:
{{
  "questions": [
    {{
      "id": 1,
      "type": "mcq",
      "question": "<the question stem>",
      "options": {{
        "A": "<option A>",
        "B": "<option B>",
        "C": "<option C>",
        "D": "<option D>"
      }},
      "correct_answer": "A",
      "explanation": "<detailed explanation of why this answer is correct>"
    }}
  ]
}}
"""
        result = generate_json(prompt)
    else:
        raise HTTPException(status_code=400, detail="Please provide either doc_id or topic.")

    return {
        "doc_id": req.doc_id,
        "topic": req.topic or "Document Review",
        "difficulty": req.difficulty,
        "question_type": req.question_type,
        **result,
    }


@router.post("/quiz/score")
def score_quiz(
    req: ScoreQuizRequest,
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db),
):
    """
    Algorithmic quiz evaluation (in Python code, NO AI hallucination/fabrication).
    Compares selected options against correct_answer keys.
    Computes score and stores real results in SQLite.
    """
    if not req.questions:
        raise HTTPException(status_code=400, detail="Questions list cannot be empty.")

    answers_map = {str(a.question_id): a.selected_option.strip().upper() for a in req.answers}

    graded_questions = []
    correct_count = 0
    total = len(req.questions)

    for q in req.questions:
        qid = str(q.get("id"))
        user_choice = answers_map.get(qid, "")
        correct_choice = str(q.get("correct_answer", "")).strip().upper()

        is_correct = bool(user_choice and user_choice == correct_choice)
        if is_correct:
            correct_count += 1

        graded_questions.append({
            "id": q.get("id"),
            "question": q.get("question"),
            "options": q.get("options", {}),
            "user_answer": user_choice,
            "correct_answer": correct_choice,
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
        })

    score_percent = round((correct_count / total * 100), 1) if total > 0 else 0.0

    # Store real attempt in SQLite
    result_record = QuizResult(
        session_id=session_id,
        doc_id=req.doc_id,
        topic=req.topic or "General",
        difficulty=req.difficulty or "Intermediate",
        question_type="mcq",
        total_questions=total,
        correct_answers=correct_count,
        score_percent=score_percent,
        questions_data=graded_questions,
    )
    db.add(result_record)
    db.commit()
    db.refresh(result_record)

    return {
        "result_id": result_record.id,
        "total_questions": total,
        "correct_answers": correct_count,
        "score_percent": score_percent,
        "graded_questions": graded_questions,
        "created_at": result_record.created_at.isoformat() if result_record.created_at else None,
    }