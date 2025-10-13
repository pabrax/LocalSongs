"""
Multi-file download endpoints for albums and playlists.

Provides Server-Sent Events (SSE) for real-time progress updates during multi-file downloads.
"""

import asyncio
import json
import logging
import time
import uuid
import os
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from concurrent.futures import ThreadPoolExecutor
import threading

from ....services.download_service import downloader, AudioQuality
from ....schemas.models import DownloadRequest
from ....core.utils import URLValidator, QualityManager
from .progress import ProgressTracker

logger = logging.getLogger(__name__)
router = APIRouter()

# Global multi-download tracking
multi_download_store: Dict[str, Dict[str, Any]] = {}
multi_download_lock = threading.Lock()

class MultiFileProgressTracker:
    """Thread-safe progress tracker for multi-file download operations."""
    
    def __init__(self, download_id: str, total_files: int):
        self.download_id = download_id
        self.total_files = total_files
        self.completed_files = 0
        self.failed_files = 0
        self.current_file_index = 0
        self.current_file_progress = 0
        self.current_file_name = ""
        self.current_file_status = "preparing"
        self.files_info: List[Dict[str, Any]] = []
        self.overall_status = "starting"
        self.error = None
        
    def update_overall(self, status: str, message: str = "", error: Optional[str] = None):
        """Update overall download status."""
        with multi_download_lock:
            self.overall_status = status
            if error:
                self.error = error
            
            multi_download_store[self.download_id] = {
                "download_id": self.download_id,
                "total_files": self.total_files,
                "completed_files": self.completed_files,
                "failed_files": self.failed_files,
                "current_file_index": self.current_file_index,
                "current_file_progress": self.current_file_progress,
                "current_file_name": self.current_file_name,
                "current_file_status": self.current_file_status,
                "overall_progress": self._calculate_overall_progress(),
                "overall_status": self.overall_status,
                "message": message,
                "error": error,
                "files_info": self.files_info.copy(),
                "timestamp": time.time()
            }
    
    def update_current_file(self, file_index: int, file_name: str, progress: int, status: str, message: str = ""):
        """Update current file progress."""
        with multi_download_lock:
            self.current_file_index = file_index
            self.current_file_name = file_name
            self.current_file_progress = progress
            self.current_file_status = status
            
            # Update or add file info
            while len(self.files_info) <= file_index:
                self.files_info.append({
                    "index": len(self.files_info),
                    "name": "",
                    "status": "pending",
                    "progress": 0,
                    "error": None
                })
            
            self.files_info[file_index] = {
                "index": file_index,
                "name": file_name,
                "status": status,
                "progress": progress,
                "error": None,
                "message": message
            }
            
            multi_download_store[self.download_id] = {
                "download_id": self.download_id,
                "total_files": self.total_files,
                "completed_files": self.completed_files,
                "failed_files": self.failed_files,
                "current_file_index": self.current_file_index,
                "current_file_progress": self.current_file_progress,
                "current_file_name": self.current_file_name,
                "current_file_status": self.current_file_status,
                "overall_progress": self._calculate_overall_progress(),
                "overall_status": self.overall_status,
                "message": f"Descargando {file_name} ({file_index + 1}/{self.total_files})",
                "error": self.error,
                "files_info": self.files_info.copy(),
                "timestamp": time.time()
            }
    
    def complete_file(self, file_index: int, file_name: str, success: bool, error: Optional[str] = None):
        """Mark a file as completed or failed."""
        with multi_download_lock:
            if success:
                self.completed_files += 1
                status = "completed"
            else:
                self.failed_files += 1
                status = "failed"
            
            # Update file info
            if file_index < len(self.files_info):
                self.files_info[file_index].update({
                    "status": status,
                    "progress": 100 if success else 0,
                    "error": error
                })
            
            multi_download_store[self.download_id] = {
                "download_id": self.download_id,
                "total_files": self.total_files,
                "completed_files": self.completed_files,
                "failed_files": self.failed_files,
                "current_file_index": self.current_file_index,
                "current_file_progress": self.current_file_progress,
                "current_file_name": self.current_file_name,
                "current_file_status": self.current_file_status,
                "overall_progress": self._calculate_overall_progress(),
                "overall_status": self.overall_status,
                "message": f"Completado: {file_name}" if success else f"Error: {file_name}",
                "error": self.error,
                "files_info": self.files_info.copy(),
                "timestamp": time.time()
            }
    
    def _calculate_overall_progress(self) -> int:
        """Calculate overall progress percentage."""
        if self.total_files == 0:
            return 0
        
        # Each completed file contributes (100 / total_files)%
        completed_contribution = (self.completed_files * 100) / self.total_files
        
        # Current file contributes its progress percentage scaled to its portion
        current_contribution = (self.current_file_progress / self.total_files) if self.total_files > 0 else 0
        
        return min(int(completed_contribution + current_contribution), 100)
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current progress information."""
        with multi_download_lock:
            return multi_download_store.get(self.download_id, {
                "download_id": self.download_id,
                "total_files": 0,
                "completed_files": 0,
                "failed_files": 0,
                "current_file_index": 0,
                "current_file_progress": 0,
                "current_file_name": "",
                "current_file_status": "unknown",
                "overall_progress": 0,
                "overall_status": "unknown",
                "message": "Estado desconocido",
                "error": None,
                "files_info": [],
                "timestamp": time.time()
            })
    
    def cleanup(self):
        """Clean up progress data."""
        with multi_download_lock:
            if self.download_id in multi_download_store:
                del multi_download_store[self.download_id]

def create_multi_download_tracker(total_files: int) -> str:
    """Create a new multi-download tracker and return its ID."""
    download_id = str(uuid.uuid4())
    tracker = MultiFileProgressTracker(download_id, total_files)
    tracker.update_overall("created", f"Preparando descarga de {total_files} archivos")
    return download_id

@router.get("/multi-progress/{download_id}")
async def get_multi_download_progress(download_id: str):
    """Get current progress for a multi-file download."""
    try:
        with multi_download_lock:
            progress_data = multi_download_store.get(download_id)
        
        if not progress_data:
            raise HTTPException(
                status_code=404,
                detail="Multi-download ID not found"
            )
        
        return progress_data
    except Exception as e:
        logger.error(f"Error getting multi-download progress: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting progress: {str(e)}"
        )

@router.get("/multi-progress-stream/{download_id}")
async def stream_multi_download_progress(download_id: str):
    """Stream multi-download progress using Server-Sent Events."""
    
    async def generate_multi_progress_stream():
        """Generate SSE stream for multi-download progress updates."""
        try:
            last_progress = -1
            max_iterations = 1800  # 30 minutes max (1800 * 1 second)
            iteration = 0
            
            while iteration < max_iterations:
                with multi_download_lock:
                    progress_data = multi_download_store.get(download_id)
                
                if not progress_data:
                    # Send completion event if no data found
                    yield f"data: {json.dumps({'overall_progress': 100, 'overall_status': 'completed', 'message': 'Descarga completada'})}\\n\\n"
                    break
                
                # Only send update if progress changed
                current_progress = progress_data.get('overall_progress', 0)
                if current_progress != last_progress or iteration == 0 or iteration % 5 == 0:  # Send every 5 seconds regardless
                    yield f"data: {json.dumps(progress_data)}\\n\\n"
                    last_progress = current_progress
                
                # Check if download is complete
                status = progress_data.get('overall_status', '')
                if status in ['completed', 'success', 'error', 'failed', 'cancelled']:
                    yield f"data: {json.dumps(progress_data)}\\n\\n"
                    break
                
                await asyncio.sleep(1)
                iteration += 1
            
            if iteration >= max_iterations:
                yield f"data: {json.dumps({'overall_progress': 0, 'overall_status': 'timeout', 'message': 'Descarga excedió tiempo límite'})}\\n\\n"
                
        except Exception as e:
            logger.error(f"Error in multi-progress stream: {e}")
            yield f"data: {json.dumps({'overall_progress': 0, 'overall_status': 'error', 'message': f'Error en stream: {str(e)}'})}\\n\\n"
    
    return StreamingResponse(
        generate_multi_progress_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

@router.delete("/multi-progress/{download_id}")
async def cleanup_multi_download_progress(download_id: str):
    """Clean up multi-download progress data."""
    try:
        with multi_download_lock:
            if download_id in multi_download_store:
                del multi_download_store[download_id]
        
        return {"message": "Multi-download progress cleaned up successfully"}
    except Exception as e:
        logger.error(f"Error cleaning up multi-download progress: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error cleaning up progress: {str(e)}"
        )

@router.get("/multi-progress/list/active")
async def list_active_multi_downloads():
    """List all active multi-downloads."""
    try:
        with multi_download_lock:
            active_downloads = list(multi_download_store.keys())
        
        return {
            "active_downloads": active_downloads,
            "count": len(active_downloads)
        }
    except Exception as e:
        logger.error(f"Error listing active multi-downloads: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing downloads: {str(e)}"
        )

@router.post("/create-zip/{download_id}")
async def create_playlist_zip(download_id: str):
    """Create a ZIP file from completed playlist download."""
    try:
        # Get download info
        with multi_download_lock:
            if download_id not in multi_download_store:
                raise HTTPException(
                    status_code=404,
                    detail="Download ID not found"
                )
            
            download_info = multi_download_store[download_id]
        
        # Check if download is completed
        if download_info.get("overall_status") != "completed":
            raise HTTPException(
                status_code=400,
                detail="Download not completed yet"
            )
        
        # Get playlist info and files
        playlist_info = download_info.get("playlist_info", {})
        files_info = download_info.get("files_info", [])
        
        if not files_info:
            raise HTTPException(
                status_code=400,
                detail="No files available for ZIP creation"
            )
        
        # Import multi downloader
        from ....services.playlist_service import multi_downloader
        
        # Create ZIP file
        playlist_name = playlist_info.get("title", f"Playlist_{download_id}")
        zip_path = multi_downloader.create_playlist_zip(files_info, playlist_name)
        
        if not zip_path:
            raise HTTPException(
                status_code=500,
                detail="Failed to create ZIP file"
            )
        
        # Update download info with ZIP path
        with multi_download_lock:
            multi_download_store[download_id]["zip_file"] = zip_path
        
        return {
            "success": True,
            "zip_file": zip_path,
            "download_url": f"/api/download-file/{os.path.basename(zip_path)}",
            "file_size": os.path.getsize(zip_path) if os.path.exists(zip_path) else 0,
            "message": "ZIP file created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating ZIP: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating ZIP: {str(e)}"
        )

@router.post("/cleanup/{download_id}")
async def cleanup_playlist_files(download_id: str, keep_zip: bool = True):
    """Clean up individual playlist files after ZIP creation."""
    try:
        # Get download info
        with multi_download_lock:
            if download_id not in multi_download_store:
                raise HTTPException(
                    status_code=404,
                    detail="Download ID not found"
                )
            
            download_info = multi_download_store[download_id]
        
        files_info = download_info.get("files_info", [])
        
        if not files_info:
            return {
                "success": True,
                "cleaned_files": 0,
                "message": "No files to clean up"
            }
        
        # Import multi downloader
        from ....services.playlist_service import multi_downloader
        
        # Clean up files
        cleaned_count = multi_downloader.cleanup_after_zip(files_info, keep_zip)
        
        return {
            "success": True,
            "cleaned_files": cleaned_count,
            "message": f"Cleaned up {cleaned_count} files"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up files: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error cleaning up: {str(e)}"
        )

@router.post("/move-external/{download_id}")
async def move_files_external(download_id: str, external_dir: str):
    """Move playlist files to external directory."""
    try:
        # Get download info
        with multi_download_lock:
            if download_id not in multi_download_store:
                raise HTTPException(
                    status_code=404,
                    detail="Download ID not found"
                )
            
            download_info = multi_download_store[download_id]
        
        files_info = download_info.get("files_info", [])
        
        if not files_info:
            return {
                "success": True,
                "moved_files": [],
                "message": "No files to move"
            }
        
        # Import multi downloader
        from ....services.playlist_service import multi_downloader
        
        # Move files
        moved_files = multi_downloader.move_files_to_external(files_info, external_dir)
        
        return {
            "success": True,
            "moved_files": moved_files,
            "count": len(moved_files),
            "message": f"Moved {len(moved_files)} files to {external_dir}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error moving files: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error moving files: {str(e)}"
        )

@router.get("/settings/external-dir")
async def get_external_directory():
    """Get current external directory setting."""
    try:
        from ...settings import settings
        return {
            "success": True,
            "external_dir": settings.external_storage_dir,
            "auto_cleanup": settings.auto_cleanup_after_zip
        }
    except Exception as e:
        logger.error(f"Error getting external directory: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting settings: {str(e)}"
        )

@router.post("/settings/auto-cleanup/{download_id}")
async def auto_cleanup_after_download(download_id: str):
    """Automatically create ZIP and cleanup files after successful download."""
    try:
        from ...settings import settings
        
        if not settings.auto_cleanup_after_zip:
            return {
                "success": False,
                "message": "Auto cleanup is disabled"
            }
        
        # Get download info
        with multi_download_lock:
            if download_id not in multi_download_store:
                raise HTTPException(
                    status_code=404,
                    detail="Download ID not found"
                )
            
            download_info = multi_download_store[download_id]
        
        # Check if download is completed
        if download_info.get("overall_status") != "completed":
            return {
                "success": False,
                "message": "Download not completed yet"
            }
        
        # Create ZIP
        playlist_info = download_info.get("playlist_info", {})
        playlist_name = playlist_info.get("title", f"Playlist_{download_id}")
        files_info = download_info.get("files_info", [])
        
        if not files_info:
            return {
                "success": False,
                "message": "No files to process"
            }
        
        # Import multi downloader
        from ....services.playlist_service import multi_downloader
        
        # Create ZIP
        zip_path = multi_downloader.create_playlist_zip(files_info, playlist_name)
        
        if zip_path:
            # Update download info with ZIP path
            with multi_download_lock:
                multi_download_store[download_id]["zip_file"] = zip_path
            
            # Cleanup individual files (keep ZIP)
            cleaned_count = multi_downloader.cleanup_after_zip(files_info, keep_zip=True)
            
            return {
                "success": True,
                "zip_file": zip_path,
                "cleaned_files": cleaned_count,
                "message": f"Auto-cleanup completed: ZIP created, {cleaned_count} files cleaned"
            }
        else:
            return {
                "success": False,
                "message": "Failed to create ZIP file"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in auto cleanup: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error in auto cleanup: {str(e)}"
        )
