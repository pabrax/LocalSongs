"""
Download API endpoints for music downloading service.

Provides endpoints for downloading audio from YouTube and Spotify platforms
with configurable quality settings and comprehensive error handling.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import Dict, Any
import os
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import signal

from ....services.download_service import downloader, AudioQuality, DownloadService
from ....services.playlist_service import multi_downloader, PlaylistService
from .progress import create_progress_tracker, ProgressTracker
from .multi_download import create_multi_download_tracker, MultiFileProgressTracker
from ....schemas.models import (
    DownloadRequest, 
    DownloadResponse, 
    AudioInfoResponse, 
    HealthResponse,
    AudioQualityRequest
)
from ....core.utils import URLValidator, QualityManager, FileUtils

logger = logging.getLogger(__name__)
router = APIRouter()

# Thread pool for blocking operations
executor = ThreadPoolExecutor(max_workers=2)

@router.post("/download", response_model=DownloadResponse)
async def download_audio(request: DownloadRequest) -> DownloadResponse:
    """
    Download audio from Spotify or YouTube Music.
    
    Args:
        request: Download request containing URL and quality settings
        
    Returns:
        DownloadResponse with success status and file information
        
    Raises:
        HTTPException: For invalid URLs, unsupported platforms, or download failures
    """
    try:
        # Validar URL
        is_valid, platform = URLValidator.is_valid_url(request.url)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail="URL no válida o plataforma no soportada"
            )
        
        # Validar calidad
        if not QualityManager.is_valid_quality(request.quality.value):
            raise HTTPException(
                status_code=400,
                detail=f"Calidad no válida: {request.quality.value}"
            )
        
        logger.info(f"Iniciando descarga: {request.url} con calidad {request.quality.value}")
        
        # Crear tracker de progreso
        download_id = create_progress_tracker()
        progress_tracker = ProgressTracker(download_id)
        
        # Convertir calidad de request a enum interno
        quality_map = {
            "96": AudioQuality.LOW,
            "128": AudioQuality.MEDIUM,
            "192": AudioQuality.HIGH,
            "320": AudioQuality.BEST
        }
        quality = quality_map[request.quality.value]
        
        # Realizar descarga con timeout usando asyncio
        try:
            # Ejecutar la descarga en un thread pool con timeout
            loop = asyncio.get_event_loop()
            
            # Crear una función wrapper que no use asyncio internamente
            def download_wrapper():
                return downloader.download_audio(request.url, quality, progress_tracker)
            
            # Timeout de 5 minutos para la descarga
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    executor, 
                    download_wrapper
                ),
                timeout=300.0  # 5 minutos
            )
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout en descarga de: {request.url}")
            raise HTTPException(
                status_code=408,
                detail="La descarga excedió el tiempo límite (5 minutos). Intenta con un video más corto."
            )
        except Exception as e:
            logger.error(f"Error en thread pool: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error durante la descarga: {str(e)}"
            )
        
        if result.success:
            logger.info(f"Descarga exitosa: {result.file_path}")
            
            # Post-procesamiento: asegurar que el archivo no tenga extensión problemática
            clean_file_path = result.file_path
            if result.file_path and result.file_path.endswith('.mp3_'):
                try:
                    clean_file_path = result.file_path.replace('.mp3_', '.mp3')
                    import os
                    os.rename(result.file_path, clean_file_path)
                    logger.info(f"Extensión corregida en post-procesamiento: {clean_file_path}")
                except Exception as e:
                    logger.error(f"Error corrigiendo extensión en post-procesamiento: {e}")
                    clean_file_path = result.file_path
            
            return DownloadResponse(
                success=True,
                message="Descarga completada exitosamente",
                file_path=clean_file_path,
                file_size=result.file_size,
                metadata=result.metadata,
                download_id=download_id  # Incluir ID de descarga para tracking
            )
        else:
            logger.error(f"Error en descarga: {result.error}")
            raise HTTPException(
                status_code=500,
                detail=f"Error en la descarga: {result.error}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado en descarga: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get("/info", response_model=AudioInfoResponse)
async def get_audio_info(url: str) -> AudioInfoResponse:
    """
    Obtener información del audio sin descargarlo
    """
    try:
        # Validar URL
        is_valid, platform = URLValidator.is_valid_url(url)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail="URL no válida o plataforma no soportada"
            )
        
        logger.info(f"Obteniendo información de: {url}")
        
        # Obtener información con timeout
        try:
            loop = asyncio.get_event_loop()
            
            # Timeout de 30 segundos para obtener info
            info = await asyncio.wait_for(
                loop.run_in_executor(
                    executor, 
                    downloader.get_audio_info, 
                    url
                ),
                timeout=30.0  # 30 segundos
            )
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout obteniendo info de: {url}")
            return AudioInfoResponse(
                success=False,
                error="Timeout al obtener información del video. Intenta nuevamente."
            )
        except Exception as e:
            logger.error(f"Error obteniendo info: {e}")
            return AudioInfoResponse(
                success=False,
                error=f"Error al obtener información: {str(e)}"
            )
        
        if info.get('success'):
            return AudioInfoResponse(
                success=True,
                title=info.get('title'),
                artist=info.get('artist'),
                album=info.get('album'),
                duration=info.get('duration'),
                platform=info.get('platform'),
                view_count=info.get('view_count'),
                thumbnail_url=info.get('thumbnail_url')
            )
        else:
            return AudioInfoResponse(
                success=False,
                error=info.get('error', 'Error desconocido')
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo información: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Verificar estado de los servicios
    """
    try:
        health = downloader.health_check()
        return HealthResponse(
            status=health['status'],
            message=health['message'],
            services=health['services']
        )
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return HealthResponse(
            status="error",
            message=f"Error verificando servicios: {str(e)}",
            services={}
        )

