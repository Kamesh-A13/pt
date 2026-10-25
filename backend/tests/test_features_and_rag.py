"""
test_features_and_rag.py — Comprehensive test suite with Ollama mocked.

Tests:
  1. File validation (empty files, size, extensions)
  2. Corrupt file detection (corrupt PDF, DOCX, PPTX)
  3. Chunking with page numbers & noise cleaning
  4. Duplicate-chunk deduplication
  5. Retrieval & "not found" weak similarity behavior
  6. LLM JSON retry logic & error handling
  7. Deterministic quiz scoring & SQLite storage
  8. Task manager CRUD, status filters, and session isolation
  9. Study planner generation & conversion to actionable tasks
 10. Progress calculations (empty state vs populated real data)
 11. Document deletion and "delete all my data" purge
"""

import uuid
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.services.llm_service import _extract_json, generate_json
from app.services.retriever import _sliding_window_chunks
from app.utils.file_utils import validate_file

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1 & 2. File Validation & Corrupt File Detection Tests
# ---------------------------------------------------------------------------

def test_validate_file_empty_bytes():
    with pytest.raises(HTTPException) as exc:
        validate_file("empty.pdf", 0, file_bytes=b"")
    assert exc.value.status_code == 400
    assert "empty" in exc.value.detail.lower()


def test_validate_file_corrupt_pdf():
    # Not starting with %PDF
    with pytest.raises(HTTPException) as exc:
        validate_file("corrupt.pdf", 100, file_bytes=b"Not a real PDF file content")
    assert exc.value.status_code == 422
    assert "corrupt" in exc.value.detail.lower() or "invalid" in exc.value.detail.lower()


def test_validate_file_corrupt_docx():
    # Not starting with PK\x03\x04
    with pytest.raises(HTTPException) as exc:
        validate_file("corrupt.docx", 100, file_bytes=b"Not a zip file")
    assert exc.value.status_code == 422


def test_validate_file_corrupt_pptx():
    with pytest.raises(HTTPException) as exc:
        validate_file("corrupt.pptx", 100, file_bytes=b"Not a zip file")
    assert exc.value.status_code == 422


# ---------------------------------------------------------------------------
# 3 & 4. Chunking, Page Numbers & Deduplication Tests
# ---------------------------------------------------------------------------

def test_chunking_preserves_page_numbers():
    raw_text = """[Page 1]
Operating systems manage hardware and provide common services for computer programs.
Process management is a core component.

[Page 2]
Memory management allocates primary memory dynamically to executing processes.
Virtual memory allows execution of processes that may not be completely in memory.
"""
    chunks, meta = _sliding_window_chunks(raw_text, chunk_size=30, overlap=5, source="os.pdf")
    assert len(chunks) >= 2
    assert meta[0]["page"] == 1
    assert any(m["page"] == 2 for m in meta)


def test_chunk_deduplication():
    # Two identical content blocks on different pages
    raw_text = """[Page 1]
Data structures and algorithms are the foundational building blocks of efficient software systems.

[Page 2]
Data structures and algorithms are the foundational building blocks of efficient software systems.
"""
    chunks, meta = _sliding_window_chunks(raw_text, chunk_size=30, overlap=5, source="test.pdf")
    # Duplicate identical block from Page 2 is filtered out
    assert len(chunks) == 1


# ---------------------------------------------------------------------------
# 5. Retrieval & "Not Found" Weak Similarity Behavior
# ---------------------------------------------------------------------------

def test_chat_weak_retrieval_returns_not_found():
    """When retrieval finds no chunks matching query, returns standard not found message."""
    response = client.post(
        "/api/chat",
        json={
            "doc_id": "non_existent_doc_id_999",
            "message": "What is the secret recipe for quantum cakes?",
        },
    )
    # Since doc_id does not exist in store, it returns 404 or not found
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        data = response.json()
        assert "This information was not found in the uploaded material" in data["response"]


# ---------------------------------------------------------------------------
# 6. JSON Retry Logic & Error Handling (Mocked)
# ---------------------------------------------------------------------------

def test_extract_json_with_code_fences():
    fenced = '```json\n{"status": "ok", "items": [1, 2, 3]}\n```'
    parsed = _extract_json(fenced)
    assert parsed["status"] == "ok"
    assert parsed["items"] == [1, 2, 3]


def test_extract_json_with_preamble_and_trailing_text():
    raw = 'Here is the response you asked for:\n{"score": 95, "topic": "AI"}\nHope this helps!'
    parsed = _extract_json(raw)
    assert parsed["score"] == 95
    assert parsed["topic"] == "AI"


