"""
tasks.py — Task management endpoints with deadlines and status tracking.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Task

router = APIRouter()


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    deadline: Optional[datetime] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    completed: Optional[bool] = None


def get_session_id(
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    session_id: Optional[str] = Query(None),
) -> str:
    sid = x_session_id or session_id or "default_session"
    return sid.strip() or "default_session"


@router.get("/tasks")
def list_tasks(
    session_id: str = Depends(get_session_id),
    status: Optional[str] = Query(None, description="all, pending, completed, upcoming, overdue"),
    db: Session = Depends(get_db),
):
    """List tasks for the current anonymous session."""
    query = db.query(Task).filter(Task.session_id == session_id)
    now = datetime.utcnow()

    if status == "completed":
        query = query.filter(Task.completed == True)
    elif status == "pending":
        query = query.filter(Task.completed == False)
    elif status == "overdue":
        query = query.filter(Task.completed == False, Task.deadline != None, Task.deadline < now)
    elif status == "upcoming":
        query = query.filter(Task.completed == False, Task.deadline != None, Task.deadline >= now)

    tasks = query.order_by(Task.deadline.asc().nullslast(), Task.created_at.desc()).all()

    # Calculate statistics
    all_tasks = db.query(Task).filter(Task.session_id == session_id).all()
    total = len(all_tasks)
    completed_count = sum(1 for t in all_tasks if t.completed)
    overdue_count = sum(1 for t in all_tasks if not t.completed and t.deadline and t.deadline < now)
    upcoming_count = sum(1 for t in all_tasks if not t.completed and t.deadline and t.deadline >= now)

    return {
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "deadline": t.deadline.isoformat() if t.deadline else None,
                "completed": t.completed,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "is_overdue": bool(not t.completed and t.deadline and t.deadline < now),
            }
            for t in tasks
        ],
        "stats": {
            "total": total,
            "completed": completed_count,
            "pending": total - completed_count,
            "overdue": overdue_count,
            "upcoming": upcoming_count,
        },
    }


@router.post("/tasks")
def create_task(
    task_in: TaskCreate,
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db),
):
    """Create a new task."""
    if not task_in.title.strip():
        raise HTTPException(status_code=400, detail="Task title cannot be empty")

    task = Task(
        session_id=session_id,
        title=task_in.title.strip(),
        description=task_in.description or "",
        deadline=task_in.deadline,
        completed=False,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "deadline": task.deadline.isoformat() if task.deadline else None,
        "completed": task.completed,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


@router.put("/tasks/{task_id}")
def update_task(
    task_id: str,
    task_in: TaskUpdate,
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db),
):
    """Update an existing task."""
    task = db.query(Task).filter(Task.id == task_id, Task.session_id == session_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_in.title is not None:
        if not task_in.title.strip():
            raise HTTPException(status_code=400, detail="Task title cannot be empty")
        task.title = task_in.title.strip()

    if task_in.description is not None:
        task.description = task_in.description

    if task_in.deadline is not None:
        task.deadline = task_in.deadline

    if task_in.completed is not None:
        task.completed = task_in.completed
        task.completed_at = datetime.utcnow() if task_in.completed else None

    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)

    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "deadline": task.deadline.isoformat() if task.deadline else None,
        "completed": task.completed,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


@router.patch("/tasks/{task_id}/toggle")
def toggle_task(
    task_id: str,
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db),
):
    """Toggle completed status of a task."""
    task = db.query(Task).filter(Task.id == task_id, Task.session_id == session_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.completed = not task.completed
    task.completed_at = datetime.utcnow() if task.completed else None
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)

    return {
        "id": task.id,
        "completed": task.completed,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: str,
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db),
):
    """Delete a task."""
    task = db.query(Task).filter(Task.id == task_id, Task.session_id == session_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()
    return {"message": "Task deleted successfully", "id": task_id}