@router.get("/qualities")
async def get_available_qualities() -> Dict[str, Any]:
    """
    Obtener calidades de audio disponibles
    """
    qualities = QualityManager.get_available_qualities()
    quality_info = {}
    
    for quality in qualities:
        quality_info[quality] = {
            "bitrate": QualityManager.get_bitrate(quality),
            "description": QualityManager.get_description(quality)
        }
    
    return {
        "available_qualities": quality_info,
        "default_quality": "192"
    }

@router.get("/download-file/{filename}")
async def download_file(filename: str) -> FileResponse:
    """
    Descargar archivo previamente procesado
    """
    try:
        file_path = os.path.join(downloader.output_dir, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail="Archivo no encontrado"
            )
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='audio/mpeg'
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error descargando archivo: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get("/test-url")
async def test_url_validation(url: str) -> Dict[str, Any]:
    """
    Probar validación de URL (endpoint de debug)
    """
    try:
        is_valid, platform = URLValidator.is_valid_url(url)
        
        return {
            "url": url,
            "is_valid": is_valid,
            "platform": platform,
            "spotify_check": URLValidator.is_valid_spotify_url(url),
            "youtube_check": URLValidator.is_valid_youtube_url(url)
        }
    except Exception as e:
        logger.error(f"Error en test de URL: {e}")
        return {
            "url": url,
            "error": str(e)
        }

@router.get("/test-filename")
async def test_filename_format(title: str, artist: str = None, quality: str = "192") -> Dict[str, Any]:
    """
    Probar formato de nombres de archivo (endpoint de debug)
    """
    try:
        # Formatear título
        clean_title = FileUtils.format_song_title(title, artist)
        
        # Generar nombre de archivo
        filename = FileUtils.generate_filename(title, artist, quality)
        
        return {
            "original_title": title,
            "artist": artist,
            "quality": quality,
            "clean_title": clean_title,
            "final_filename": filename
        }
    except Exception as e:
        logger.error(f"Error en test de filename: {e}")
        return {
            "error": str(e)
        }

