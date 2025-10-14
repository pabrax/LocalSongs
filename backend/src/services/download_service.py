"""
Music Download Service

Handles downloading music from Spotify and YouTube platforms with
high-quality audio extraction and consistent file naming.
"""

import os
import tempfile
import shutil
import subprocess
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from enum import Enum

import yt_dlp

from ..core.utils import URLValidator, FileUtils, QualityManager, ErrorHandler
from ..core.config import settings

logger = logging.getLogger(__name__)

class AudioQuality(Enum):
    """Audio quality options with corresponding bitrates."""
    LOW = "96"      # 96 kbps
    MEDIUM = "128"  # 128 kbps  
    HIGH = "192"    # 192 kbps (default)
    BEST = "320"    # 320 kbps


class Platform(Enum):
    """Supported music platforms."""
    SPOTIFY = "spotify"
    YOUTUBE = "youtube"
    YOUTUBE_MUSIC = "youtube_music"


class DownloadResult:
    """Container for download operation results."""
    
    def __init__(self, success: bool, file_path: Optional[str] = None, 
                 error: Optional[str] = None, metadata: Optional[Dict] = None,
                 file_size: Optional[int] = None):
        self.success = success
        self.file_path = file_path
        self.error = error
        self.metadata = metadata or {}
        self.file_size = file_size

