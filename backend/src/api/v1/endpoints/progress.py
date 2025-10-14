"""
Progress tracking endpoints for download operations.

Provides Server-Sent Events (SSE) for real-time progress updates during downloads.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from concurrent.futures import ThreadPoolExecutor
import threading

logger = logging.getLogger(__name__)
router = APIRouter()

# Global progress tracking
progress_store: Dict[str, Dict[str, Any]] = {}
progress_lock = threading.Lock()

class ProgressTracker:
    """Thread-safe progress tracker for download operations."""
    
    def __init__(self, download_id: str):
        self.download_id = download_id
        self.progress = 0
        self.status = "starting"
        self.message = "Iniciando descarga..."
        self.error = None
        self._cancelled = False
        
    def update(self, progress: int, status: str, message: str, error: Optional[str] = None, filename: Optional[str] = None):
        """Update progress information."""
        with progress_lock:
            progress_store[self.download_id] = {
                "progress": progress,
                "status": status,
                "message": message,
                "error": error,
                "filename": filename,
                "timestamp": time.time(),
                "cancelled": self._cancelled
            }
    
    def cancel(self):
        """Mark download as cancelled."""
        self._cancelled = True
        self.update(0, "cancelled", "Descarga cancelada", "Operación cancelada por el usuario")
    
    def is_cancelled(self) -> bool:
        """Check if download has been cancelled."""
        return self._cancelled
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current progress information."""
        with progress_lock:
            return progress_store.get(self.download_id, {
                "progress": 0,
                "status": "unknown",
                "message": "Estado desconocido",
                "error": None
            })
    
    def cleanup(self):
        """Clean up progress data."""
        with progress_lock:
            if self.download_id in progress_store:
                del progress_store[self.download_id]

def create_progress_tracker() -> str:
    """Create a new progress tracker and return its ID."""
    download_id = str(uuid.uuid4())
    tracker = ProgressTracker(download_id)
    tracker.update(0, "created", "Descarga creada")
    return download_id

def get_progress_tracker(download_id: str) -> Optional[ProgressTracker]:
    """Get existing progress tracker."""
    if download_id in progress_store:
        return ProgressTracker(download_id)
    return None

@router.get("/progress/{download_id}")
async def get_download_progress(download_id: str):
    """Get current progress for a download."""
    try:
        with progress_lock:
            progress_data = progress_store.get(download_id)
        
        if not progress_data:
            raise HTTPException(
                status_code=404,
                detail="Download ID not found"
            )
        
        return progress_data
    except Exception as e:
        logger.error(f"Error getting progress: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting progress: {str(e)}"
        )

@router.get("/progress-stream/{download_id}")
async def stream_download_progress(download_id: str):
    """Stream download progress using Server-Sent Events."""
    
    async def generate_progress_stream():
        """Generate SSE stream for progress updates."""
        try:
            last_progress = -1
            max_iterations = 600  # 10 minutes max (600 * 1 second)
            iteration = 0
            
            while iteration < max_iterations:
                with progress_lock:
                    progress_data = progress_store.get(download_id)
                
                if not progress_data:
                    # Send completion event if no data found
                    yield f"data: {json.dumps({'progress': 100, 'status': 'completed', 'message': 'Descarga completada'})}\n\n"
                    break
                
                # Only send update if progress changed
                current_progress = progress_data.get('progress', 0)
                if current_progress != last_progress or iteration == 0:
                    yield f"data: {json.dumps(progress_data)}\n\n"
                    last_progress = current_progress
                
                # Check if download is complete or failed
                status = progress_data.get('status', '')
                if status in ['completed', 'success']:
                    # Add download URL to completed progress
                    progress_data['download_url'] = f"/api/v1/download-zip/{download_id}"
                    progress_data['ready_for_download'] = True
                    yield f"data: {json.dumps(progress_data)}\n\n"
                    break
                elif status in ['error', 'failed']:
                    break
                
                await asyncio.sleep(1)  # Update every second
                iteration += 1
            
            # Send final completion event
            yield f"data: {json.dumps({'progress': 100, 'status': 'stream_ended', 'message': 'Stream finalizado'})}\n\n"
            
        except Exception as e:
            logger.error(f"Error in progress stream: {e}")
            error_data = {
                'progress': 0,
                'status': 'error',
                'message': f'Error en stream: {str(e)}',
                'error': str(e)
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        generate_progress_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@router.delete("/progress/{download_id}")
async def cleanup_progress(download_id: str):
    """Clean up progress data for a download."""
    try:
        with progress_lock:
            if download_id in progress_store:
                del progress_store[download_id]
                return {"message": "Progress data cleaned up"}
            else:
                raise HTTPException(
                    status_code=404,
                    detail="Download ID not found"
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up progress: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error cleaning up progress: {str(e)}"
        )

@router.get("/active-downloads")
async def get_active_downloads():
    """Get list of active downloads."""
    try:
        with progress_lock:
            active_downloads = {
                download_id: data for download_id, data in progress_store.items()
                if data.get('status') not in ['completed', 'success', 'error', 'failed', 'cancelled']
            }
        
        return {
            "active_downloads": active_downloads,
            "count": len(active_downloads)
        }
    except Exception as e:
        logger.error(f"Error getting active downloads: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting active downloads: {str(e)}"
        )

@router.post("/cancel/{download_id}")
async def cancel_download(download_id: str):
    """Cancel a download operation."""
    try:
        with progress_lock:
            if download_id in progress_store:
                # Mark as cancelled in the store
                progress_store[download_id]["status"] = "cancelled"
                progress_store[download_id]["message"] = "Descarga cancelada"
                progress_store[download_id]["cancelled"] = True
                
                logger.info(f"Download {download_id} marked as cancelled")
                return {"success": True, "message": "Descarga cancelada"}
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Download {download_id} not found"
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling download: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error cancelling download: {str(e)}"
        )
