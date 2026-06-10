from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings

router = APIRouter()


def check_llm_config() -> dict:
    """Checks if the LLM provider connection (Groq API) is fully configured.

    Returns:
        A dict outlining status, configured state, and active model name.
    """
    from app.services.llm import llm_service

    configured = llm_service.is_configured()
    return {
        "status": "ok" if configured else "unavailable",
        "model": settings.GROQ_MODEL,
        "configured": configured,
    }


def check_embedding_model() -> dict:
    """Checks if the local SentenceTransformers embedding model is loaded.

    Returns:
        A dict outlining status, model name, readiness, and fallback status.
    """
    from app.services.embeddings import embedding_service

    ready = embedding_service.is_ready()
    return {
        "status": "ok" if ready else "degraded",
        "model": embedding_service.model_name,
        "ready": ready,
        "fallback_active": not ready,
    }


async def check_database() -> dict:
    """Tests connection to SQL database (PostgreSQL/SQLite) using a simple query.

    Returns:
        A dict outlining database status, backend driver name, and active database name.
    """
    from app.db.session import get_engine

    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "backend": engine.url.get_backend_name(),
            "database": engine.url.database,
        }
    except Exception as exc:
        return {
            "status": "unavailable",
            "error": exc.__class__.__name__,
        }


def check_qdrant() -> dict:
    """Tests connection to Qdrant vector database using a list collections ping.

    Returns:
        A dict outlining status, collection counts, or error name if offline.
    """
    from app.services.rag import rag_service

    try:
        collections = rag_service.ping()
        return {
            "status": "ok",
            "collections": collections,
        }
    except Exception as exc:
        return {
            "status": "unavailable",
            "error": exc.__class__.__name__,
        }


def check_redis() -> dict:
    """Checks cache connectivity using a ping command to Redis.

    Returns:
        A dict outlining cache status and error class if offline.
    """
    from app.services.cache import cache_service

    try:
        cache_service.ping()
        return {"status": "ok"}
    except Exception as exc:
        return {
            "status": "unavailable",
            "error": exc.__class__.__name__,
        }


@router.get("/health", tags=["health"])
def health_check():
    """Performs a simple app-level liveness health check.

    Returns:
        JSON payload outlining app details and active environment.
    """
    return {
        "status": "ok",
        "app": settings.PROJECT_NAME,
        "environment": settings.APP_ENV,
    }


@router.get("/ready", tags=["health"])
async def readiness_check():
    """Runs connectivity checks on all dependent backends (DB, Redis, Qdrant, Model loading).

    Returns:
        JSONResponse showing complete readiness payload of the RAG system dependencies.
    """
    services = {
        "database": await check_database(),
        "qdrant": check_qdrant(),
        "redis": check_redis(),
        "embeddings": check_embedding_model(),
        "llm": check_llm_config(),
    }

    is_ready = all(service["status"] == "ok" for service in services.values())
    payload = {
        "status": "ready" if is_ready else "not_ready",
        "environment": settings.APP_ENV,
        "services": services,
    }
    return JSONResponse(status_code=200 if is_ready else 503, content=payload)
