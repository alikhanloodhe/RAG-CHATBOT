# RAG Pipeline Test Suite Documentation

This document describes the design, coverage, and running instructions for the unit test suite in the Scalable RAG Project.

---

## 1. Test Architecture & Design Principles

The backend unit tests are designed with **strict isolation** in mind:
*   **Zero External Network Calls**: Database layers, vector stores, and cache backends are fully mocked or fall back to mock memory drivers to ensure tests run fast and deterministically.
*   **Fast Execution**: The test suite executes in less than 11 seconds.
*   **Framework**: Uses Python's standard `unittest` framework.

---

## 2. Test Cases Overview

The test cases are located in the [backend/tests/](file:///Users/alikhanlodhi/Documents/Projects/Scalable-RAG-Project/backend/tests) folder:

### A. API Liveness Check (`test_api.py`)
*   **Purpose**: Validates the `/api/v1/health` liveness endpoint.
*   **Details**: Utilizes `fastapi.testclient.TestClient` to verify that the health check is a lightweight process check (returns status `ok` and does not query backend databases, preventing cascading failure alerts on simple liveness probes).

### B. Configuration Validation (`test_config.py`)
*   **Purpose**: Tests the `Settings` schema loading constraints.
*   **Details**: Verifies environment defaults, validates that CORS wildcards are blocked in production environments, and ensures that the SQLAlchemy PostgreSQL connection URI is computed correctly with passwords.

### C. Security & Authentication (`test_security.py`)
*   **Purpose**: Verifies cryptography, password hashing, and token signatures.
*   **Details**:
    *   Tests password salting and PBKDF2 SHA-256 iterations matching hash formats.
    *   Validates JWT Bearer Token generation, expire time windows, and signature decodes.
    *   Ensures that invalid, mutated, or expired tokens are rejected.

### D. Cache Backend (`test_cache.py`)
*   **Purpose**: Tests the in-memory fallback cache system when Redis is offline.
*   **Details**: Verifies basic `get` and `set` operations, and asserts that TTL keys correctly expire and are purged from memory.

### E. Query Cache Namespacing (`test_query_cache.py`)
*   **Purpose**: Tests semantic RAG query cache keys.
*   **Details**:
    *   Verifies that queries are normalized (lowercased, spaces stripped) before hashing to prevent redundant cache misses (e.g. `" What is RAG? "` hashes identically to `"what is rag?"`).
    *   Tests user-scoped query cache keys to prevent cross-user data leakage.
    *   Validates that the user's namespace counter increments on invalidation (logical cache eviction when a document is added/deleted).

### F. Text Chunker (`test_chunker.py`)
*   **Purpose**: Validates chunking boundaries and BGE token limit alignment.
*   **Details**: Tests sentence split preserving logic, and verifies the backup word-estimation fallback when HuggingFace tokenizers are absent locally.

### G. Hybrid Search & RFF Reranking (`test_hybrid.py`)
*   **Purpose**: Verifies BM25 and vector search fusion.
*   **Details**:
    *   Mocks the Qdrant client `scroll` and `query_points` APIs.
    *   Loads a mock corpus and tokenizes it dynamically.
    *   Computes BM25 query matches using the `rank-bm25` library.
    *   Validates that Reciprocal Rank Fusion (RRF) correctly combines ranks and places highly relevant keyword matches at the top of the retrieval deck, even if they are missing from raw vector retrieval.
    *   Ensures that documents with 0 keyword matches (score <= 0) receive no RRF rank boost.

---

## 3. Running Backend Tests

Ensure you have activated the virtual environment and installed the dependencies first:

```bash
cd backend
source .venv/bin/activate
python -m unittest discover -s tests
```

### Expected Output

```bash
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
...........
----------------------------------------------------------------------
Ran 11 tests in 10.477s

OK
```