@patch("app.services.llm_service._call_ollama")
def test_generate_json_retry_success(mock_call):
    # First attempt returns invalid text, second returns valid JSON
    mock_call.side_effect = [
        "Oops, not JSON!",
        '{"title": "Valid JSON", "count": 42}',
    ]
    result = generate_json("dummy prompt")
    assert result["title"] == "Valid JSON"
    assert result["count"] == 42
    assert mock_call.call_count == 2


@patch("app.services.llm_service._call_ollama")
def test_generate_json_retry_failure(mock_call):
    # All attempts return invalid text
    mock_call.return_value = "Always invalid JSON"
    with pytest.raises(HTTPException) as exc:
        generate_json("dummy prompt")
    assert exc.value.status_code == 500
    assert "invalid json" in exc.value.detail.lower()


# ---------------------------------------------------------------------------
# 7. Deterministic Quiz Scoring in Python
# ---------------------------------------------------------------------------

def test_quiz_scoring_deterministic():
    questions = [
        {
            "id": 1,
            "question": "What is 2 + 2?",
            "options": {"A": "3", "B": "4", "C": "5", "D": "6"},
            "correct_answer": "B",
            "explanation": "2+2=4",
        },
        {
            "id": 2,
            "question": "Which data structure uses LIFO?",
            "options": {"A": "Queue", "B": "Stack", "C": "Array", "D": "Tree"},
            "correct_answer": "B",
            "explanation": "Stack is Last-In-First-Out",
        },
        {
            "id": 3,
            "question": "Is HTTP stateless?",
            "options": {"A": "Yes", "B": "No"},
            "correct_answer": "A",
            "explanation": "HTTP is stateless by design",
        },
    ]

    # User answers 1 and 2 correctly, 3 wrong
    answers = [
        {"question_id": 1, "selected_option": "B"},
        {"question_id": 2, "selected_option": "B"},
        {"question_id": 3, "selected_option": "B"},  # wrong
    ]

    response = client.post(
        "/api/quiz/score",
        json={
            "topic": "CS Fundamentals",
            "difficulty": "Basic",
            "questions": questions,
            "answers": answers,
        },
        headers={"X-Session-ID": "test_quiz_session"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["total_questions"] == 3
    assert data["correct_answers"] == 2
    assert data["score_percent"] == 66.7
    assert data["graded_questions"][0]["is_correct"] is True
    assert data["graded_questions"][1]["is_correct"] is True
    assert data["graded_questions"][2]["is_correct"] is False


# ---------------------------------------------------------------------------
# 8. Task Manager CRUD & Session Isolation
# ---------------------------------------------------------------------------

def test_task_manager_crud_and_isolation():
    session_a = "session_alpha"
    session_b = "session_beta"

    # Create task in session A
    res_a = client.post(
        "/api/tasks",
        json={"title": "Study Neural Networks", "description": "Read Chapter 4"},
        headers={"X-Session-ID": session_a},
    )
    assert res_a.status_code == 200
    task_a = res_a.json()
    task_id = task_a["id"]

    # Session B should NOT see session A's task
    list_b = client.get("/api/tasks", headers={"X-Session-ID": session_b})
    assert list_b.status_code == 200
    assert not any(t["id"] == task_id for t in list_b.json()["tasks"])

    # Session A sees its task
    list_a = client.get("/api/tasks", headers={"X-Session-ID": session_a})
    assert any(t["id"] == task_id for t in list_a.json()["tasks"])

    # Toggle task completed
    toggle_res = client.patch(
        f"/api/tasks/{task_id}/toggle",
        headers={"X-Session-ID": session_a},
    )
    assert toggle_res.status_code == 200
    assert toggle_res.json()["completed"] is True

    # Delete task
    del_res = client.delete(
        f"/api/tasks/{task_id}",
        headers={"X-Session-ID": session_a},
    )
    assert del_res.status_code == 200

    # Verify deleted
    list_a2 = client.get("/api/tasks", headers={"X-Session-ID": session_a})
    assert not any(t["id"] == task_id for t in list_a2.json()["tasks"])


# ---------------------------------------------------------------------------
# 9. Study Planner & Conversion to Tasks (Mocked LLM)
# ---------------------------------------------------------------------------

@patch("app.routers.planner.generate_study_plan")
def test_study_planner_and_conversion(mock_plan):
    mock_plan.return_value = {
        "plan": [
            {
                "date": "2026-11-01",
                "sessions": [
                    {
                        "subject": "Mathematics",
                        "topic": "Linear Algebra",
                        "duration_minutes": 60,
                        "notes": "Focus on Eigenvalues",
                    }
                ],
            }
        ],
        "summary": "14-day intensive review",
        "disclaimer": "This is an AI-generated study suggestion.",
    }

    session_id = "test_planner_session"
    res = client.post(
        "/api/planner/generate",
        json={
            "subjects": ["Mathematics"],
            "exam_dates": {"Mathematics": "2026-11-15"},
            "daily_hours": 4.0,
            "topics": {"Mathematics": ["Linear Algebra", "Calculus"]},
        },
        headers={"X-Session-ID": session_id},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["plan"]["disclaimer"] == "This is an AI-generated study suggestion."

    # Convert plan to tasks
    convert_res = client.post(
        "/api/planner/convert-to-tasks",
        headers={"X-Session-ID": session_id},
    )
    assert convert_res.status_code == 200
    assert convert_res.json()["tasks_created"] == 1

    # Verify task exists in task manager
    tasks_res = client.get("/api/tasks", headers={"X-Session-ID": session_id})
    assert any("Linear Algebra" in t["title"] for t in tasks_res.json()["tasks"])


# ---------------------------------------------------------------------------
# 10. Progress Calculations (Real Data vs Empty State)
# ---------------------------------------------------------------------------

def test_progress_empty_state_and_real_stats():
    fresh_session = f"fresh_{uuid.uuid4().hex[:8]}"

    # 1. Fresh session should report has_data=False
    res_empty = client.get("/api/progress", headers={"X-Session-ID": fresh_session})
    assert res_empty.status_code == 200
    data_empty = res_empty.json()
    assert data_empty["has_data"] is False
    assert data_empty["tasks"]["total"] == 0
    assert data_empty["quizzes"]["total_taken"] == 0

    # 2. Add a real completed task
    client.post(
        "/api/tasks",
        json={"title": "Finish Assignment 1"},
        headers={"X-Session-ID": fresh_session},
    )
    # Add a quiz result
    client.post(
        "/api/quiz/record",
        json={
            "topic": "Python OOP",
            "difficulty": "Intermediate",
            "total_questions": 10,
            "correct_answers": 9,
        },
        headers={"X-Session-ID": fresh_session},
    )

    # 3. Check progress now
    res_prog = client.get("/api/progress", headers={"X-Session-ID": fresh_session})
    assert res_prog.status_code == 200
    data_prog = res_prog.json()
    assert data_prog["has_data"] is True
    assert data_prog["tasks"]["total"] == 1
    assert data_prog["quizzes"]["total_taken"] == 1
    assert data_prog["quizzes"]["average_score"] == 90.0
    assert data_prog["quizzes"]["topic_performance"][0]["topic"] == "Python OOP"


# ---------------------------------------------------------------------------
# 11. Data Deletion & Purge Endpoint
# ---------------------------------------------------------------------------

def test_delete_all_user_data():
    purge_session = "purge_test_session"

    # Create task and plan
    client.post(
        "/api/tasks",
        json={"title": "To be purged task"},
        headers={"X-Session-ID": purge_session},
    )

    # Call delete all data
    del_res = client.delete("/api/data", headers={"X-Session-ID": purge_session})
    assert del_res.status_code == 200
    assert del_res.json()["purged"]["tasks"] >= 1

    # Verify session is empty
    tasks_res = client.get("/api/tasks", headers={"X-Session-ID": purge_session})
    assert len(tasks_res.json()["tasks"]) == 0


# ---------------------------------------------------------------------------
# 12. Conversational & Study Meta-Questions
# ---------------------------------------------------------------------------

def test_chat_conversational_greetings_and_study_advice():
    # 1. Greeting
    res_hi = client.post("/api/chat", json={"message": "Hi!"})
    assert res_hi.status_code == 200
    assert "Welcome to StudyOS AI" in res_hi.json()["response"]

    # 2. Completion time estimate
    res_time = client.post(
        "/api/chat",
        json={"message": "how much time will it take to complete?"},
    )
    assert res_time.status_code == 200
    assert "Estimated Study & Completion Time" in res_time.json()["response"]

    # 3. Simple study strategy
    res_simple = client.post(
        "/api/chat",
        json={"message": "how to study it simple"},
    )
    assert res_simple.status_code == 200
    assert "How to Study This in a Simple & Effective Way" in res_simple.json()["response"]

