from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any
from enum import Enum

class AudioQualityRequest(str, Enum):
    """Calidades de audio disponibles para requests"""
    LOW = "96"
    MEDIUM = "128"
    HIGH = "192"
    BEST = "320"

class PlatformType(str, Enum):
    """Tipos de plataformas soportadas"""
    SPOTIFY = "spotify"
    YOUTUBE = "youtube"
    YOUTUBE_MUSIC = "youtube_music"

class DownloadRequest(BaseModel):
    """Modelo para solicitudes de descarga"""
    url: str
    quality: AudioQualityRequest = AudioQualityRequest.HIGH
    output_format: str = "mp3"

class AudioMetadata(BaseModel):
    """Metadatos del audio"""
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    duration: Optional[int] = None
    quality: Optional[str] = None
    platform: Optional[str] = None
    view_count: Optional[int] = None
    upload_date: Optional[str] = None
    file_hash: Optional[str] = None

class DownloadResponse(BaseModel):
    """Respuesta de descarga"""
    success: bool
    message: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class AudioInfoResponse(BaseModel):
    """Respuesta de información de audio"""
    success: bool
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    duration: Optional[int] = None
    platform: Optional[str] = None
    view_count: Optional[int] = None
    thumbnail_url: Optional[str] = None
    error: Optional[str] = None

class HealthResponse(BaseModel):
    """Respuesta de health check"""
    status: str
    message: str
    services: Dict[str, bool]