# Main API Router configurations, merging routes from documents and health namespaces.

from fastapi import APIRouter
from app.api.documents import router as documents_router
from app.api.health import router as health_router

api_router = APIRouter()

# Register sub-routers
api_router.include_router(health_router, tags=["health"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
