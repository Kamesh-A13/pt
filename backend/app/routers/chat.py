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
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.middleware.rate_limit import LIMIT_CHAT, limiter
from app.services.llm_service import generate_text
from app.services.retriever import retrieve
from app.services.vector_store import VectorStore

router = APIRouter()

SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.30"))


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