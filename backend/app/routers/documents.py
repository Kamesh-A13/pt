"""
documents.py — Document upload, listing, and deletion endpoints.
Includes:
  - Document validation (file type, file size, empty files, corrupt PDFs)
  - Per-session document and vector index isolation
  - Document deletion endpoint
  - "Delete all my data" endpoint
"""

import logging
from typing import Optional
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Header, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DocumentRecord, QuizResult, StudyPlan, Task
from app.services.parser import parse_document
from app.services.retriever import delete_document, delete_session_documents, ingest_document
from app.utils.file_utils import validate_file

logger = logging.getLogger(__name__)
router = APIRouter()


def get_session_id(
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    session_id: Optional[str] = Query(None),
) -> str:
    sid = x_session_id or session_id or "default_session"
    return sid.strip() or "default_session"


def _ingest_background(doc_id: str, filename: str, file_bytes: bytes, session_id: str) -> None:
    """Background task: embed chunks and persist FAISS index with session isolation."""
    try:
        n = ingest_document(doc_id, filename, file_bytes, session_id=session_id)
        logger.info("Background ingest complete: %d chunks for doc_id=%s (session=%s)", n, doc_id, session_id)
    except Exception as exc:
        logger.error("Background ingest failed for doc_id=%s: %s", doc_id, exc)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db),
):
    """
    Accept a PDF, DOCX, or PPTX file.
    Validates file type, size, non-emptiness, and file integrity (corrupt PDFs/DOCX).
    Stores text in DOC_STORE and SQLite, and kicks off background FAISS embedding.
    """
    file_bytes = await file.read()

    # Full validation: extension, max size, empty files, corrupt PDFs/documents
    validate_file(file.filename, len(file_bytes), file_bytes=file_bytes)

    extracted_text = parse_document(file.filename, file_bytes)

    if not extracted_text.strip():
        raise HTTPException(
            status_code=422,
            detail="No readable text found in the uploaded file.",
        )

    doc_id = str(uuid.uuid4())

    # Cache text in memory for fast retrieval
    from app.routers.generate import DOC_STORE
    DOC_STORE[doc_id] = extracted_text

    # Record in database for session tracking
    doc_record = DocumentRecord(
        session_id=session_id,
        doc_id=doc_id,
        filename=file.filename,
        char_count=len(extracted_text),
        word_count=len(extracted_text.split()),
    )
    db.add(doc_record)
    db.commit()

    # Trigger background indexing
    background_tasks.add_task(
        _ingest_background, doc_id, file.filename, file_bytes, session_id
    )

    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "char_count": len(extracted_text),
        "word_count": len(extracted_text.split()),
        "preview": extracted_text[:500],
        "full_text": extracted_text,
    }


@router.get("/documents")
def list_documents(
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db),
):
    """List all documents uploaded by the current session."""
    records = (
        db.query(DocumentRecord)
        .filter(DocumentRecord.session_id == session_id)
        .order_by(DocumentRecord.created_at.desc())
        .all()
    )

    return {
        "documents": [
            {
                "id": r.id,
                "doc_id": r.doc_id,
                "filename": r.filename,
                "char_count": r.char_count,
                "word_count": r.word_count,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]
    }


@router.delete("/documents/{doc_id}")
def delete_single_document(
    doc_id: str,
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db),
):
    """
    Delete a document from memory, database records, and FAISS index.
    """
    from app.routers.generate import DOC_STORE
    DOC_STORE.pop(doc_id, None)

    # Delete disk index
    delete_document(doc_id, session_id=session_id)

    # Delete DB records
    deleted = (
        db.query(DocumentRecord)
        .filter(DocumentRecord.doc_id == doc_id, DocumentRecord.session_id == session_id)
        .delete()
    )
    db.commit()

    if not deleted:
        # Also check without session_id filter if it was a default doc
        db.query(DocumentRecord).filter(DocumentRecord.doc_id == doc_id).delete()
        db.commit()

    return {"message": "Document and its index deleted successfully", "doc_id": doc_id}


@router.delete("/data")
def delete_all_user_data(
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db),
):
    """
    'Delete all my data' endpoint.
    Completely purges all tasks, quiz results, study plans, documents,
    and FAISS index directories for the requesting session.
    """
    # 1. Purge FAISS index files for this session
    delete_session_documents(session_id)

    # 2. Clear memory store for session documents
    from app.routers.generate import DOC_STORE
    session_docs = db.query(DocumentRecord).filter(DocumentRecord.session_id == session_id).all()
    for d in session_docs:
        DOC_STORE.pop(d.doc_id, None)

    # 3. Purge SQLite records for this session
    del_tasks = db.query(Task).filter(Task.session_id == session_id).delete()
    del_quizzes = db.query(QuizResult).filter(QuizResult.session_id == session_id).delete()
    del_plans = db.query(StudyPlan).filter(StudyPlan.session_id == session_id).delete()
    del_docs = db.query(DocumentRecord).filter(DocumentRecord.session_id == session_id).delete()

    db.commit()

    return {
        "message": "All session data and vector indices have been deleted.",
        "purged": {
            "tasks": del_tasks,
            "quizzes": del_quizzes,
            "plans": del_plans,
            "documents": del_docs,
        },
    }
