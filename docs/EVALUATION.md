# StudyOS Evaluation Framework & Methodology

## Overview

StudyOS features an empirical evaluation framework designed to benchmark both the **Retrieval (RAG)** pipeline and the **Generation (Local Ollama)** pipeline on local hardware. 

Per the project requirements:
- No fabricated scores or artificial benchmarks are reported.
- Metrics are calculated from real retrieval queries and local LLM inferences.
- Evaluation runs against real document corpora (`sample.pdf`, `sample.docx`, `sample.pptx`).

---

## Measured Metrics

### 1. Precision@K (Retrieval)
Measures the proportion of retrieved chunks in the top-K results that contain the ground truth source page and factual keywords.
$$\text{Precision@K} = \frac{|\{\text{retrieved chunks in top-K that are relevant}\}|}{K}$$
Evaluated at:
- **Precision@1**: Relevance of the single best chunk.
- **Precision@3**: Proportion of relevant chunks in the top 3.
- **Precision@5**: Proportion of relevant chunks in the top 5.

### 2. Answer Relevance (Semantic Cosine Similarity)
Measures how well the generated answer addresses the question and aligns with the expected ground-truth answer.
$$\text{Relevance} = \cos(\mathbf{e}_{\text{generated}}, \mathbf{e}_{\text{expected}}) = \frac{\mathbf{e}_{\text{gen}} \cdot \mathbf{e}_{\text{exp}}}{\|\mathbf{e}_{\text{gen}}\| \|\mathbf{e}_{\text{exp}}\|}$$
Computed using `sentence-transformers/all-MiniLM-L6-v2` dense embeddings.

### 3. Faithfulness to Context (Grounding & Anti-Hallucination)
Measures whether the statements in the generated response are grounded in the retrieved document chunks rather than hallucinated.
$$\text{Faithfulness} = \frac{|\{\text{key terms in generated response supported by context}\}|}{|\{\text{total key terms in generated response}\}|}$$

### 4. Quiz Answer Correctness & Structure Compliance
Validates that generated MCQs:
- Adhere to the strict JSON schema (`id`, `question`, `options`, `correct_answer`, `explanation`).
- Have valid distractor options (A, B, C, D) and an accurate explanation.

### 5. Latency & Response Times
- **Retrieval Latency**: Time required to embed query and perform FAISS vector similarity search (milliseconds).
- **Generation Latency**: Time taken by Ollama to stream or return the completed completion (milliseconds).
- **Total Latency**: End-to-end turnaround time.

---

## How to Run the Evaluation

1. Ensure Ollama is running and the model is pulled:
   ```bash
   ollama pull llama3.2
   ```

2. Activate the backend virtual environment:
   ```bash
   cd backend
   source venv/bin/activate
   ```

3. Run the evaluation script:
   ```bash
   python evaluation/evaluate.py
   ```

4. The script outputs:
   - Real-time evaluation progress in the terminal.
   - Raw empirical JSON results in `backend/evaluation/results.json`.
   - A human-readable Markdown summary report in `backend/evaluation/REPORT.md`.

---

## Hardware Dependency Note

Because StudyOS operates on local models with zero API dependencies, response times and throughput depend on your host processor (e.g., Apple Silicon M-series, CUDA GPU, or x86 CPU) and available RAM.
