"""
chat.py — Document RAG chat and general subject study chat.

Features:
  - Answers based strictly on retrieved chunks for document chat
  - Weak retrieval detection with similarity threshold -> "This information was not found in the uploaded material"
  - Source attribution (filename and page numbers)
  - Answer length modes: short / medium / detailed
  - General study chat mode (non-document) for subjects like Python, Java, Data Structures, Networks, AI, ML, Maths
"""

import os
import re
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.middleware.rate_limit import LIMIT_CHAT, limiter
from app.services.llm_service import generate_text
from app.services.retriever import retrieve
from app.services.vector_store import VectorStore

router = APIRouter()

SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.30"))


def _detect_conversational_intent(msg: str) -> Optional[str]:
    m = msg.lower().strip()
    # Greetings
    if re.search(r"^(hi|hello|hey|greetings|good\s+(morning|afternoon|evening))\b", m) and len(m.split()) <= 6:
        return "greeting"
    # Time to complete
    if any(phrase in m for phrase in [
        "how much time", "how long will it take", "how long to", "time will it take",
        "time to complete", "completion time", "how many hours", "time required",
        "how long does it take", "how much time to complete", "how much time to finish"
    ]):
        return "time_estimate"
    # How to study simple
    if any(phrase in m for phrase in [
        "how to study it simple", "how to study simple", "how to study simply",
        "how should i study", "simple way to study", "easy way to study",
        "how to study this", "how to learn simply", "study it simple",
        "explain simply how to study", "best way to study", "how to study"
    ]):
        return "study_simple"
    return None


def get_session_id(
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    session_id: Optional[str] = Query(None),
) -> str:
    sid = x_session_id or session_id or "default_session"
    return sid.strip() or "default_session"


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    doc_id: Optional[str] = None
    subject: Optional[str] = None  # e.g. Python, Java, Data Structures, Networks, AI, ML, Maths
    message: str = Field(..., min_length=1)
    history: List[dict] = []
    mode: str = Field(default="medium", description="short, medium, detailed")


DOC_RAG_PROMPT = """You are an academic study assistant answering questions strictly based on the uploaded document excerpts.

Strict Constraints:
1. Answer using ONLY facts directly mentioned in the context below.
2. If the context does not contain the answer, respond EXACTLY with:
"This information was not found in the uploaded material."
3. Do not speculate or invent information outside the document context.
4. Reference the source file and page numbers when stating key facts.

Length Mode: {mode_instruction}

Context:
<content>
{context}
</content>

Conversation history:
{history}

Student's Question: {message}

Answer:"""


GENERAL_STUDY_PROMPT = """You are an expert tutor in Computer Science, Engineering, and Mathematics, specializing in subjects such as Python, Java, Data Structures & Algorithms, Computer Networks, Operating Systems, Artificial Intelligence, Machine Learning, and Mathematics.

Subject: {subject}
Length Mode: {mode_instruction}

Provide a clear, accurate, educational explanation suitable for a student. Use code examples, analogies, and step-by-step reasoning where helpful.

Conversation history:
{history}

Student's Question: {message}

Answer:"""


def _get_mode_instruction(mode: str) -> str:
    m = mode.lower().strip()
    if m == "short":
        return "Keep the answer concise, direct, and under 2 short paragraphs or bullet points."
    elif m == "detailed":
        return "Provide an exhaustive, in-depth explanation covering theory, examples, definitions, and edge cases."
    return "Provide a clear, balanced explanation of 2 to 4 paragraphs with key concepts highlighted."


