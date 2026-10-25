"""
planner.py — Study planner endpoints using Ollama.
Generates realistic study schedules based on subjects, exam dates, daily hours, and topics.
"""

from typing import Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import StudyPlan, Task
from app.services.llm_service import generate_study_plan

router = APIRouter()


def get_session_id(
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    session_id: Optional[str] = Query(None),
) -> str:
    sid = x_session_id or session_id or "default_session"
    return sid.strip() or "default_session"


class StudyPlanRequest(BaseModel):
    subjects: List[str] = Field(..., min_length=1)
    exam_dates: Dict[str, str] = Field(default_factory=dict)
    daily_hours: float = Field(default=4.0, ge=0.5, le=16.0)
    topics: Dict[str, List[str]] = Field(default_factory=dict)


@router.post("/planner/generate")
def create_study_plan(
    req: StudyPlanRequest,
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db),
):
    """Generate a realistic daily study schedule with Ollama and persist it."""
    # Call Ollama study planner
    plan_data = generate_study_plan(
        subjects=req.subjects,
        exam_dates=req.exam_dates,
        daily_hours=req.daily_hours,
        topics=req.topics,
    )

    # Save to database
    record = StudyPlan(
        session_id=session_id,
        subjects=req.subjects,
        exam_dates=req.exam_dates,
        daily_hours=req.daily_hours,
        topics=req.topics,
        plan_data=plan_data,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "session_id": record.session_id,
        "subjects": record.subjects,
        "exam_dates": record.exam_dates,
        "daily_hours": record.daily_hours,
        "plan": plan_data,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


@router.get("/planner")
def get_latest_study_plan(
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db),
):
    """Get the most recent study plan for the session."""
    record = (
        db.query(StudyPlan)
        .filter(StudyPlan.session_id == session_id)
        .order_by(StudyPlan.created_at.desc())
        .first()
    )

    if not record:
        return {"plan": None, "message": "No study plan created yet."}

    return {
        "id": record.id,
        "session_id": record.session_id,
        "subjects": record.subjects,
        "exam_dates": record.exam_dates,
        "daily_hours": record.daily_hours,
        "plan": record.plan_data,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


@router.post("/planner/convert-to-tasks")
def convert_plan_to_tasks(
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db),
):
    """
    Extract sessions from the latest study plan and insert them as actionable tasks.
    """
    record = (
        db.query(StudyPlan)
        .filter(StudyPlan.session_id == session_id)
        .order_by(StudyPlan.created_at.desc())
        .first()
    )

    if not record or not record.plan_data:
        raise HTTPException(status_code=404, detail="No study plan found to convert")

    created_tasks = []
    days = record.plan_data.get("plan", [])
    for day in days:
        day_date_str = day.get("date")
        sessions = day.get("sessions", [])
        deadline_dt = None
        if day_date_str:
            try:
                deadline_dt = datetime.strptime(day_date_str, "%Y-%m-%d")
            except ValueError:
                pass

        for s in sessions:
            subject = s.get("subject", "Study")
            topic = s.get("topic", "")
            duration = s.get("duration_minutes", 60)
            notes = s.get("notes", "")

            title = f"[{subject}] {topic} ({duration}m)"
            task = Task(
                session_id=session_id,
                title=title,
                description=f"Planned study session for {subject}. Notes: {notes}",
                deadline=deadline_dt,
                completed=False,
            )
            db.add(task)
            created_tasks.append(title)

    db.commit()
    return {
        "message": f"Successfully created {len(created_tasks)} tasks from study plan",
        "tasks_created": len(created_tasks),
    }


@router.delete("/planner")
def delete_study_plans(
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db),
):
    """Delete all study plans for the current session."""
    deleted = db.query(StudyPlan).filter(StudyPlan.session_id == session_id).delete()
    db.commit()
    return {"message": f"Deleted {deleted} study plan(s)"}
