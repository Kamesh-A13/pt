"""
models.py — SQLAlchemy ORM models for structured data.

All models use session_id for data isolation between anonymous users.
"""

import datetime
import uuid

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, Boolean, JSON
from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Task(Base):
    """Task manager — create, edit, complete, delete tasks with deadlines."""
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    deadline = Column(DateTime, nullable=True)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class QuizResult(Base):
    """Store quiz attempt results for progress tracking."""
    __tablename__ = "quiz_results"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, nullable=False, index=True)
    doc_id = Column(String, nullable=True)
    topic = Column(String, default="")
    difficulty = Column(String, default="Intermediate")
    question_type = Column(String, default="mcq")
    total_questions = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    score_percent = Column(Float, default=0.0)
    questions_data = Column(JSON, nullable=True)  # Full quiz Q&A for review
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class StudyPlan(Base):
    """Store generated study plans."""
    __tablename__ = "study_plans"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, nullable=False, index=True)
    subjects = Column(JSON, nullable=True)
    exam_dates = Column(JSON, nullable=True)
    daily_hours = Column(Float, default=4.0)
    topics = Column(JSON, nullable=True)
    plan_data = Column(JSON, nullable=True)  # The generated plan
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class DocumentRecord(Base):
    """Track uploaded documents per session."""
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, nullable=False, index=True)
    doc_id = Column(String, nullable=False, unique=True, index=True)
    filename = Column(String, nullable=False)
    char_count = Column(Integer, default=0)
    word_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
