"""
test_retriever.py — Integration tests for the embedding pipeline.

Run with:
    cd backend
    pytest tests/test_retriever.py -v
"""

import shutil
import uuid

import pytest

from app.services.retriever import (
    _sliding_window_chunks,
    ingest_document,
    retrieve,
    retrieve_context_string,
)
from app.services.vector_store import FAISS_INDEX_ROOT, VectorStore

# ---------------------------------------------------------------------------
# Shared test content
# ---------------------------------------------------------------------------

# Raw text with [Page N] markers on their own lines — exactly as the parser
# outputs. Must NOT be passed through clean_text before chunking.
SAMPLE_RAW_TEXT = """[Page 1]
Machine learning is a subset of artificial intelligence that enables computers to learn from data without explicit programming.
The field has grown significantly over the past decades.
There are three main types of machine learning approaches used today.

[Page 2]
Supervised learning uses labelled training data to teach models the relationship between inputs and outputs.
Common algorithms include linear regression, decision trees, and neural networks.
The goal is to predict outputs for new, unseen inputs accurately.

[Page 3]
Unsupervised learning discovers hidden patterns in unlabelled data without prior knowledge.
Clustering algorithms group similar data points together based on their features.
Dimensionality reduction techniques like PCA reduce feature space complexity significantly.

[Page 4]
Neural networks are inspired by the human brain's biological structure and organization.
They consist of layers of interconnected nodes called neurons with weighted connections.
Deep learning stacks many hidden layers to learn complex representations from raw data.

[Page 5]
Backpropagation is the fundamental algorithm used to train neural networks efficiently.
It computes gradients to update weights during training iteratively.
Gradient descent is the core optimization algorithm that minimizes the loss function.
Learning rate controls how large each update step is during optimization.
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def doc_id():
    """
    Build a FAISS index from SAMPLE_RAW_TEXT using small chunk sizes
    suitable for the test corpus (~150 words total).
    Cleans up the index directory after all tests in this module.
    """
    _id = f"test-{uuid.uuid4().hex[:8]}"

    # Use small chunk size so the short test corpus produces multiple chunks
    chunks, meta = _sliding_window_chunks(
        SAMPLE_RAW_TEXT,
        chunk_size=30,
        overlap=5,
        source="sample_test.txt",
    )

    assert chunks, (
        "Fixture produced zero chunks from SAMPLE_RAW_TEXT. "
        "Check that _sliding_window_chunks receives raw (not cleaned) text."
    )

    vs = VectorStore(_id)
    vs.add_documents(chunks, meta)
    vs.save()

    yield _id

    index_dir = FAISS_INDEX_ROOT / _id
    if index_dir.exists():
        shutil.rmtree(index_dir)


# ---------------------------------------------------------------------------
# Chunking unit tests
# ---------------------------------------------------------------------------

class TestSlidingWindowChunker:

    def test_produces_multiple_chunks_from_long_text(self):
        text = " ".join([f"word{i}" for i in range(200)])
        chunks, _ = _sliding_window_chunks(text, chunk_size=50, overlap=10)
        assert len(chunks) >= 2

    def test_overlap_words_shared_between_adjacent_chunks(self):
        words = [f"w{i}" for i in range(100)]
        text  = " ".join(words)
        chunks, _ = _sliding_window_chunks(text, chunk_size=30, overlap=10)
        assert len(chunks) >= 2
        end_of_first    = set(chunks[0].split()[-10:])
        start_of_second = set(chunks[1].split()[:10])
        assert len(end_of_first & start_of_second) > 0

    def test_page_markers_not_in_chunk_text(self):
        chunks, _ = _sliding_window_chunks(SAMPLE_RAW_TEXT, chunk_size=50, overlap=10)
        assert chunks, "Expected chunks from SAMPLE_RAW_TEXT"
        for chunk in chunks:
            assert "[Page" not in chunk

    def test_page_number_in_metadata(self):
        _, meta = _sliding_window_chunks(SAMPLE_RAW_TEXT, chunk_size=50, overlap=10)
        assert meta, "Expected metadata entries"
        # All chunks from our sample should come from page >= 1
        assert all(m["page"] >= 1 for m in meta), (
            f"Found page=0 metadata: {[m for m in meta if m['page'] < 1]}"
        )

    def test_source_stored_in_metadata(self):
        _, meta = _sliding_window_chunks(
            SAMPLE_RAW_TEXT, chunk_size=50, overlap=10, source="lecture.pdf"
        )
        assert all(m["source"] == "lecture.pdf" for m in meta)

    def test_empty_text_returns_no_chunks(self):
        chunks, meta = _sliding_window_chunks("", chunk_size=50, overlap=10)
        assert chunks == []
        assert meta == []

    def test_text_with_only_markers_returns_no_chunks(self):
        marker_only = "[Page 1]\n[Page 2]\n[Page 3]\n"
        chunks, _ = _sliding_window_chunks(marker_only, chunk_size=50, overlap=10)
        assert chunks == []

    def test_very_short_text_below_min_words_returns_no_chunks(self):
        chunks, _ = _sliding_window_chunks("hello world", chunk_size=50, overlap=5)
        assert chunks == []

    def test_chunk_word_count_does_not_exceed_chunk_size(self):
        chunks, _ = _sliding_window_chunks(SAMPLE_RAW_TEXT, chunk_size=40, overlap=5)
        for chunk in chunks:
            assert len(chunk.split()) <= 40 + 1  # +1 for rounding tolerance

    def test_invalid_overlap_raises_value_error(self):
        with pytest.raises(ValueError, match="chunk_size must be greater than overlap"):
            _sliding_window_chunks("some text here", chunk_size=10, overlap=10)

    def test_raw_text_chunked_before_cleaning(self):
        """
        The core regression test: ensure clean_text is NOT applied before
        chunking, which would collapse [Page N] markers onto the same line
        as content and cause all words to be silently dropped.
        """
        chunks, meta = _sliding_window_chunks(SAMPLE_RAW_TEXT, chunk_size=30, overlap=5)
        assert len(chunks) > 0, (
            "Zero chunks produced — likely clean_text was called before "
            "_sliding_window_chunks, merging page markers with content lines."
        )
        assert all(m["page"] >= 1 for m in meta), (
            "All page numbers are 0 — page markers were not detected. "
            "Ensure raw text is passed to _sliding_window_chunks."
        )


# ---------------------------------------------------------------------------
# Ingest tests
# ---------------------------------------------------------------------------

class TestIngestDocument:

    def test_index_contains_positive_chunk_count(self, doc_id):
        assert VectorStore.load(doc_id).size > 0

    def test_ingest_is_idempotent(self, doc_id):
        """Second call without force_reindex returns same count without re-embedding."""
        # Create a tiny dummy file — ingest should short-circuit on the existing index
        n1 = VectorStore.load(doc_id).size
        # Pass dummy bytes; with force_reindex=False this should not re-parse
        n2 = ingest_document(doc_id, "dummy.pdf", b"", force_reindex=False)
        assert n1 == n2

    def test_empty_file_bytes_raises(self):
        with pytest.raises(Exception):
            ingest_document(
                f"empty-{uuid.uuid4().hex[:6]}",
                "empty.pdf",
                b"",
                force_reindex=True,
            )

    def test_index_file_exists_after_ingest(self, doc_id):
        assert VectorStore.exists(doc_id)

    def test_persist_and_reload_same_size(self, doc_id):
        vs1 = VectorStore.load(doc_id)
        vs2 = VectorStore.load(doc_id)
        assert vs1.size == vs2.size


# ---------------------------------------------------------------------------
# Retrieval tests
# ---------------------------------------------------------------------------

class TestRetrieve:

    def test_returns_exactly_k_results(self, doc_id):
        results = retrieve(doc_id, "machine learning", k=3)
        assert len(results) == 3

    def test_scores_are_in_descending_order(self, doc_id):
        results = retrieve(doc_id, "neural network backpropagation", k=5)
        scores  = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_backpropagation_query_returns_relevant_chunk(self, doc_id):
        results = retrieve(doc_id, "how does backpropagation update weights", k=5)
        top_text = results[0].text.lower()
        assert "backpropagation" in top_text or "gradient" in top_text

    def test_scores_are_valid_cosine_similarities(self, doc_id):
        results = retrieve(doc_id, "clustering algorithm", k=5)
        for r in results:
            assert 0.0 <= r.score <= 1.0 + 1e-5

    def test_nonexistent_doc_id_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            retrieve("nonexistent-doc-id-xyz", "query", k=3)

    def test_k_capped_at_index_size(self, doc_id):
        results = retrieve(doc_id, "machine learning", k=9999)
        vs      = VectorStore.load(doc_id)
        assert len(results) <= vs.size

    def test_context_string_is_non_empty(self, doc_id):
        ctx = retrieve_context_string(doc_id, "gradient descent", k=3)
        assert isinstance(ctx, str)
        assert len(ctx) > 0

    def test_context_string_respects_max_chars(self, doc_id):
        ctx = retrieve_context_string(doc_id, "neural networks", k=10, max_chars=500)
        assert len(ctx) <= 550

    def test_chunk_metadata_is_populated(self, doc_id):
        results = retrieve(doc_id, "unsupervised learning clustering", k=3)
        for r in results:
            assert r.chunk_id >= 0
            assert isinstance(r.text, str)
            assert len(r.text) > 0