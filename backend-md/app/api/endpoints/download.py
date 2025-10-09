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

from ...controllers.downloader_controllers import downloader, AudioQuality
from ...models import (
    DownloadRequest, 
    DownloadResponse, 
    AudioInfoResponse, 
    HealthResponse,
    AudioQualityRequest
)
from ...utils import URLValidator, QualityManager
from ...utils import FileUtils

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
            
            # Timeout de 5 minutos para la descarga
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    executor, 
                    downloader.download_audio, 
                    request.url, 
                    quality
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
                metadata=result.metadata
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