class MusicDownloader:
    """
    Main controller for downloading music from different platforms.
    
    Supports YouTube (direct + Music) and Spotify with timeout management,
    URL validation, and automatic file cleanup. Provides configurable audio
    quality and comprehensive error handling.
    
    Features:
    - Multi-platform support (YouTube, YouTube Music, Spotify)
    - Configurable audio quality (96-320 kbps)
    - Automatic file extension and naming cleanup
    - Comprehensive error handling and logging
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """Initialize downloader with output directory and spotdl configuration."""
        self.output_dir = output_dir or settings.default_output_dir
        FileUtils.ensure_directory(self.output_dir)
        
        # Setup spotdl
        self._setup_spotdl()
        
    def _setup_spotdl(self):
        """Configure spotdl without credentials (using public mode)."""
        try:
            # SpotDL can work without credentials for many functions
            # using YouTube as audio source
            logger.info("Configuring SpotDL in public mode (no credentials)")
            self.spotdl_available = True
        except Exception as e:
            logger.error(f"Error configuring spotdl: {e}")
            self.spotdl_available = False
    
    def detect_platform(self, url: str) -> Platform:
        """Detect the platform based on the URL."""
        is_valid, platform_type = URLValidator.is_valid_url(url)
        
        if not is_valid:
            raise ValueError(ErrorHandler.get_error_message("invalid_url"))
        
        platform_map = {
            "spotify": Platform.SPOTIFY,
            "youtube": Platform.YOUTUBE,
            "youtube_music": Platform.YOUTUBE_MUSIC
        }
        
        return platform_map[platform_type]
    
    def _get_output_filename(self, title: str, artist: str, quality: str) -> str:
        """Generate output filename with proper formatting."""
        return FileUtils.generate_filename(title, artist, quality, "mp3")
    
    def download_from_spotify(self, url: str, quality: AudioQuality, progress_tracker=None) -> DownloadResult:
        """
        Download music from Spotify using spotdl directly as subprocess.
        
        Args:
            url: Spotify track/album/playlist URL
            quality: Audio quality enum (96-320 kbps)
            
        Returns:
            DownloadResult with success status, file path, and metadata
        """
        try:
            # Import the new Spotify service
            from .spotify_service import spotify_downloader
            
            if progress_tracker:
                progress_tracker.update(5, "preparing", "Preparando descarga de Spotify...")
            
            logger.info(f"Downloading from Spotify using simplified spotdl: {url}")
            
            # Use the new simplified Spotify downloader
            result = spotify_downloader.download(url, quality, progress_tracker)
            
            if result.success:
                logger.info(f"Spotify download successful: {result.file_path}")
            else:
                logger.error(f"Spotify download failed: {result.error}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in Spotify download: {e}")
            if progress_tracker:
                progress_tracker.update(0, "error", f"Error: {str(e)}")
            
            return DownloadResult(
                success=False,
                error=f"Error descargando desde Spotify: {str(e)}"
            )
    
    def download_from_youtube(self, url: str, quality: AudioQuality, progress_tracker=None) -> DownloadResult:
        """
        Download music from YouTube/YouTube Music using yt-dlp.
        
        Args:
            url: YouTube video/playlist URL
            quality: Audio quality enum (96-320 kbps)
            
        Returns:
            DownloadResult with success status, file path, and metadata
        """
        try:
            # Clean URL to extract only individual video (remove playlist params)
            from ..core.utils import URLValidator
            cleaned_url = URLValidator.clean_youtube_url(url)
            
            if cleaned_url != url:
                logger.info(f"Cleaned URL from {url} to {cleaned_url}")
                url = cleaned_url
            
            # Update progress
            if progress_tracker:
                progress_tracker.update(5, "preparing", "Preparando descarga de YouTube...")
                
                # Check for cancellation
                if hasattr(progress_tracker, 'is_cancelled') and progress_tracker.is_cancelled():
                    return DownloadResult(success=False, error="Descarga cancelada por el usuario")
            
            logger.info(f"Downloading from YouTube: {url} with quality {quality.value}")
            
            # Temporary name to avoid conflicts
            temp_template = os.path.join(self.output_dir, 'temp_%(title)s.%(ext)s')
            
            # Progress hook for yt-dlp
            def progress_hook(d):
                if progress_tracker and d['status'] == 'downloading':
                    # Check for cancellation before updating progress
                    if hasattr(progress_tracker, 'is_cancelled') and progress_tracker.is_cancelled():
                        raise Exception("Descarga cancelada por el usuario")
                        
                    if 'total_bytes' in d and d['total_bytes']:
                        downloaded = d.get('downloaded_bytes', 0)
                        total = d['total_bytes']
                        percentage = int((downloaded / total) * 60) + 10  # 10-70% for download
                        progress_tracker.update(percentage, "downloading", f"Descargando: {percentage-10}/60%")
                    elif '_percent_str' in d:
                        # Fallback to yt-dlp's percentage string
                        percent_str = d['_percent_str'].strip().replace('%', '')
                        try:
                            percent = int(float(percent_str))
                            progress = min(int(percent * 0.6) + 10, 70)  # Scale to 10-70%
                            progress_tracker.update(progress, "downloading", f"Descargando: {percent}%")
                        except:
                            pass
                elif progress_tracker and d['status'] == 'finished':
                    progress_tracker.update(70, "converting", "Convirtiendo a MP3...")

            # Configure yt-dlp options with timeouts and best settings
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': temp_template,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': quality.value,
                }],
                'postprocessor_args': [
                    '-ar', '44100',  # Sample rate
                ],
                'prefer_ffmpeg': True,
                'keepvideo': False,
                'quiet': False,  # Changed to see more information
                'no_warnings': False,  # Changed for debugging
                'progress_hooks': [progress_hook],  # Add progress hook
                # Timeout and network configurations
                'socket_timeout': 30,  # Socket timeout
                'fragment_retries': 3,  # Fragment retries
                'retries': 3,  # General retries
                'file_access_retries': 3,  # File access retries
                'http_chunk_size': 10485760,  # 10MB chunks
                # Additional configurations to avoid hangs
                'extractor_retries': 3,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'writedescription': False,
                'writeinfojson': False,
                'writethumbnail': False,
                # Headers to avoid blocks
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info("Extracting video information...")
                # Get video information with timeout
                try:
                    info = ydl.extract_info(url, download=False)
                except Exception as e:
                    logger.error(f"Error extracting information: {e}")
                    return DownloadResult(
                        success=False,
                        error=f"Error getting video information: {str(e)}"
                    )
                
                if not info:
                    return DownloadResult(
                        success=False,
                        error="Could not get video information"
                    )
                
                title = info.get('title', 'Unknown')
                uploader = info.get('uploader', 'Unknown')
                duration = info.get('duration', 0)
                
                logger.info(f"Video found: '{title}' by {uploader} ({duration}s)")
                
                # Check if video is too long (more than 20 minutes)
                if duration and duration > 1200:  # 20 minutes
                    logger.warning(f"Very long video ({duration}s), this may take time...")
                
                # Download with improved error handling
                logger.info("Starting download...")
                try:
                    ydl.download([url])
                    logger.info("Download completed")
                except Exception as e:
                    logger.error(f"Error during download: {e}")
                    return DownloadResult(
                        success=False,
                        error=f"Error during download: {str(e)}"
                    )
                
                # Update progress
                if progress_tracker:
                    progress_tracker.update(85, "finalizing", "Finalizando descarga...")
                
                # Find downloaded file and rename it
                temp_file = None
                for file in os.listdir(self.output_dir):
                    if file.startswith('temp_') and (file.endswith('.mp3') or file.endswith('.mp3_')):
                        temp_file = os.path.join(self.output_dir, file)
                        # Clean problematic extension if exists
                        temp_file = FileUtils.clean_file_extension(temp_file)
                        break
                
                if not temp_file or not os.path.exists(temp_file):
                    return DownloadResult(
                        success=False,
                        error="Downloaded file not found"
                    )
                
                # Rename with consistent format
                final_filename = self._get_output_filename(title, uploader, quality.value)
                final_path = os.path.join(self.output_dir, final_filename)
                
                try:
                    os.rename(temp_file, final_path)
                    file_path = final_path
                    logger.info(f"File renamed to: {final_filename}")
                except OSError as e:
                    logger.warning(f"Could not rename file: {e}")
                    file_path = temp_file
                
                file_size = FileUtils.get_file_size(file_path)
                
                metadata = {
                    "title": title,
                    "artist": uploader,
                    "duration": info.get('duration', 0),
                    "quality": quality.value,
                    "view_count": info.get('view_count', 0),
                    "upload_date": info.get('upload_date', ''),
                    "platform": "youtube_music" if "music.youtube.com" in url else "youtube",
                    "file_hash": FileUtils.get_file_hash(file_path)
                }
                
                # Update progress - completed
                filename = os.path.basename(file_path)
                if progress_tracker:
                    progress_tracker.update(100, "completed", f"Descarga completada: {filename}", None, filename)
                
                return DownloadResult(
                    success=True,
                    file_path=file_path,
                    metadata=metadata,
                    file_size=file_size
                )
                
        except Exception as e:
            logger.error(f"Error downloading from YouTube: {e}")
            return DownloadResult(success=False, error=str(e))
    
    def download_audio(self, url: str, quality: AudioQuality = AudioQuality.HIGH, progress_tracker=None) -> DownloadResult:
        """Main method to download audio from any supported platform."""
        try:
            # Validate URL
            is_valid, _ = URLValidator.is_valid_url(url)
            if not is_valid:
                return DownloadResult(
                    success=False,
                    error=ErrorHandler.get_error_message("invalid_url")
                )
            
            # Validate quality
            if not QualityManager.is_valid_quality(quality.value):
                return DownloadResult(
                    success=False,
                    error=ErrorHandler.get_error_message("quality_not_supported")
                )
            
            # Detect platform
            platform = self.detect_platform(url)
            logger.info(f"Platform detected: {platform.value}")
            
            # Clean directory if there are too many files
            FileUtils.clean_directory(self.output_dir, keep_files=20)
            
            # Download according to platform
            if platform == Platform.SPOTIFY:
                logger.info(f"Processing Spotify URL: {url}")
                result = self.download_from_spotify(url, quality, progress_tracker)
                if not result.success:
                    logger.error(f"Spotify download failed: {result.error}")
                return result
            elif platform in [Platform.YOUTUBE, Platform.YOUTUBE_MUSIC]:
                logger.info(f"Processing YouTube URL: {url}")
                result = self.download_from_youtube(url, quality, progress_tracker)
                if not result.success:
                    logger.error(f"YouTube download failed: {result.error}")
                return result
            else:
                return DownloadResult(
                    success=False,
                    error=ErrorHandler.get_error_message("platform_not_supported")
                )
                
        except ValueError as e:
            return DownloadResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"General download error: {e}")
            return DownloadResult(success=False, error=str(e))
    
    def get_audio_info(self, url: str) -> Dict[str, Any]:
        """Get audio information without downloading it."""
        try:
            is_valid, platform_type = URLValidator.is_valid_url(url)
            if not is_valid:
                return {"error": ErrorHandler.get_error_message("invalid_url")}
            
            if platform_type == "spotify":
                if not self.spotdl_available:
                    return {"error": "SpotDL is not available"}
                
                # For Spotify, for now we return basic information
                # since the meta API has changed
                return {
                    "success": True,
                    "title": "Spotify Track",
                    "artist": "Spotify Artist",
                    "album": "Unknown",
                    "duration": 0,
                    "platform": "spotify",
                    "note": "Complete information available after download"
                }
            
            elif platform_type in ["youtube", "youtube_music"]:
                ydl_opts = {
                    'quiet': False, 
                    'no_warnings': False,
                    'socket_timeout': 15,  # Shorter timeout for info
                    'retries': 2,
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                }
                
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        logger.info(f"Getting information from: {url}")
                        info = ydl.extract_info(url, download=False)
                        
                        if not info:
                            return {"error": "Could not get video information"}
                        
                        return {
                            "success": True,
                            "title": info.get('title', 'Unknown'),
                            "artist": info.get('uploader', 'Unknown'),
                            "duration": info.get('duration', 0),
                            "view_count": info.get('view_count', 0),
                            "platform": platform_type,
                            "thumbnail_url": info.get('thumbnail', '')
                        }
                except Exception as e:
                    logger.error(f"Error getting YouTube info: {e}")
                    return {"error": f"Error getting information: {str(e)}"}
            
            return {"error": ErrorHandler.get_error_message("platform_not_supported")}
            
        except Exception as e:
            logger.error(f"Error getting information: {e}")
            return {"error": str(e)}
    
    def get_available_qualities(self) -> list:
        """Get list of available qualities."""
        return QualityManager.get_available_qualities()
    
    def health_check(self) -> Dict[str, Any]:
        """Check service status."""
        services = {
            "spotify": self._test_spotdl_connection(),
            "youtube": self._test_youtube_connection(),
            "output_directory": os.path.exists(self.output_dir) and os.access(self.output_dir, os.W_OK)
        }
        
        all_healthy = all(services.values())
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "services": services,
            "message": "All services working" if all_healthy else "Some services unavailable"
        }
    
    def _test_spotdl_connection(self) -> bool:
        """Test if spotdl is available."""
        try:
            import subprocess
            # Check if we're in a uv environment
            if os.environ.get('VIRTUAL_ENV') or os.environ.get('UV_PROJECT_ENVIRONMENT'):
                cmd = ['uv', 'run', 'spotdl', '--version']
            else:
                cmd = ['spotdl', '--version']
                
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
    
    def _test_youtube_connection(self) -> bool:
        """Test YouTube connection with a lightweight check."""
        try:
            # Just check if yt-dlp is importable and working
            import yt_dlp
            return True  # If we can import yt-dlp, we consider YouTube "available"
                
        except Exception as e:
            logger.error(f"YouTube test error: {e}")
            return False
    
    def cleanup(self):
        """Limpiar archivos temporales"""
        try:
            FileUtils.clean_directory(self.output_dir, keep_files=0)
            logger.info("Archivos temporales limpiados")
        except Exception as e:
            logger.error(f"Error limpiando archivos temporales: {e}")

class DownloadService:
    """
    Service layer for music download operations.
    Provides a clean interface for download functionality.
    """
    
    def __init__(self):
        self._downloader = MusicDownloader()
    
    def download_audio(self, url: str, quality: str = "192", progress_tracker=None):
        """Download audio from supported platforms."""
        quality_enum = AudioQuality(quality)
        return self._downloader.download_audio(url, quality_enum, progress_tracker)
    
    def get_audio_info(self, url: str):
        """Get audio information without downloading."""
        return self._downloader.get_audio_info(url)
    
    def health_check(self):
        """Check service health."""
        return self._downloader.health_check()
    
    def cleanup(self):
        """Cleanup temporary files."""
        return self._downloader.cleanup()

# Legacy global instance for backward compatibility
downloader = MusicDownloader()