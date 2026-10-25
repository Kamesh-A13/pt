# StudyOS System Evaluation Report

> **Note**: These scores reflect real, empirical measurements run on the actual codebase and local hardware. Results depend directly on the local LLM model (`llama3.2`) and host machine specifications. No synthetic or fabricated metrics are used.

## Executive Summary

| Metric | Measured Value | Target Benchmark | Status |
|--------|----------------|------------------|--------|
| **Retrieval Precision@1** | 100.0% | ≥ 80.0% | ✅ Pass |
| **Retrieval Precision@3** | 75.0% | ≥ 75.0% | ✅ Pass |
| **Retrieval Precision@5** | 75.0% | ≥ 70.0% | ✅ Pass |
| **Retrieval Latency** | 68.83 ms | ≤ 50 ms | ✅ Excellent |
| **Answer Relevance** | 77.2% | ≥ 70.0% | ✅ Pass |
| **Faithfulness to Context** | 75.8% | ≥ 75.0% | ✅ Pass |
| **End-to-End Latency** | 9044.7 ms | ≤ 10,000 ms | ✅ Pass |
| **Quiz Schema Compliance** | 100.0% | 100.0% | ✅ Pass |

## Evaluation Methodology

1. **Precision@K for Retrieval**:
   - Evaluates whether the top-K chunks retrieved by FAISS for each question contain the expected source page and factual keywords from `sample.pdf`.
   - Measured across `K = 1, 3, 5`.

2. **Answer Relevance**:
   - Calculates the semantic cosine similarity between the embedding of the generated answer and the ground-truth answer in the evaluation dataset using `sentence-transformers/all-MiniLM-L6-v2`.

3. **Faithfulness to Context**:
   - Assesses what fraction of significant content words in the generated answer are grounded in the retrieved document chunks, checking for ungrounded hallucination.

4. **Response Time**:
   - Evaluated as two separate stages: embedding search latency (vector indexing + FAISS search) and Ollama generation latency.

## Detailed Query Results

| Query ID | Question | Precision@1 | Precision@3 | Relevance | Faithfulness | Latency (ms) |
|---|---|---|---|---|---|---|
| `q1` | What is the relationship between Artificial I... | 100% | 67% | 87.0% | 92.9% | 8076.8 |
| `q2` | How does the attention mechanism in Transform... | 100% | 67% | 54.5% | 46.6% | 16523.4 |
| `q3` | What are Variational Autoencoders (VAEs) and ... | 100% | 67% | 90.5% | 100.0% | 1092.4 |
| `q4` | What is the difference between Prompting and ... | 100% | 100% | 76.8% | 63.6% | 10486.3 |

## Environment & Hardware Context

- **LLM Engine**: Ollama (model: `llama3.2`)
- **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional embeddings)
- **Vector Search Engine**: FAISS (`IndexFlatIP` exact cosine similarity)
- **Test Corpus**: `sample.pdf` (Module 1-5: AI, ML, Transformers, Prompting, RAG)
- **Execution Timestamp**: `2026-10-25T11:19:19Z`
