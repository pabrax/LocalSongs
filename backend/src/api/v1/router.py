"""
API Router v1

Main router for API version 1 endpoints.
"""

from fastapi import APIRouter

from .endpoints import download, multi_download, progress

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    download.router,
    prefix="/v1",
    tags=["download"]
)

api_router.include_router(
    multi_download.router,
    prefix="/v1", 
    tags=["multi-download"]
)

api_router.include_router(
    progress.router,
    prefix="/v1",
    tags=["progress"]
)

# Health check endpoint (no version prefix for compatibility)
@api_router.get("/health")
async def health_check():
    """Health check endpoint for backward compatibility."""
    from src.services.download_service import DownloadService
    
    service = DownloadService()
    return service.health_check()