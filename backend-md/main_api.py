"""
Music Downloader API

A FastAPI application for downloading music from YouTube and Spotify platforms
with configurable quality settings and comprehensive error handling.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import download
from app.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    
    app = FastAPI(
        title=settings.app_name,
        description="API for downloading music from Spotify and YouTube Music",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Frontend URLs
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    
    # Include API routers
    app.include_router(
        download.router,
        prefix="/api/v1",
        tags=["download"]
    )
    
    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "message": "🎵 Music Downloader API",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
            "health": "/api/v1/health",
            "endpoints": {
                "download": "/api/v1/download",
                "info": "/api/v1/info",
                "health": "/api/v1/health"
            }
        }
    
    @app.on_event("startup")
    async def startup_event():
        """Application startup event."""
        logger.info("🚀 Music Downloader API starting up...")
        logger.info(f"📁 Downloads directory: {settings.downloads_dir}")
        logger.info(f"🎵 Default quality: {settings.default_quality}")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Application shutdown event."""
        logger.info("⏹️  Music Downloader API shutting down...")
    
    return app


# Create the FastAPI application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting server directly from main_api.py")
    uvicorn.run(
        "main_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )