import os
from fastapi.testclient import TestClient
from app.main import app
from app.services.parser import parse_document_chunks

client = TestClient(app)


def load_sample(filename: str) -> bytes:
    path = os.path.join(os.path.dirname(__file__), "sample_files", filename)
    with open(path, "rb") as f:
        return f.read()


# ── Chunk Parser Tests ─────────────────────────────────

def test_parse_document_chunks_pdf():
    pdf_bytes = load_sample("sample.pdf")
    chunks = parse_document_chunks("sample.pdf", pdf_bytes)

    assert isinstance(chunks, list)
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)


def test_parse_document_chunks_docx():
    docx_bytes = load_sample("sample.docx")
    chunks = parse_document_chunks("sample.docx", docx_bytes)

    assert isinstance(chunks, list)
    assert len(chunks) > 0


def test_parse_document_chunks_pptx():
    pptx_bytes = load_sample("sample.pptx")
    chunks = parse_document_chunks("sample.pptx", pptx_bytes)

    assert isinstance(chunks, list)
    assert len(chunks) > 0


# ── /process Endpoint Tests ───────────────────────────

def test_process_endpoint_pdf():
    path = os.path.join(os.path.dirname(__file__), "sample_files", "sample.pdf")

    with open(path, "rb") as f:
        response = client.post("/process", files={"file": f})

    assert response.status_code == 200
    data = response.json()

    assert "filename" in data
    assert "chunks" in data
    assert data["num_chunks"] > 0


def test_process_endpoint_docx():
    path = os.path.join(os.path.dirname(__file__), "sample_files", "sample.docx")

    with open(path, "rb") as f:
        response = client.post("/process", files={"file": f})

    assert response.status_code == 200


def test_process_endpoint_pptx():
    path = os.path.join(os.path.dirname(__file__), "sample_files", "sample.pptx")

    with open(path, "rb") as f:
        response = client.post("/process", files={"file": f})

    assert response.status_code == 200
