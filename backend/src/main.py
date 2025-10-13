"""
LocalSongs Backend Application

A modern music downloader API built with FastAPI.
Supports YouTube, YouTube Music, and Spotify platforms.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from src.api.v1.router import api_router
from src.core.config import settings

def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="LocalSongs API",
        description="Music downloader service supporting YouTube and Spotify",
        version="2.3.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API router
    app.include_router(api_router, prefix="/api")

    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return JSONResponse({
            "message": "LocalSongs API",
            "version": "2.3.0",
            "docs": "/docs",
            "status": "running"
        })

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        from src.services.download_service import DownloadService
        
        service = DownloadService()
        health_status = service.health_check()
        
        return JSONResponse(health_status)

    return app

app = create_application()

if __name__ == "__main__":
    import sys
    import os
    
    # Add the backend directory to the Python path
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, backend_dir)
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )