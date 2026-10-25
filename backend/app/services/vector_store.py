"""
vector_store.py — FAISS-backed vector store for document chunks.

Provides a clean interface: add_documents → search → persist/load.
No external database required — the index lives on disk as two files:
    <index_dir>/index.faiss   — the FAISS index binary
    <index_dir>/metadata.json — chunk texts + source metadata

Design decisions:
    - IndexFlatIP (inner product) over unit vectors = exact cosine similarity.
    - No approximate index (HNSW/IVF) because our chunk counts are small
      (typically < 2000 per document). Flat is faster at this scale.
    - One store per document (keyed by doc_id). Stores are lazy-loaded.

Usage:
    from app.services.vector_store import VectorStore

    vs = VectorStore(doc_id="abc123")
    vs.add_documents(chunks, metadata_list)
    results = vs.search("what is backpropagation", k=5)
    vs.save()

    vs2 = VectorStore.load(doc_id="abc123")
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


from app.services.embedder import get_embedder

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

FAISS_INDEX_ROOT = Path(
    os.getenv("FAISS_INDEX_ROOT", "faiss_index")
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ChunkMetadata:
    """Metadata attached to every stored chunk."""
    chunk_id:  int
    text:      str
    source:    str = ""    # filename or slide/page label
    page:      int = -1    # page / slide number (-1 = unknown)
    char_count: int = 0


@dataclass
class SearchResult:
    """Returned by VectorStore.search()."""
    chunk_id:  int
    text:      str
    score:     float       # cosine similarity in [0, 1]
    source:    str = ""
    page:      int = -1


# ---------------------------------------------------------------------------
# VectorStore
# ---------------------------------------------------------------------------

class VectorStore:
    """
    Per-document FAISS index with chunk text storage.

    Lifecycle:
        1. vs = VectorStore(doc_id)          — new empty store
        2. vs.add_documents(chunks, meta)    — embed + index
        3. vs.save()                         — write to disk
        4. vs = VectorStore.load(doc_id)     — restore from disk
        5. results = vs.search(query, k=5)   — retrieve top-k chunks
    """

    def __init__(self, doc_id: str, session_id: str | None = None) -> None:
        self.doc_id     = doc_id
        self.session_id = session_id
        self._index     = None   # faiss.IndexFlatIP
        self._meta: list[ChunkMetadata] = []
        self._embedder  = get_embedder()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_documents(
        self,
        chunks: list[str],
        metadata: list[dict[str, Any]] | None = None,
    ) -> None:
        """
        Embed chunks and add them to the FAISS index.

        Args:
            chunks:   List of text strings (already cleaned + chunked).
            metadata: Optional list of dicts with keys: source, page.
                      If None, defaults are used.
        """
        if not chunks:
            logger.warning("add_documents called with empty chunk list")
            return

        import faiss  # lazy import — only needed when indexing

        metadata = metadata or [{}] * len(chunks)
        if len(metadata) != len(chunks):
            raise ValueError("metadata length must match chunks length")

        logger.info("Embedding %d chunks for doc_id=%s (session=%s)", len(chunks), self.doc_id, self.session_id)
        vectors = self._embedder.embed(chunks, show_progress=True)  # (N, dim)

        # Build or extend FAISS index
        if self._index is None:
            self._index = faiss.IndexFlatIP(self._embedder.dim)

        self._index.add(vectors)

        start_id = len(self._meta)
        for i, (chunk, meta, vec) in enumerate(zip(chunks, metadata, vectors)):
            self._meta.append(ChunkMetadata(
                chunk_id  = start_id + i,
                text      = chunk,
                source    = meta.get("source", ""),
                page      = meta.get("page", -1),
                char_count = len(chunk),
            ))

        logger.info("Index now contains %d vectors", self._index.ntotal)

    def search(self, query: str, k: int = 5) -> list[SearchResult]:
        """
        Find the top-k most relevant chunks for a query.

        Args:
            query: Natural language question or keyword string.
            k:     Number of results to return.

        Returns:
            List of SearchResult sorted by descending cosine similarity.

        Raises:
            RuntimeError: If the index is empty (no documents added yet).
        """
        if self._index is None or self._index.ntotal == 0:
            raise RuntimeError(
                f"VectorStore for doc_id='{self.doc_id}' is empty. "
                "Call add_documents() first."
            )

        k = min(k, self._index.ntotal)
        query_vec = self._embedder.embed_query(query).reshape(1, -1)  # (1, dim)

        scores, indices = self._index.search(query_vec, k)
        scores  = scores[0].tolist()    # flatten from (1, k) → (k,)
        indices = indices[0].tolist()

        results = []
        for score, idx in zip(scores, indices):
            if idx < 0:   # FAISS returns -1 when k > ntotal
                continue
            meta = self._meta[idx]
            results.append(SearchResult(
                chunk_id = meta.chunk_id,
                text     = meta.text,
                score    = float(score),
                source   = meta.source,
                page     = meta.page,
            ))

        return results

    def save(self) -> Path:
        """
        Persist the FAISS index and metadata to disk.

        Returns:
            Path to the index directory.
        """
        import faiss

        index_dir = self._index_dir()
        index_dir.mkdir(parents=True, exist_ok=True)

        # Write FAISS binary
        faiss.write_index(self._index, str(index_dir / "index.faiss"))

        # Write metadata JSON
        meta_path = index_dir / "metadata.json"
        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(
                [asdict(m) for m in self._meta],
                f,
                ensure_ascii=False,
                indent=2,
            )

        logger.info("Saved index (%d vectors) → %s", self._index.ntotal, index_dir)
        return index_dir

    @classmethod
    def load(cls, doc_id: str, session_id: str | None = None) -> "VectorStore":
        """
        Restore a VectorStore from disk.

        Args:
            doc_id: The document ID used when the store was saved.
            session_id: Optional session identifier for isolated directories.

        Returns:
            A fully populated VectorStore ready for search().
        """
        import faiss

        if session_id and (FAISS_INDEX_ROOT / session_id / doc_id / "index.faiss").exists():
            vs = cls(doc_id, session_id=session_id)
        elif (FAISS_INDEX_ROOT / doc_id / "index.faiss").exists():
            vs = cls(doc_id, session_id=None)
        elif session_id:
            vs = cls(doc_id, session_id=session_id)
        else:
            vs = cls(doc_id)

        index_dir = vs._index_dir()
        faiss_path = index_dir / "index.faiss"
        meta_path  = index_dir / "metadata.json"

        if not faiss_path.exists():
            raise FileNotFoundError(
                f"No saved FAISS index for doc_id='{doc_id}' at {faiss_path}"
            )

        vs._index = faiss.read_index(str(faiss_path))

        with meta_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        vs._meta = [ChunkMetadata(**m) for m in raw]

        logger.info(
            "Loaded index (%d vectors) for doc_id=%s (session=%s)",
            vs._index.ntotal, doc_id, vs.session_id,
        )
        return vs

    @classmethod
    def exists(cls, doc_id: str, session_id: str | None = None) -> bool:
        """Return True if a saved index exists for this doc_id."""
        if session_id and (FAISS_INDEX_ROOT / session_id / doc_id / "index.faiss").exists():
            return True
        return (FAISS_INDEX_ROOT / doc_id / "index.faiss").exists()

    @classmethod
    def delete(cls, doc_id: str, session_id: str | None = None) -> bool:
        """Delete saved FAISS index directory and metadata."""
        import shutil
        deleted = False
        candidates = []
        if session_id:
            candidates.append(FAISS_INDEX_ROOT / session_id / doc_id)
        candidates.append(FAISS_INDEX_ROOT / doc_id)

        for path in candidates:
            if path.exists():
                shutil.rmtree(path)
                deleted = True
        return deleted

    @classmethod
    def delete_session(cls, session_id: str) -> bool:
        """Delete all index directories belonging to a session."""
        import shutil
        session_path = FAISS_INDEX_ROOT / session_id
        if session_path.exists():
            shutil.rmtree(session_path)
            return True
        return False

    @property
    def size(self) -> int:
        """Number of indexed vectors."""
        return self._index.ntotal if self._index else 0

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _index_dir(self) -> Path:
        if self.session_id:
            return FAISS_INDEX_ROOT / self.session_id / self.doc_id
        return FAISS_INDEX_ROOT / self.doc_id