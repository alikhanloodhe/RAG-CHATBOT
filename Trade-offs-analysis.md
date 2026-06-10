# RAG Pipeline Trade-Offs Analysis

This document outlines the architectural trade-offs and rationale behind the chunking strategy, embedding models, retrieval pipelines, and backend processing models for the Scalable RAG Project.

---

## 1. Context & The Embedding Model Limit
The system currently uses **`BAAI/bge-small-en-v1.5`** as its local embedding model. 
* **Model Dimension**: 384 dimensions (Cosine similarity distance metric).
* **Max Sequence Length (Context Window)**: **512 tokens**.

### The Silent Truncation Problem
* **Original Parameters**: `min_tokens = 500`, `max_tokens = 800`, `overlap_tokens = 100`.
* **The Issue**: Any text chunk containing more than 512 tokens was silently truncated by the model's tokenizer when generating embeddings. This meant words past the 512th token did not contribute to the vector representation, resulting in a loss of semantic information for the second half of large chunks.
* **Updated Parameters**:
  * **`min_tokens = 300`**
  * **`max_tokens = 500`**
  * **`overlap_tokens = 50`**

---

## 2. Detailed Chunking Trade-Offs

Choosing chunk parameters involves balancing competing constraints in vector retrieval and LLM context utility.

| Dimension | Small Chunks (100–300 tokens) | Medium-Large Chunks (300–500 tokens) |
| :--- | :--- | :--- |
| **Retrieval Precision** | **High**: The vector matches the exact, focused semantic unit (sentence or paragraph) containing the information. | **Moderate**: The target information is packed alongside surrounding text, slightly diluting focus. |
| **LLM Context Quality** | **Low/Moderate**: May lose broader narrative context, antecedent references (e.g., pronouns), or table schemas. | **High**: Retains complete sections, code blocks, tables, and sequential reasoning steps. |
| **Prompt Space Efficiency** | **High**: You can fit many distinct chunks from different documents into the LLM's prompt window, increasing answer diversity. | **Moderate**: Fits fewer distinct source documents in the prompt before reaching the LLM's limit. |
| **Truncation Risks** | **None**: Safely fits inside the 512-token limit of lightweight models like BGE-small. | **Low/Moderate**: Near the physical limit of the model (512 tokens). Requires careful token budget management. |

### Rationale for the `300–500` Range
* **Pros**: Maximize the amount of semantic content loaded into a single vector, retaining paragraph coherence.
* **Risks**: Because BGE-small has a strict 512-token context limit, a 500-token chunk leaves only 12 tokens for control characters and search prefixes. Any chunk that drifts slightly past 512 tokens during tokenizer encoding will experience minor tail-end truncation.

---

## 3. Asymmetric Retrieval & Query Instructions

BGE is an **asymmetric retrieval model**—it is specifically trained to match short queries (questions) against long documents (passages). Because of this asymmetry, the model requires different input formats for queries versus passages:

1. **Passages / Document Chunks**: Indexed as raw text. **No instruction prefix is added**. (Adding a prefix to stored passages would pollute the index and degrade accuracy).
2. **Queries**: Must have the search prefix prepended: 
   `"Represent this sentence for searching relevant passages: {query}"`

### Implementation & Trade-off
* **Our Approach**: We updated `get_embedding(text, is_query=True)` in `embeddings.py` to dynamically detect BGE models and prepend the instruction string to the query before vectorization.
* **Trade-off**: Adding the instruction prefix to query execution consumes roughly **9 tokens** of the 512 context limit. However, it aligns the query representation with the model's training distribution, resulting in **significantly higher search precision and semantic overlap scores** during cosine similarity comparisons in Qdrant.

---

## 4. Hybrid Search (Dense Vector vs. Sparse BM25)

The RAG pipeline implements a hybrid search combining dense vector search and BM25 lexical search.

*   **Dense Semantic Search (Qdrant)**:
    *   *Pros*: Captures semantic meaning, synonyms, and conceptual relationships (e.g., matching "database connection issues" with "pool limit exceeded" even if no words overlap).
    *   *Cons*: Fails at matching exact, arbitrary strings (e.g., serial numbers, error codes like `ERR_503`, user IDs, specific email addresses).
*   **Sparse Lexical Search (BM25)**:
    *   *Pros*: Outstanding at precise keyword matching, exact terms, and specific identifiers. Very fast computation.
    *   *Cons*: Complete lack of semantic understanding (fails if synonyms or paraphrased queries are used).
*   **The Trade-off**: Running both side-by-side increases query execution time by a few milliseconds and requires loading the user's corpus into memory, but it guarantees that the RAG pipeline is robust both semantically and keywords-wise.

---

## 5. Rank Aggregation: Reciprocal Rank Fusion (RRF)

To merge dense and sparse results, the system implements **Reciprocal Rank Fusion (RRF)**.
*   **How it works**: Combines the rank position of items returned by both models instead of adding their raw similarity scores directly:
    $$RRF(d) = \sum_{m \in \text{rankers}} \frac{1}{60 + \text{rank}_m(d)}$$
*   **Why it's preferred over Score Summation**: Dense search returns cosine similarity scores (range `-1.0` to `1.0`, typically clustered in `0.5` to `0.9`), while BM25 returns raw scoring metrics (range `0.0` to `infinity` depending on document length and term frequency). You cannot normalize or add these scores mathematically. RRF bypasses score normalization entirely.
*   **The Trade-off**: RRF treats rank steps linearly (the transition from rank 1 to rank 2 has the same weight regardless of whether the score gap is large or tiny). It ignores the relative magnitude of search scores.

---

## 6. Concurrency: Async Event Loop vs. Thread Pools (`asyncio.to_thread`)

Background document ingestion does heavy parsing (PDFs) and CPU-heavy tasks (generating embeddings via local PyTorch/SentenceTransformers).
*   **The Issue**: FastAPI runs background tasks marked as `async def` in the main event loop. If a background task runs heavy CPU work, it blocks the main loop. This freezes the server, causing other user requests (like status checks) to hang.
*   **Our Solution**: Offload CPU-bound functions to an external thread pool using **`asyncio.to_thread`**.
*   **The Trade-off**: Thread context switching incurs minor OS overhead and Python's Global Interpreter Lock (GIL) prevents true multi-core utilization for CPU-bound tasks in a single process. However, for a web server, keeping the event loop responsive to prevent client timeouts is significantly more important than optimizing raw single-thread CPU execution.
