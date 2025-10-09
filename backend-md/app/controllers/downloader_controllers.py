"""
Music Download Controller

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

from ..utils import URLValidator, FileUtils, QualityManager, ErrorHandler
from ..settings import settings

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
    
    def download_from_spotify(self, url: str, quality: AudioQuality) -> DownloadResult:
        """
        Download music from Spotify using spotdl with direct URL processing.
        
        Args:
            url: Spotify track/album/playlist URL
            quality: Audio quality enum (96-320 kbps)
            
        Returns:
            DownloadResult with success status, file path, and metadata
        """
        try:
            if not self.spotdl_available:
                return DownloadResult(
                    success=False, 
                    error="SpotDL is not available"
                )
            
            logger.info(f"Downloading from Spotify: {url} with quality {quality.value}")
            
            # Import required modules
            import subprocess
            import tempfile
            
            # Create temporary directory for this download
            temp_dir = tempfile.mkdtemp(prefix="spotify_download_")
            logger.info(f"Temporary directory created: {temp_dir}")
            
            # Direct download command - using temporary directory
            download_cmd = [
                "spotdl", "download", url,
                "--output", temp_dir,
                "--format", "mp3",
                "--bitrate", f"{quality.value}k",
                "--overwrite", "force"
            ]
            
            logger.info(f"Executing command: {' '.join(download_cmd)}")
            
            # Execute download
            result = subprocess.run(download_cmd, capture_output=True, text=True)
            
            logger.info(f"Spotdl exit code: {result.returncode}")
            if result.stdout:
                logger.info(f"Stdout: {result.stdout}")
            if result.stderr:
                logger.warning(f"Stderr: {result.stderr}")
            
            if result.returncode == 0:
                # Search for downloaded file in temporary directory
                downloaded_file = None
                temp_files = os.listdir(temp_dir)
                logger.info(f"Files in temporary directory: {temp_files}")
                
                for file in temp_files:
                    if file.endswith(".mp3"):
                        downloaded_file = os.path.join(temp_dir, file)
                        logger.info(f"MP3 file found: {file}")
                        break
                    elif file.endswith(".mp3_"):
                        # If spotdl creates file with mp3_, rename it immediately
                        old_path = os.path.join(temp_dir, file)
                        new_file = file.replace(".mp3_", ".mp3")
                        new_path = os.path.join(temp_dir, new_file)
                        os.rename(old_path, new_path)
                        downloaded_file = new_path
                        logger.info(f"MP3_ file renamed to: {new_file}")
                        break
                
                if downloaded_file and os.path.exists(downloaded_file):
                    # Get file information
                    file_size = FileUtils.get_file_size(downloaded_file)
                    temp_filename = os.path.basename(downloaded_file)
                    
                    logger.info(f"Processing downloaded file: {temp_filename}")
                    
                    # Clean filename to extract title and artist
                    clean_filename = temp_filename.replace(".mp3", "")
                    
                    # Try to extract artist and title from filename
                    if " - " in clean_filename:
                        parts = clean_filename.split(" - ", 1)
                        artist = parts[0].strip()
                        title = parts[1].strip()
                    else:
                        artist = "Unknown Artist"
                        title = clean_filename.strip()
                    
                    logger.info(f"Extracted metadata - Artist: '{artist}', Title: '{title}'")
                    
                    # Generate final filename with clean format
                    final_filename = self._get_output_filename(title, artist, quality.value)
                    final_path = os.path.join(self.output_dir, final_filename)
                    
                    # Move file from temporary directory to final directory
                    try:
                        import shutil
                        shutil.move(downloaded_file, final_path)
                        logger.info(f"File moved to: {final_filename}")
                        
                        # Clean up temporary directory
                        shutil.rmtree(temp_dir)
                        logger.info("Temporary directory cleaned up")
                        
                        file_path = final_path
                    except Exception as e:
                        logger.error(f"Error moving file: {e}")
                        # If move fails, use temporary file
                        file_path = downloaded_file
                    
                    metadata = {
                        "title": title,
                        "artist": artist,
                        "album": "Unknown",
                        "duration": 0,
                        "quality": quality.value,
                        "platform": "spotify",
                        "file_hash": FileUtils.get_file_hash(file_path)
                    }
                    
                    return DownloadResult(
                        success=True,
                        file_path=file_path,
                        metadata=metadata,
                        file_size=file_size
                    )
                else:
                    # Clean up temporary directory if no file found
                    try:
                        import shutil
                        shutil.rmtree(temp_dir)
                    except:
                        pass
                    
                    return DownloadResult(
                        success=False,
                        error="File was not created after download"
                    )
            else:
                # Clean up temporary directory on error
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                except:
                    pass
                
                error_msg = result.stderr or result.stdout or "Unknown spotdl error"
                return DownloadResult(
                    success=False,
                    error=f"Spotdl error: {error_msg}"
                )
                
        except Exception as e:
            logger.error(f"Error downloading from Spotify: {e}")
            return DownloadResult(success=False, error=str(e))
    
    def download_from_youtube(self, url: str, quality: AudioQuality) -> DownloadResult:
        """
        Download music from YouTube/YouTube Music using yt-dlp.
        
        Args:
            url: YouTube video/playlist URL
            quality: Audio quality enum (96-320 kbps)
            
        Returns:
            DownloadResult with success status, file path, and metadata
        """
        try:
            logger.info(f"Downloading from YouTube: {url} with quality {quality.value}")
            
            # Temporary name to avoid conflicts
            temp_template = os.path.join(self.output_dir, 'temp_%(title)s.%(ext)s')
            
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
                
                return DownloadResult(
                    success=True,
                    file_path=file_path,
                    metadata=metadata,
                    file_size=file_size
                )
                
        except Exception as e:
            logger.error(f"Error downloading from YouTube: {e}")
            return DownloadResult(success=False, error=str(e))
    
    def download_audio(self, url: str, quality: AudioQuality = AudioQuality.HIGH) -> DownloadResult:
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
                return self.download_from_spotify(url, quality)
            elif platform in [Platform.YOUTUBE, Platform.YOUTUBE_MUSIC]:
                return self.download_from_youtube(url, quality)
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
            result = subprocess.run(["spotdl", "--version"], capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False
    
    def _test_youtube_connection(self) -> bool:
        """Test YouTube connection."""
        try:
            ydl_opts = {
                'quiet': True, 
                'no_warnings': True,
                'socket_timeout': 10,
                'retries': 1,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Test with a public short test video
                test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # 10-second video
                info = ydl.extract_info(test_url, download=False)
                return info is not None
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

# Instancia global del downloader
downloader = MusicDownloader()