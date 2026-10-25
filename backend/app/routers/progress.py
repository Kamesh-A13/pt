"""
progress.py — Real progress tracking and analytics from SQLite storage.
Strict rule: Only return real stored data; never show fake or fabricated numbers.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Task, QuizResult, StudyPlan, DocumentRecord

router = APIRouter()


def get_session_id(
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    session_id: Optional[str] = Query(None),
) -> str:
    sid = x_session_id or session_id or "default_session"
    return sid.strip() or "default_session"


class RecordQuizRequest(BaseModel):
    doc_id: Optional[str] = None
    topic: Optional[str] = "General"
    difficulty: Optional[str] = "Intermediate"
    question_type: Optional[str] = "mcq"
    total_questions: int = Field(..., ge=1)
    correct_answers: int = Field(..., ge=0)
    questions_data: Optional[List[Dict[str, Any]]] = None


@router.post("/quiz/record")
def record_quiz_result(
    req: RecordQuizRequest,
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db),
):
    """
    Record real quiz score in SQLite. Scored in code (no AI fabrication).
    """
    if req.correct_answers > req.total_questions:
        raise HTTPException(status_code=400, detail="correct_answers cannot exceed total_questions")

    score_percent = round((req.correct_answers / req.total_questions) * 100, 1)

    result = QuizResult(
        session_id=session_id,
        doc_id=req.doc_id,
        topic=req.topic or "General",
        difficulty=req.difficulty or "Intermediate",
        question_type=req.question_type or "mcq",
        total_questions=req.total_questions,
        correct_answers=req.correct_answers,
        score_percent=score_percent,
        questions_data=req.questions_data,
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    return {
        "id": result.id,
        "session_id": result.session_id,
        "score_percent": result.score_percent,
        "correct_answers": result.correct_answers,
        "total_questions": result.total_questions,
        "created_at": result.created_at.isoformat() if result.created_at else None,
    }


@router.get("/progress")
def get_progress_overview(
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db),
):
    """
    Get aggregated progress reports based strictly on stored database records.
    Returns has_data=False when no records exist.
    """
    # 1. Tasks analytics
    tasks = db.query(Task).filter(Task.session_id == session_id).all()
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.completed)
    pending_tasks = total_tasks - completed_tasks
    task_completion_rate = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0.0

    # 2. Quiz analytics
    quizzes = (
        db.query(QuizResult)
        .filter(QuizResult.session_id == session_id)
        .order_by(QuizResult.created_at.desc())
        .all()
    )
    total_quizzes = len(quizzes)
    average_quiz_score = (
        round(sum(q.score_percent for q in quizzes) / total_quizzes, 1)
        if total_quizzes > 0
        else 0.0
    )
    highest_quiz_score = (
        round(max(q.score_percent for q in quizzes), 1)
        if total_quizzes > 0
        else 0.0
    )

    # Topic-wise performance
    topics_map: Dict[str, List[float]] = {}
    for q in quizzes:
        t = q.topic or "General"
        if t not in topics_map:
            topics_map[t] = []
        topics_map[t].append(q.score_percent)

    topic_performance = [
        {
            "topic": t,
            "attempts": len(scores),
            "average_score": round(sum(scores) / len(scores), 1),
            "highest_score": round(max(scores), 1),
        }
        for t, scores in topics_map.items()
    ]

    # 3. Documents
    docs_count = (
        db.query(DocumentRecord)
        .filter(DocumentRecord.session_id == session_id)
        .count()
    )

    # 4. Study plans
    plans_count = (
        db.query(StudyPlan)
        .filter(StudyPlan.session_id == session_id)
        .count()
    )

    has_data = bool(total_tasks > 0 or total_quizzes > 0 or docs_count > 0 or plans_count > 0)

    recent_quizzes = [
        {
            "id": q.id,
            "topic": q.topic,
            "difficulty": q.difficulty,
            "score_percent": q.score_percent,
            "correct_answers": q.correct_answers,
            "total_questions": q.total_questions,
            "created_at": q.created_at.isoformat() if q.created_at else None,
        }
        for q in quizzes[:5]
    ]

    return {
        "has_data": has_data,
        "tasks": {
            "total": total_tasks,
            "completed": completed_tasks,
            "pending": pending_tasks,
            "completion_rate": task_completion_rate,
        },
        "quizzes": {
            "total_taken": total_quizzes,
            "average_score": average_quiz_score,
            "highest_score": highest_quiz_score,
            "recent": recent_quizzes,
            "topic_performance": topic_performance,
        },
        "activity": {
            "documents_uploaded": docs_count,
            "plans_generated": plans_count,
        },
    }
