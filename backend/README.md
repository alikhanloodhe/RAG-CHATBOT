# Scalable RAG Back-End (FastAPI)

This is the FastAPI backend for the Scalable RAG Project.

## Tech Stack & Highlights
- **FastAPI**: Main web framework for the API.
- **Bearer Token Auth**: Passwords are hashed with PBKDF2, and protected routes use signed bearer tokens.
- **SQLModel & Asyncpg**: Async ORM & driver for local PostgreSQL.
- **Qdrant Client**: Integrates with Qdrant for semantic/vector search.
- **Redis Client**: Ready for high-speed query/response caching.
- **UV**: Lightning-fast Python package installer and resolver.

## Prerequisites
1. Install [uv](https://github.com/astral-sh/uv) if not already installed:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

## Getting Started

1. Initialize a virtual environment and sync packages:
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -e .
   ```

2. Setup Environment Variables:
   ```bash
   cp .env.example .env
   ```
   Update `SECRET_KEY` in `.env` to a long random value. The default is only for local development.

   Key environment controls:
   ```env
   APP_ENV=development
   CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
   POSTGRES_SERVER=localhost
   POSTGRES_PORT=5432
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   POSTGRES_DB=rag_db
   SECRET_KEY=replace-with-a-long-random-secret
   ```

3. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

4. Run the lightweight test suite:
   ```bash
   python -m unittest discover -s tests
   ```

The backend API documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## Health & Readiness

- `GET /api/v1/health`: lightweight liveness check for the FastAPI process.
- `GET /api/v1/ready`: readiness check for local PostgreSQL, Qdrant, Redis, embedding model, and LLM configuration.

`/ready` returns `200` only when every dependency reports `ok`; otherwise it returns `503` with per-service details.

## RAG Query Response

`POST /api/v1/documents/query` returns a structured payload:
```json
{
  "answer": "Grounded answer text",
  "citations": [
    {
      "source_id": "vector-id",
      "score": 0.82,
      "filename": "paper.pdf",
      "chunk_index": 3,
      "text": "Retrieved source chunk"
    }
  ],
  "timings": {
    "retrieval_ms": 42,
    "generation_ms": 680,
    "total_ms": 722
  },
  "cache_hit": false
}
```

The citations are produced from retrieved vector payloads, not from parsing LLM text.
Repeated user/query pairs are cached using a normalized query key and `QUERY_CACHE_TTL_SECONDS`. Redis is preferred; in development, the app falls back to an in-memory cache if Redis is unavailable. Uploading or deleting documents bumps a per-user cache namespace so older answers are ignored after the source corpus changes.

## Environment Handling

- Local PostgreSQL is required for metadata in every environment. The app builds its database URL from `POSTGRES_SERVER`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`.
- `APP_ENV=development`: enables local development fallbacks for disk-backed Qdrant and in-memory query cache if those external services are down.
- `APP_ENV=production`: requires Qdrant and the embedding model to be available. The app raises explicit errors instead of silently using local/mock fallbacks.
- `CORS_ORIGINS`: comma-separated list of allowed frontend origins. `*` is rejected when `APP_ENV=production`.

## Authentication Flow

1. Register or log in with:
   ```http
   POST /api/v1/documents/auth/register
   POST /api/v1/documents/auth/login
   ```

2. The response includes:
   ```json
   {
     "access_token": "<signed-token>",
     "token_type": "bearer",
     "user": {
       "id": 1,
       "username": "alice"
     }
   }
   ```

3. Send the token to protected endpoints:
   ```http
   Authorization: Bearer <signed-token>
   ```

The document and query endpoints derive the active user from the bearer token instead of accepting a client-supplied `user_id`.

## Production Considerations & Tradeoffs

- This project requires local PostgreSQL for metadata and avoids hidden local database fallback behavior.
- `APP_ENV=production` fails loudly when Qdrant or the embedding model are unavailable.
- Logging is centralized through Python logging, and internal exception details are kept in logs rather than returned to end users.
- The project uses lightweight `unittest` tests to avoid extra test dependencies while still covering auth, config, chunking, and API liveness behavior.
