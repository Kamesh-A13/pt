# Architecture Decisions & Analysis

## What Exists in the Original StudyOS Repo

### Backend (FastAPI)
- **Document upload**: `/api/upload` — parses PDF/DOCX/PPTX, stores text in an in-memory dict (`DOC_STORE`), triggers background FAISS indexing
- **Content generation**: `/api/summarize`, `/api/flashcards`, `/api/faq`, `/api/mock-quiz` — all powered by Google Gemini
- **RAG chat**: `/api/chat` — retrieves relevant chunks from FAISS, injects context into prompt
- **File processing**: `/api/process` — extracts and chunks text (debugging endpoint)
- **Auth**: Google OAuth 2.0 SSO with JWT tokens
- **Rate limiting**: slowapi middleware
- **LLM Service**: Tightly coupled to `google-generativeai` SDK (Gemini)
- **Embeddings**: SentenceTransformers (`all-MiniLM-L6-v2`, 384-dim)
- **Vector store**: FAISS (`IndexFlatIP`) with per-document indices
- **Chunking**: Sliding-window chunker in `retriever.py` (350 words, 50 overlap)
- **Prompts**: Centralized prompt templates with difficulty calibration
- **Tests**: `test_parser.py`, `test_processing.py`, `test_retriever.py` (chunking + retrieval integration)
- **Sample files**: `sample.pdf`, `sample.docx`, `sample.pptx` in `tests/sample_files/`

### Frontend (React 19 + Vite + Tailwind)
- Pages: Login, AuthCallback, NotebooksList, Notebook, Summary, Flashcards, FAQ, Quiz, (unused: History, Metrics, Register, Results, Upload)
- Components: FileUpload, FlashCard, Navbar, ProtectedRoute, ResultsTabs, SummaryDisplay, FAQDisplay, ui/*
- Context: AuthContext (Google SSO), NotebookContext (localStorage)
- API Service: Axios client with Bearer token interceptor

### CI/CD
- `github/workflows/frontend-ci.yml` — note: folder is `github/` not `.github/`, so the workflow will never run on GitHub Actions

### Docker
- `docker-compose.yml` with backend + frontend services
- Backend and frontend Dockerfiles exist but are empty (0 bytes)

## What Is Missing / Needs Work

### Critical
1. **LLM provider**: Currently hardcoded to Gemini with `GOOGLE_API_KEY` required at import time (crashes if unset). Must replace with Ollama.
2. **No database**: All data (docs, quiz results, tasks) is in-memory dicts. Lost on restart.
3. **No data isolation**: All users share the same `DOC_STORE` and FAISS index root.
4. **CI workflow path**: `github/` should be `.github/` for GitHub Actions to discover it.
5. **Empty Dockerfiles**: Both `backend/Dockerfile` and `frontend/Dockerfile` are 0 bytes.

### Features Missing
1. **Task manager** — no endpoint or UI
2. **Study planner** — no endpoint or UI  
3. **Progress dashboard** — no endpoint or UI
4. **Notes summarizer with modes** — only one summary format (no short/medium/detailed, no key points, no definitions, no exam revision)
5. **Quiz scoring** — quiz generation exists but no scoring logic
6. **Chat modes** — no short/medium/detailed; no general (non-doc) study chat
7. **Document deletion** — no way to delete uploaded documents or their indices
8. **Health check for Ollama** — current health check doesn't verify LLM availability
9. **File validation** — basic extension + size check exists, but no empty-file or corrupt-PDF detection

### Code Quality
1. No TypeScript — frontend is all JSX/JS
2. No linting for backend (ruff not configured)
3. No `.env.example` file
4. `.gitignore` missing `faiss_index/`, `*.db`
5. Some unused pages in frontend (HistoryPage, MetricsPage, RegisterPage, ResultsPage, UploadPage)

## Key Decisions Made

| Decision | Rationale |
|----------|-----------|
| Use Ollama HTTP API directly (not a Python SDK) | Simpler, fewer dependencies, works with any Ollama model |
| Default model: `llama3.2` | Small, fast, good for local dev; user can change via env var |
| SQLite + SQLAlchemy for structured data | Lightweight, no extra infrastructure, persists across restarts |
| Anonymous session IDs (not Google SSO) | Removes dependency on Google OAuth secrets; simpler for local use |
| Keep SentenceTransformers for embeddings | Already works well, no Ollama dependency for embeddings |
| Keep FAISS for vector store | Already implemented and tested, good for small-scale use |
| Migrate frontend to TypeScript | Type safety, better IDE support, catches bugs at compile time |
| Use vanilla CSS (not Tailwind) for new components | Per project guidelines; existing Tailwind kept for compatibility |
| Chunk size 500-800 tokens (configurable) | Better context windows for Ollama models vs original 350 words |
| Add ruff for Python linting | Fast, comprehensive, replaces flake8+isort+black |

## Baseline Test & Build Results

### Backend
- **Test command**: `pytest backend/tests/ -v`
- **Result**: 40 passed in 5.20s (including `test_parser.py`, `test_processing.py`, and `test_retriever.py` with sliding window chunker, embedding index persistence, and retrieval tests).

### Frontend
- **Lint command**: `npm run lint`
- **Result**: 6 problems (3 errors, 3 warnings).
  - `ProgressBar.jsx`: Synchronous `setState` in `useEffect`.
  - `AuthCallbackPage.jsx`: Synchronous `setState` in `useEffect`.
  - `NotebooksListPage.jsx`: Impure call `Date.now()` during render.
- **Build command**: `npm run build`
- **Result**: Succeeded (production bundle generated with Vite in `frontend/dist`). Will be migrated to TypeScript and clean ESLint.

