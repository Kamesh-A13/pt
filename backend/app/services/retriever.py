"""
retriever.py — Hardened document ingestion pipeline + retrieval interface.

Features:
  - 500-800 word/token configurable chunking with overlap
  - Page & slide numbers preserved in metadata
  - Text cleaning (noise removal, whitespace normalization)
  - Duplicate-chunk removal (deduplication)
  - Session and document isolation
  - Document deletion
"""

from __future__ import annotations

import hashlib
import logging
import os
import re

from app.services.parser import parse_document
from app.services.vector_store import SearchResult, VectorStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tunable chunk parameters (500-800 tokens configurable via env)
# ---------------------------------------------------------------------------

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
DEFAULT_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))


# ---------------------------------------------------------------------------
# Text cleaning & noise removal
# ---------------------------------------------------------------------------

def clean_text_noise(text: str) -> str:
    """
    Remove control characters, excessive formatting noise, and normalize spaces.
    Preserves alphanumeric text, basic punctuation, and paragraph structures.
    """
    if not text:
        return ""

    # Replace strange unicode quotes and hyphens with standard ASCII
    text = text.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    text = text.replace("—", "-").replace("–", "-")

    # Remove non-printable control characters except \n and \t
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

    # Collapse repetitive decoration symbols like '-----' or '=====' or '.....'
    text = re.sub(r"[-=_~*#]{4,}", " ", text)
    text = re.sub(r"\.{4,}", "...", text)

    # Normalize whitespace inside lines
    lines = []
    for line in text.splitlines():
        cleaned_line = " ".join(line.split())
        lines.append(cleaned_line)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sliding-window chunker with metadata & deduplication
# ---------------------------------------------------------------------------

def _sliding_window_chunks(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
    source: str = "",
) -> tuple[list[str], list[dict]]:
    """
    Split raw parsed text into overlapping word-window chunks.

    Operates on RAW parsed text so [Page N] / [Slide N] markers appear on their
    own lines and can be detected to populate chunk metadata.

    Cleans text noise, normalizes whitespace, and removes exact/near-duplicate chunks.

    Args:
        text: Raw document text from parser (with [Page N] markers).
        chunk_size: Target chunk size in words (default 500).
        overlap: Words shared between adjacent chunks (default 50).
        source: Original filename — stored in chunk metadata.

    Returns:
        (chunks, metadata_list)
    """
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    step = chunk_size - overlap
    current_page = 0
    words_with_page: list[tuple[str, int]] = []

    cleaned_raw = clean_text_noise(text)

    for line in cleaned_raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Page/slide markers are on their own lines in parser output
        if stripped.startswith("[Page ") or stripped.startswith("[Slide "):
            try:
                current_page = int(stripped.split()[-1].rstrip("]"))
            except (ValueError, IndexError):
                pass
            continue
        for word in stripped.split():
            words_with_page.append((word, current_page))

    if not words_with_page:
        return [], []

    words = [w for w, _ in words_with_page]
    pages = [p for _, p in words_with_page]

    chunks: list[str] = []
    metadata: list[dict] = []
    seen_hashes: set[str] = set()

    i = 0
    while i < len(words):
        end = min(i + chunk_size, len(words))
        raw_chunk = " ".join(words[i:end])
        page = pages[i]

        # Normalise whitespace per chunk
        cleaned_chunk = " ".join(raw_chunk.split())

        # Require meaningful content (at least 5 words)
        if len(cleaned_chunk.split()) >= 5:
            # Duplicate-chunk removal: hash normalized alphanumeric content
            norm_content = re.sub(r"[^\w\s]", "", cleaned_chunk.lower())
            chunk_hash = hashlib.md5(norm_content.encode("utf-8")).hexdigest()

            if chunk_hash not in seen_hashes:
                seen_hashes.add(chunk_hash)
                chunks.append(cleaned_chunk)
                metadata.append({"source": source, "page": page})
            else:
                logger.debug("Filtered duplicate chunk on page %d", page)

        if end == len(words):
            break
        i += step

    return chunks, metadata


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ingest_document(
    doc_id: str,
    filename: str,
    file_bytes: bytes,
    session_id: str | None = None,
    force_reindex: bool = False,
) -> int:
    """
    Parse, chunk, embed, and persist a document with session isolation.

    Returns the number of chunks indexed.
    Idempotent — skips re-embedding if the index already exists
    (unless force_reindex=True).
    """
    if not force_reindex and VectorStore.exists(doc_id, session_id=session_id):
        logger.info("Index already exists for doc_id=%s, skipping ingest", doc_id)
        return VectorStore.load(doc_id, session_id=session_id).size

    logger.info("Ingesting: %s (doc_id=%s, session_id=%s)", filename, doc_id, session_id)

    # 1. Parse — keeps [Page N] / [Slide N] markers on separate lines
    raw_text = parse_document(filename, file_bytes)
    if not raw_text.strip():
        raise ValueError("No text extracted from document — cannot index.")

    # 2. Chunk the RAW text with noise removal and deduplication
    chunks, meta = _sliding_window_chunks(
        raw_text,
        chunk_size=CHUNK_SIZE,
        overlap=CHUNK_OVERLAP,
        source=filename,
    )

    if not chunks:
        raise ValueError(
            f"Document produced zero indexable chunks "
            f"(raw_text={len(raw_text)} chars, {len(raw_text.split())} words)."
        )

    logger.info(
        "Created %d chunks (size=%d words, overlap=%d) for %s",
        len(chunks), CHUNK_SIZE, CHUNK_OVERLAP, filename,
    )

    # 3. Embed + index with session isolation
    vs = VectorStore(doc_id, session_id=session_id)
    vs.add_documents(chunks, meta)

    # 4. Persist to disk
    vs.save()

    return len(chunks)


def retrieve(
    doc_id: str,
    query: str,
    k: int = DEFAULT_TOP_K,
    session_id: str | None = None,
) -> list[SearchResult]:
    """
    Retrieve the top-k most relevant chunks for a query.

    Raises:
        FileNotFoundError: If no index exists for this doc_id.
    """
    vs = VectorStore.load(doc_id, session_id=session_id)
    results = vs.search(query, k=k)
    logger.debug("Retrieved %d chunks for query=%r", len(results), query[:60])
    return results


def retrieve_context_string(
    doc_id: str,
    query: str,
    k: int = DEFAULT_TOP_K,
    max_chars: int = 6000,
    session_id: str | None = None,
) -> str:
    """
    Retrieve top-k chunks as a single formatted string for LLM injection.
    Truncated at max_chars.
    """
    results = retrieve(doc_id, query, k=k, session_id=session_id)

    parts = []
    total = 0
    for r in results:
        label = f"[{r.source} p.{r.page}]" if r.page >= 0 else f"[{r.source}]"
        chunk = f"{label}\n{r.text}\n"
        if total + len(chunk) > max_chars:
            remaining = max_chars - total
            if remaining > 100:
                parts.append(chunk[:remaining])
            break
        parts.append(chunk)
        total += len(chunk)

    return "\n".join(parts)


def delete_document(doc_id: str, session_id: str | None = None) -> bool:
    """Delete a document's vector store and disk index."""
    return VectorStore.delete(doc_id, session_id=session_id)


def delete_session_documents(session_id: str) -> bool:
    """Delete all vector store indexes for a session."""
    return VectorStore.delete_session(session_id)