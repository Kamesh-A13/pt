"""
main.py — FastAPI application entry point.
v3: Ollama LLM, SQLite storage, anonymous sessions, no Google SSO.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.routers import documents
from app.routers import generate as generate_router
from app.routers.process import router as process_router
from app.routers.chat import router as chat_router
from app.routers.tasks import router as tasks_router
from app.routers.planner import router as planner_router
from app.routers.progress import router as progress_router
from app.middleware.rate_limit import limiter, rate_limit_handler
from app.database import init_db
from app.services.llm_service import check_ollama_health

from dotenv import load_dotenv
import os

load_dotenv()

# Initialize database tables on startup
init_db()

# fastapi app instance
app = FastAPI(
    title="StudyOS — AI-Powered Student Assistant",
    description="Local LLM-powered study assistant with RAG, quizzes, task management, and study planning. Uses Ollama (no API keys).",
    version="3.0.0",
)

# ── Rate limiting ────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# ── CORS ─────────────────────────────────────────────────────────────────────
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(documents.router,           prefix="/api", tags=["documents"])
app.include_router(generate_router.router,     prefix="/api", tags=["generate"])
app.include_router(process_router,             prefix="/api", tags=["process"])
app.include_router(process_router,             tags=["process"])
app.include_router(chat_router,                prefix="/api", tags=["chat"])
app.include_router(tasks_router,               prefix="/api", tags=["tasks"])
app.include_router(planner_router,             prefix="/api", tags=["planner"])
app.include_router(progress_router,            prefix="/api", tags=["progress"])


@app.get("/health")
def health_check():
    ollama_status = check_ollama_health()
    return {
        "status": "ok",
        "message": "StudyOS API is running",
        "version": "3.0.0",
        "llm_provider": "ollama",
        "features": ["rag", "chat", "quiz", "tasks", "planner", "progress"],
        "ollama": ollama_status,
    }