"""
file_utils.py — Validation helpers for uploaded files.
Handles:
  - Allowed extensions (.pdf, .docx, .pptx)
  - File size limits (max 20MB)
  - Empty files (0 bytes)
  - Corrupt PDF / DOCX / PPTX detection
"""

import io
import os
from fastapi import HTTPException

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx"}
MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def validate_file(filename: str, file_size: int, file_bytes: bytes | None = None) -> None:
    """
    Validate file extension, size, non-emptiness, and integrity.
    Raises HTTPException with appropriate HTTP status codes on failure.
    """
    if not filename or not filename.strip():
        raise HTTPException(status_code=400, detail="Filename cannot be empty.")

    ext = os.path.splitext(filename)[-1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed types: PDF, DOCX, PPTX",
        )

    if file_size <= 0 or (file_bytes is not None and len(file_bytes) == 0):
        raise HTTPException(
            status_code=400,
            detail=f"Uploaded file '{filename}' is empty (0 bytes).",
        )

    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({file_size / (1024*1024):.1f}MB). Max allowed size is {MAX_FILE_SIZE_MB}MB.",
        )

    # Content integrity check if bytes provided
    if file_bytes is not None:
        if ext == ".pdf":
            # PDF magic bytes check (%PDF-)
            if not file_bytes.startswith(b"%PDF"):
                raise HTTPException(
                    status_code=422,
                    detail="Corrupt or invalid PDF file: Missing %PDF header.",
                )
            try:
                import fitz
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                if doc.is_encrypted:
                    raise HTTPException(
                        status_code=422,
                        detail="Encrypted or password-protected PDFs are not supported.",
                    )
                if len(doc) == 0:
                    raise HTTPException(
                        status_code=422,
                        detail="Corrupt PDF: document contains 0 pages.",
                    )
                doc.close()
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=422,
                    detail=f"Corrupt or invalid PDF file: {str(e)}",
                )

        elif ext == ".docx":
            # ZIP magic bytes check (PK\x03\x04)
            if not file_bytes.startswith(b"PK\x03\x04"):
                raise HTTPException(
                    status_code=422,
                    detail="Corrupt or invalid DOCX file: Invalid file header.",
                )
            try:
                from docx import Document
                Document(io.BytesIO(file_bytes))
            except Exception as e:
                raise HTTPException(
                    status_code=422,
                    detail=f"Corrupt or unreadable DOCX file: {str(e)}",
                )

        elif ext == ".pptx":
            # ZIP magic bytes check (PK\x03\x04)
            if not file_bytes.startswith(b"PK\x03\x04"):
                raise HTTPException(
                    status_code=422,
                    detail="Corrupt or invalid PPTX file: Invalid file header.",
                )
            try:
                from pptx import Presentation
                Presentation(io.BytesIO(file_bytes))
            except Exception as e:
                raise HTTPException(
                    status_code=422,
                    detail=f"Corrupt or unreadable PPTX file: {str(e)}",
                )


def get_file_extension(filename: str) -> str:
    return os.path.splitext(filename)[-1].lower()