@router.post("/download-with-progress")
async def download_with_progress(request: DownloadRequest) -> Dict[str, str]:
    """
    Iniciar descarga con seguimiento de progreso.
    Retorna un download_id para hacer seguimiento del progreso.
    """
    try:
        # Validar URL
        is_valid, platform = URLValidator.is_valid_url(request.url)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail="URL no válida o plataforma no soportada"
            )
        
        # Validar calidad
        if not QualityManager.is_valid_quality(request.quality.value):
            raise HTTPException(
                status_code=400,
                detail=f"Calidad no válida: {request.quality.value}"
            )
        
        # Crear tracker de progreso
        download_id = create_progress_tracker()
        
        # Iniciar descarga en background
        async def background_download():
            try:
                progress_tracker = ProgressTracker(download_id)
                
                # Convertir calidad
                quality_map = {
                    "96": AudioQuality.LOW,
                    "128": AudioQuality.MEDIUM,
                    "192": AudioQuality.HIGH,
                    "320": AudioQuality.BEST
                }
                quality = quality_map[request.quality.value]
                
                # Ejecutar descarga
                loop = asyncio.get_event_loop()
                
                def download_wrapper():
                    return downloader.download_audio(request.url, quality, progress_tracker)
                
                result = await loop.run_in_executor(
                    executor,
                    download_wrapper
                )
                
                if not result.success:
                    progress_tracker.update(0, "error", f"Error: {result.error}", result.error)
                
            except Exception as e:
                logger.error(f"Error en descarga background: {e}")
                progress_tracker = ProgressTracker(download_id)
                progress_tracker.update(0, "error", f"Error: {str(e)}", str(e))
        
        # Ejecutar en background
        asyncio.create_task(background_download())
        
        return {
            "download_id": download_id,
            "message": "Descarga iniciada. Usa el download_id para hacer seguimiento del progreso.",
            "progress_url": f"/api/v1/progress-stream/{download_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error iniciando descarga con progreso: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get("/playlist-info")
async def get_playlist_info(url: str) -> Dict[str, Any]:
    """
    Obtener información de un playlist/album sin descargarlo
    """
    try:
        # Validar URL
        is_valid, platform = URLValidator.is_valid_url(url)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail="URL no válida o plataforma no soportada"
            )
        
        logger.info(f"Obteniendo información de playlist: {url}")
        
        # Obtener información del playlist
        success, info = multi_downloader.get_playlist_info(url)
        
        if success:
            return {
                "success": True,
                "info": info
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=info.get("error", "No se pudo obtener información del playlist")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo información de playlist: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.post("/download-playlist")
async def download_playlist_with_progress(request: DownloadRequest) -> Dict[str, Any]:
    """
    Iniciar descarga de playlist/album con seguimiento de progreso.
    Retorna un download_id para hacer seguimiento del progreso multi-archivo.
    """
    try:
        logger.info(f"Iniciando descarga de playlist: {request.url}")
        
        # Validar URL
        is_valid, platform = URLValidator.is_valid_url(request.url)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail="URL no válida o plataforma no soportada"
            )
        
        # Validar calidad
        if not QualityManager.is_valid_quality(request.quality.value):
            raise HTTPException(
                status_code=400,
                detail=f"Calidad no válida: {request.quality.value}"
            )
        
        # Obtener información del playlist primero
        try:
            success, info = multi_downloader.get_playlist_info(request.url)
            logger.info(f"Información de playlist obtenida: success={success}, info={info}")
        except Exception as e:
            logger.error(f"Error obteniendo información de playlist: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error obteniendo información del playlist: {str(e)}"
            )
        
        if not success:
            error_msg = info.get("error", "No se pudo obtener información del playlist") if isinstance(info, dict) else "Error desconocido"
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )
        
        total_files = info.get("total_tracks", 0)
        if total_files == 0:
            raise HTTPException(
                status_code=400,
                detail="No se encontraron tracks en el playlist/album"
            )
        
        # Crear tracker de progreso multi-archivo
        download_id = create_multi_download_tracker(total_files)
        logger.info(f"Creado tracker multi-download: {download_id} para {total_files} archivos")
        
        # Iniciar descarga en background
        async def background_multi_download():
            try:
                logger.info(f"Iniciando descarga múltiple en background para {download_id}")
                progress_tracker = MultiFileProgressTracker(download_id, total_files)
                
                # Convertir calidad
                quality_map = {
                    "96": AudioQuality.LOW,
                    "128": AudioQuality.MEDIUM,
                    "192": AudioQuality.HIGH,
                    "320": AudioQuality.BEST
                }
                quality = quality_map[request.quality.value]
                
                # Ejecutar descarga múltiple
                loop = asyncio.get_event_loop()
                
                def multi_download_wrapper():
                    try:
                        return multi_downloader.download_multiple(request.url, quality, progress_tracker)
                    except Exception as e:
                        logger.error(f"Error en multi_download_wrapper: {e}")
                        return type('Result', (), {'success': False, 'error': str(e)})()
                
                result = await loop.run_in_executor(
                    executor,
                    multi_download_wrapper
                )
                
                if not result.success:
                    logger.error(f"Descarga múltiple falló: {result.error}")
                    progress_tracker.update_overall("error", f"Error: {result.error}", result.error)
                else:
                    logger.info(f"Descarga múltiple completada exitosamente: {download_id}")
                    progress_tracker.update_overall("completed", "Descarga completada exitosamente")
                    
                    # Store files info in the tracker for ZIP creation
                    if hasattr(result, 'files') and result.files:
                        from .multi_download import multi_download_store, multi_download_lock
                        with multi_download_lock:
                            if download_id in multi_download_store:
                                multi_download_store[download_id]["files_info"] = result.files
                                logger.info(f"Stored {len(result.files)} files info for download {download_id}")
                        
                        # Trigger auto-cleanup if enabled
                        try:
                            from ...settings import settings
                            if settings.auto_cleanup_after_zip:
                                # Make a request to auto-cleanup endpoint
                                import aiohttp
                                async with aiohttp.ClientSession() as session:
                                    async with session.post(f"http://localhost:8000/api/settings/auto-cleanup/{download_id}") as resp:
                                        if resp.status == 200:
                                            logger.info(f"Auto-cleanup triggered for {download_id}")
                                        else:
                                            logger.warning(f"Auto-cleanup failed for {download_id}")
                        except Exception as auto_cleanup_error:
                            logger.error(f"Error triggering auto-cleanup: {auto_cleanup_error}")
                
            except Exception as e:
                logger.error(f"Error en descarga múltiple background: {e}")
                try:
                    progress_tracker = MultiFileProgressTracker(download_id, total_files)
                    progress_tracker.update_overall("error", f"Error: {str(e)}", str(e))
                except Exception as tracker_error:
                    logger.error(f"Error actualizando tracker: {tracker_error}")
        
        # Ejecutar en background
        asyncio.create_task(background_multi_download())
        
        response = {
            "download_id": download_id,
            "message": f"Descarga de playlist iniciada. {total_files} archivos. Usa el download_id para hacer seguimiento del progreso.",
            "progress_url": f"/api/v1/multi-progress-stream/{download_id}",
            "total_files": total_files,
            "playlist_info": info,
            "success": True
        }
        
        logger.info(f"Respuesta de descarga playlist: {response}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error iniciando descarga de playlist: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get("/list-files")
async def list_downloaded_files(folder: str = None) -> Dict[str, Any]:
    """
    Listar archivos descargados en una carpeta específica o en el directorio raíz
    """
    try:
        downloads_dir = downloader.output_dir
        
        if folder:
            # Buscar carpeta específica
            target_dir = os.path.join(downloads_dir, folder)
        else:
            target_dir = downloads_dir
            
        if not os.path.exists(target_dir):
            return {
                "success": False,
                "error": f"Folder not found: {folder}",
                "files": [],
                "count": 0
            }
        
        files = []
        for file_name in os.listdir(target_dir):
            file_path = os.path.join(target_dir, file_name)
            if os.path.isfile(file_path) and file_name.endswith(('.mp3', '.wav', '.flac', '.m4a')):
                file_size = os.path.getsize(file_path)
                files.append({
                    "name": file_name,
                    "size": file_size,
                    "path": file_path,
                    "folder": folder
                })
        
        # Ordenar por nombre
        files.sort(key=lambda x: x["name"])
        
        return {
            "success": True,
            "files": files,
            "count": len(files),
            "folder": folder
        }
        
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.post("/fix-extensions")
async def fix_file_extensions() -> Dict[str, Any]:
    """
    Corregir extensiones problemáticas en el directorio de descargas
    """
    try:
        from ...utils import FileUtils
        
        fixed_count = FileUtils.fix_all_extensions_in_directory(downloader.output_dir)
        
        return {
            "message": f"Extensiones corregidas exitosamente",
            "files_fixed": fixed_count,
            "directory": downloader.output_dir
        }
    except Exception as e:
        logger.error(f"Error corrigiendo extensiones: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error corrigiendo extensiones: {str(e)}"
        )

@router.delete("/cleanup")
async def cleanup_files() -> Dict[str, str]:
    """
    Limpiar archivos temporales
    """
    try:
        downloader.cleanup()
        return {"message": "Archivos temporales limpiados exitosamente"}
    except Exception as e:
        logger.error(f"Error limpiando archivos: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error limpiando archivos: {str(e)}"
        )