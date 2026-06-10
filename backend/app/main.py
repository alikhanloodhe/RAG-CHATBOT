"""Main entry point for the FastAPI application.

Configures logging, manages database initialization via the application lifespan,
applies CORS policies, and mounts API endpoints.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import configure_logging
from app.api.router import api_router
from app.db.session import init_db

# Configure JSON structured logging
configure_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the startup and shutdown lifespans of the FastAPI application."""
    # Run migrations and setup DB schemas on startup
    await init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Apply Cross-Origin Resource Sharing (CORS) rules
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount core API endpoints
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    """Serves the root greeting endpoint."""
    return {"message": "Welcome to the Scalable RAG API. Visit /api/v1/health or /docs for documentation."}
