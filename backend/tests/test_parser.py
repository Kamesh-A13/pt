import pytest
import os
from app.services.parser import parse_pdf, parse_document
from app.utils.file_utils import validate_file
from fastapi import HTTPException

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_sample(filename: str) -> bytes:
    path = os.path.join(os.path.dirname(__file__), "sample_files", filename)
    with open(path, "rb") as f:
        return f.read()

# ── File Validation Tests ─────────────────────────────────────────────────────

def test_validate_file_valid_pdf():
    validate_file("notes.pdf", 1024)  # should not raise

def test_validate_file_valid_docx():
    validate_file("notes.docx", 1024)

def test_validate_file_valid_pptx():
    validate_file("slides.pptx", 1024)

def test_validate_file_invalid_extension():
    with pytest.raises(HTTPException) as exc:
        validate_file("notes.txt", 1024)
    assert exc.value.status_code == 400

def test_validate_file_too_large():
    with pytest.raises(HTTPException) as exc:
        validate_file("notes.pdf", 25 * 1024 * 1024)  # 25MB
    assert exc.value.status_code == 413

# ── Parser Tests (require sample files) ──────────────────────────────────────

def test_parse_pdf_returns_text():
    pdf_bytes = load_sample("sample.pdf")
    result = parse_pdf(pdf_bytes)
    assert isinstance(result, str)
    assert len(result) > 0

def test_parse_pdf_contains_page_markers():
    pdf_bytes = load_sample("sample.pdf")
    result = parse_pdf(pdf_bytes)
    assert "[Page 1]" in result

def test_parse_document_routes_pdf():
    pdf_bytes = load_sample("sample.pdf")
    result = parse_document("sample.pdf", pdf_bytes)
    assert isinstance(result, str)
    assert len(result) > 50

def test_parse_document_unsupported_type():
    with pytest.raises(HTTPException) as exc:
        parse_document("notes.txt", b"some text")
    assert exc.value.status_code == 400