@router.post("/chat")
@limiter.limit(LIMIT_CHAT)
async def chat_endpoint(
    request: Request,
    req: ChatRequest,
    session_id: str = Depends(get_session_id),
):
    """
    Handle document Q&A (RAG) and general subject study chat with selectable modes.
    """
    mode_instruction = _get_mode_instruction(req.mode)

    history_str = ""
    for msg in req.history[-6:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        history_str += f"{role.capitalize()}: {content}\n"
    if not history_str:
        history_str = "No prior messages."

    # --------------------------------------------------------------------------
    # Check for Conversational / Meta-Study Intents (Greetings, Time, Methods)
    # --------------------------------------------------------------------------
    intent = _detect_conversational_intent(req.message)
    if intent == "greeting":
        doc_note = f"Your document '{req.doc_id}' is loaded and ready for questions." if req.doc_id else "I am ready to help you study any subject or uploaded notes."
        return {
            "response": (
                f"👋 **Hello! Welcome to StudyOS AI!**\n\n"
                f"{doc_note}\n\n"
                f"Here are a few quick ways we can learn together:\n"
                f"• ⏱️ Ask *\"How much time will it take to complete?\"* for an estimated study schedule.\n"
                f"• 💡 Ask *\"How to study it simple?\"* for an easy step-by-step study method.\n"
                f"• 📝 Ask for a summary or key takeaways from the material.\n"
                f"• 🎯 Take a quick practice quiz in the **Quiz Generator** tab.\n\n"
                f"What would you like to focus on right now?"
            ),
            "doc_id": req.doc_id,
            "sources": [],
            "mode": req.mode,
        }

    if intent == "time_estimate":
        target = f"for this material ({req.doc_id})" if req.doc_id else f"for {req.subject or 'this topic'}"
        return {
            "response": (
                f"⏱️ **Estimated Study & Completion Time {target}:**\n\n"
                "Here is an efficient, research-backed study breakdown to master this without burnout:\n\n"
                "| Phase | Recommended Activity | Estimated Time |\n"
                "|---|---|---|\n"
                "| **1. The Quick Skim** | Read headings, summaries, and key bold terms | **15 – 20 mins** |\n"
                "| **2. Focused Learning** | Deep reading in 25-minute Pomodoro sprints | **45 – 60 mins** |\n"
                "| **3. Active Recall** | Take a 5-question test in the **Quiz** tab | **15 – 20 mins** |\n"
                "| **4. Mistake Review** | Review missed questions & simplify difficult points | **15 – 20 mins** |\n\n"
                "💡 **Total Study Time:** **~1.5 to 2.5 hours** for thorough understanding.\n\n"
                "**Pro-tip:** Don't cram in one sitting! Take a 5-minute break every 25 minutes to lock facts into long-term memory."
            ),
            "doc_id": req.doc_id,
            "sources": [],
            "mode": req.mode,
        }

    if intent == "study_simple":
        return {
            "response": (
                "📚 **How to Study This in a Simple & Effective Way:**\n\n"
                "You don't need to read and memorize everything at once. Use this proven **4-Step Simple Method**:\n\n"
                "1. 🗺️ **Step 1: 10-Minute Big Picture Skim**\n"
                "   - Flip through the document or topic headings. Build a quick mental map of the core ideas before diving into details.\n\n"
                "2. 🍅 **Step 2: 25-Minute Focused Bites (Pomodoro)**\n"
                "   - Read one concept at a time. After each section, ask yourself: *\"What is the one main takeaway here?\"* Write down one sentence in your own words.\n\n"
                "3. 🧠 **Step 3: Test Yourself Early (Active Recall)**\n"
                "   - Passive reading gives a false sense of confidence. Go to the **Quiz Generator** tab and test yourself immediately. Mistakes show you what to re-read.\n\n"
                "4. 👶 **Step 4: The Feynman Simplification (ELI5)**\n"
                "   - Explain the concept as if you were explaining it to a 10-year-old. If you get stuck on complex words, ask me: *\"Explain [concept] in simple terms!\"*\n\n"
                "Would you like me to explain the core concept simply right now?"
            ),
            "doc_id": req.doc_id,
            "sources": [],
            "mode": req.mode,
        }

    # --------------------------------------------------------------------------
    # Case A: Document Chat (RAG)
    # --------------------------------------------------------------------------
    if req.doc_id:
        # Check if vector store exists
        if not VectorStore.exists(req.doc_id, session_id=session_id):
            # Also check if text is in DOC_STORE
            from app.routers.generate import DOC_STORE
            if req.doc_id not in DOC_STORE:
                raise HTTPException(
                    status_code=404,
                    detail=f"Document '{req.doc_id}' not found. Please upload it first.",
                )

        # Retrieve relevant chunks
        matched_chunks = []
        sources = []
        try:
            results = retrieve(req.doc_id, req.message, k=5, session_id=session_id)
            # Filter by similarity threshold
            for r in results:
                if r.score >= SIMILARITY_THRESHOLD:
                    matched_chunks.append(f"[{r.source} p.{r.page}]\n{r.text}")
                    sources.append({
                        "source": r.source,
                        "page": r.page,
                        "score": round(float(r.score), 4),
                    })
        except Exception:
            pass

        # Weak retrieval check
        if not matched_chunks:
            return {
                "response": "This information was not found in the uploaded material.",
                "doc_id": req.doc_id,
                "sources": [],
                "mode": req.mode,
            }

        context_str = "\n\n".join(matched_chunks)[:6000]

        prompt = DOC_RAG_PROMPT.format(
            context=context_str,
            history=history_str,
            message=req.message,
            mode_instruction=mode_instruction,
        )

        response = generate_text(prompt)

        return {
            "response": response,
            "doc_id": req.doc_id,
            "sources": sources,
            "mode": req.mode,
        }

    # --------------------------------------------------------------------------
    # Case B: General Subject Study Chat
    # --------------------------------------------------------------------------
    subject = req.subject or "Computer Science / General Study"
    prompt = GENERAL_STUDY_PROMPT.format(
        subject=subject,
        history=history_str,
        message=req.message,
        mode_instruction=mode_instruction,
    )

    response = generate_text(prompt)
    return {
        "response": response,
        "doc_id": None,
        "subject": subject,
        "sources": [],
        "mode": req.mode,
    }