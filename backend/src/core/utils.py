import re
import os
import hashlib
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)

class URLValidator:
    """URL validator for different platforms."""
    
    SPOTIFY_PATTERNS = [
        r'https?://open\.spotify\.com/(track|album|playlist)/([a-zA-Z0-9]+)',
        r'https?://open\.spotify\.com/(track|album|playlist)/([a-zA-Z0-9]+)\?.*',  # With parameters
        r'https?://open\.spotify\.com/intl-[a-z]{2}/(track|album|playlist)/([a-zA-Z0-9]+)',  # International URLs
        r'https?://open\.spotify\.com/intl-[a-z]{2}/(track|album|playlist)/([a-zA-Z0-9]+)\?.*',  # International with parameters
        r'spotify:(track|album|playlist):([a-zA-Z0-9]+)'
    ]
    
    YOUTUBE_PATTERNS = [
        r'https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'https?://youtu\.be/([a-zA-Z0-9_-]+)',
        r'https?://(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)',
        r'https?://music\.youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'https?://music\.youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)'
    ]
    
    @staticmethod
    def is_valid_spotify_url(url: str) -> bool:
        """Validate if it's a valid Spotify URL."""
        logger.info(f"Validating Spotify URL: {url}")
        for pattern in URLValidator.SPOTIFY_PATTERNS:
            if re.match(pattern, url):
                logger.info(f"Valid Spotify URL with pattern: {pattern}")
                return True
        logger.warning(f"Invalid Spotify URL: {url}")
        return False
    
    @staticmethod
    def is_valid_youtube_url(url: str) -> bool:
        """Validate if it's a valid YouTube URL."""
        return any(re.match(pattern, url) for pattern in URLValidator.YOUTUBE_PATTERNS)
    
    @staticmethod
    def is_valid_url(url: str) -> Tuple[bool, Optional[str]]:
        """Validate URL and return platform type."""
        logger.info(f"Validating URL: {url}")
        
        if URLValidator.is_valid_spotify_url(url):
            logger.info("Detected as Spotify")
            return True, "spotify"
        elif URLValidator.is_valid_youtube_url(url):
            if "music.youtube.com" in url:
                logger.info("Detected as YouTube Music")
                return True, "youtube_music"
            else:
                logger.info("Detected as YouTube")
                return True, "youtube"
        
        logger.warning(f"Invalid or unsupported URL: {url}")
        return False, None

class FileUtils:
    """File handling utilities."""
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename."""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove additional special characters that can cause problems
        filename = filename.replace('&', 'and')
        filename = filename.replace('#', 'No')
        filename = filename.replace('@', 'at')
        filename = filename.replace('%', 'percent')
        
        # Remove multiple spaces and dashes
        filename = re.sub(r'\s+', ' ', filename)  # Multiple spaces to one
        filename = re.sub(r'-+', '-', filename)   # Multiple dashes to one
        filename = re.sub(r'_+', '_', filename)   # Multiple underscores to one
        
        # Limit length
        if len(filename) > 200:
            filename = filename[:200]
        
        return filename.strip()
    
    @staticmethod
    def format_song_title(title: str, artist: str = None, album: str = None) -> str:
        """Format song title in a cleaner way."""
        # Clean title
        clean_title = title
        
        # Remove common extra information in YouTube titles
        patterns_to_remove = [
            r'\(Official.*?\)',  # (Official Video), (Official Audio), etc.
            r'\[Official.*?\]',  # [Official Video], [Official Audio], etc.
            r'\(Audio\)',        # (Audio)
            r'\[Audio\]',        # [Audio]
            r'\(Video\)',        # (Video)
            r'\[Video\]',        # [Video]
            r'\(Lyric.*?\)',     # (Lyrics), (Lyric Video), etc.
            r'\[Lyric.*?\]',     # [Lyrics], [Lyric Video], etc.
            r'\(HD\)',           # (HD)
            r'\[HD\]',           # [HD]
            r'\(4K\)',           # (4K)
            r'\[4K\]',           # [4K]
            r'\(Remaster.*?\)',  # (Remastered), etc.
            r'\[Remaster.*?\]',  # [Remastered], etc.
            r'\(\d{4}\)',        # (2023), (2024), etc.
            r'\[\d{4}\]',        # [2023], [2024], etc.
        ]
        
        for pattern in patterns_to_remove:
            clean_title = re.sub(pattern, '', clean_title, flags=re.IGNORECASE)
        
        # Clean extra spaces
        clean_title = re.sub(r'\s+', ' ', clean_title).strip()
        
        # If we have artist, try to remove it from title if duplicated
        if artist:
            # Remove artist from title beginning if it's there
            if clean_title.lower().startswith(artist.lower()):
                clean_title = clean_title[len(artist):].strip()
                if clean_title.startswith('-'):
                    clean_title = clean_title[1:].strip()
            
            # Remove patterns like "Artist - Title" at the beginning
            artist_pattern = rf'^{re.escape(artist)}\s*-\s*'
            clean_title = re.sub(artist_pattern, '', clean_title, flags=re.IGNORECASE)
        
        return clean_title.strip()
    
    @staticmethod
    def generate_filename(title: str, artist: str = None, quality: str = "192", extension: str = "mp3") -> str:
        """Generate optimized filename."""
        # Format clean title
        clean_title = FileUtils.format_song_title(title, artist)
        
        # Format artist
        clean_artist = artist if artist else "Unknown Artist"
        clean_artist = FileUtils.sanitize_filename(clean_artist)
        
        # Create filename
        if clean_artist and clean_artist.lower() != "unknown artist":
            filename = f"{clean_artist} - {clean_title}"
        else:
            filename = clean_title
        
        # Sanitize complete filename
        filename = FileUtils.sanitize_filename(filename)
        
        # Add quality and extension
        filename = f"{filename} [{quality}kbps].{extension}"
        
        return filename
    
    @staticmethod
    def clean_file_extension(file_path: str) -> str:
        """Clean problematic extensions like .mp3_ -> .mp3."""
        if not os.path.exists(file_path):
            logger.warning(f"File does not exist: {file_path}")
            return file_path
            
        # Lista de extensiones problemáticas a corregir
        problematic_extensions = {
            ".mp3_": ".mp3",
            ".m4a_": ".m4a",
            ".wav_": ".wav",
            ".flac_": ".flac",
            ".ogg_": ".ogg"
        }
        
        for bad_ext, good_ext in problematic_extensions.items():
            if file_path.endswith(bad_ext):
                new_path = file_path.replace(bad_ext, good_ext)
                try:
                    # Verificar que el archivo destino no exista
                    if os.path.exists(new_path):
                        # Si existe, agregar un sufijo único
                        base, ext = os.path.splitext(new_path)
                        counter = 1
                        while os.path.exists(f"{base}_{counter}{ext}"):
                            counter += 1
                        new_path = f"{base}_{counter}{ext}"
                    
                    os.rename(file_path, new_path)
                    logger.info(f"Extension corrected: {os.path.basename(file_path)} -> {os.path.basename(new_path)}")
                    return new_path
                except OSError as e:
                    logger.error(f"Error correcting extension from {file_path} to {new_path}: {e}")
                    return file_path
        
        return file_path
    
    @staticmethod
    def fix_all_extensions_in_directory(directory: str) -> int:
        """Fix all problematic extensions in a directory. Returns number of files fixed."""
        fixed_count = 0
        try:
            if not os.path.exists(directory):
                return 0
                
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                if os.path.isfile(file_path):
                    original_path = file_path
                    fixed_path = FileUtils.clean_file_extension(file_path)
                    if fixed_path != original_path:
                        fixed_count += 1
                        
        except Exception as e:
            logger.error(f"Error fixing extensions in directory {directory}: {e}")
            
        return fixed_count

    @staticmethod
    def get_file_size(file_path: str) -> int:
        """Get file size in bytes."""
        try:
            return os.path.getsize(file_path)
        except OSError:
            return 0
    
    @staticmethod
    def get_file_hash(file_path: str) -> str:
        """Get MD5 hash of file."""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash: {e}")
            return ""
    
    @staticmethod
    def ensure_directory(path: str) -> None:
        """Ensure directory exists."""
        Path(path).mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def clean_directory(path: str, keep_files: int = 10) -> None:
        """Clean directory keeping only the most recent files."""
        try:
            if not os.path.exists(path):
                return
            
            files = []
            for file in os.listdir(path):
                file_path = os.path.join(path, file)
                if os.path.isfile(file_path):
                    files.append((file_path, os.path.getmtime(file_path)))
            
            # Sort by modification date (most recent first)
            files.sort(key=lambda x: x[1], reverse=True)
            
            # Remove old files
            for file_path, _ in files[keep_files:]:
                try:
                    os.remove(file_path)
                    logger.info(f"File deleted: {file_path}")
                except Exception as e:
                    logger.error(f"Error deleting file {file_path}: {e}")
                    
        except Exception as e:
            logger.error(f"Error cleaning directory {path}: {e}")
    
    @staticmethod
    def create_zip_archive(file_paths: List[str], zip_name: str, output_dir: str) -> Optional[str]:
        """
        Create a ZIP archive from a list of files.
        
        Args:
            file_paths: List of full paths to files to include
            zip_name: Name for the ZIP file (without extension)
            output_dir: Directory where to save the ZIP
            
        Returns:
            Full path to created ZIP file or None if failed
        """
        try:
            # Sanitize zip name
            safe_zip_name = FileUtils.sanitize_filename(zip_name)
            zip_filename = f"{safe_zip_name}.zip"
            zip_path = os.path.join(output_dir, zip_filename)
            
            # Create ZIP archive
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in file_paths:
                    if os.path.exists(file_path):
                        # Use just the filename in the archive (no directory structure)
                        arcname = os.path.basename(file_path)
                        zipf.write(file_path, arcname)
                        logger.info(f"Added to ZIP: {arcname}")
                    else:
                        logger.warning(f"File not found for ZIP: {file_path}")
            
            if os.path.exists(zip_path):
                logger.info(f"ZIP created successfully: {zip_path}")
                return zip_path
            else:
                logger.error("ZIP file was not created")
                return None
                
        except Exception as e:
            logger.error(f"Error creating ZIP archive: {e}")
            return None
    
    @staticmethod
    def cleanup_files(file_paths: List[str], keep_zip: bool = True) -> int:
        """
        Clean up files after ZIP creation.
        
        Args:
            file_paths: List of file paths to delete
            keep_zip: Whether to keep ZIP files during cleanup
            
        Returns:
            Number of files successfully deleted
        """
        deleted_count = 0
        
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    # Skip ZIP files if keep_zip is True
                    if keep_zip and file_path.endswith('.zip'):
                        continue
                        
                    os.remove(file_path)
                    deleted_count += 1
                    logger.info(f"Cleaned up file: {file_path}")
                    
            except Exception as e:
                logger.error(f"Error deleting file {file_path}: {e}")
        
        return deleted_count
    
    @staticmethod
    def move_files_to_external_dir(file_paths: List[str], external_dir: str) -> List[str]:
        """
        Move files to an external directory outside the backend.
        
        Args:
            file_paths: List of file paths to move
            external_dir: External directory path
            
        Returns:
            List of new file paths after moving
        """
        moved_files = []
        
        try:
            # Ensure external directory exists
            FileUtils.ensure_directory(external_dir)
            
            for file_path in file_paths:
                if os.path.exists(file_path):
                    filename = os.path.basename(file_path)
                    new_path = os.path.join(external_dir, filename)
                    
                    # Handle name conflicts
                    counter = 1
                    base_name, ext = os.path.splitext(filename)
                    while os.path.exists(new_path):
                        new_filename = f"{base_name}_{counter}{ext}"
                        new_path = os.path.join(external_dir, new_filename)
                        counter += 1
                    
                    try:
                        shutil.move(file_path, new_path)
                        moved_files.append(new_path)
                        logger.info(f"Moved file: {file_path} -> {new_path}")
                    except Exception as e:
                        logger.error(f"Error moving file {file_path}: {e}")
                        
        except Exception as e:
            logger.error(f"Error setting up external directory {external_dir}: {e}")
        
        return moved_files

class QualityManager:
    """Audio quality manager."""
    
    QUALITY_MAP = {
        "96": {"bitrate": "96k", "description": "Low quality"},
        "128": {"bitrate": "128k", "description": "Standard quality"},
        "192": {"bitrate": "192k", "description": "High quality"},
        "320": {"bitrate": "320k", "description": "Maximum quality"}
    }
    
    @staticmethod
    def is_valid_quality(quality: str) -> bool:
        """Validate if quality is valid."""
        return quality in QualityManager.QUALITY_MAP
    
    @staticmethod
    def get_bitrate(quality: str) -> str:
        """Get bitrate for specified quality."""
        return QualityManager.QUALITY_MAP.get(quality, {}).get("bitrate", "192k")
    
    @staticmethod
    def get_description(quality: str) -> str:
        """Get quality description."""
        return QualityManager.QUALITY_MAP.get(quality, {}).get("description", "Unknown quality")
    
    @staticmethod
    def get_available_qualities() -> list:
        """Get list of available qualities."""
        return list(QualityManager.QUALITY_MAP.keys())

class ErrorHandler:
    """Custom error handler."""
    
    ERROR_MESSAGES = {
        "invalid_url": "Invalid or unsupported URL",
        "platform_not_supported": "Platform not supported",
        "download_failed": "Error during download",
        "file_not_found": "File not found",
        "quality_not_supported": "Quality not supported",
        "spotify_config_error": "Spotify configuration error",
        "network_error": "Network connection error",
        "ffmpeg_error": "Audio conversion error",
        "permission_error": "File permission error",
        "disk_space_error": "Insufficient disk space"
    }
    
    @staticmethod
    def get_error_message(error_code: str, default: str = "Unknown error") -> str:
        """Get custom error message."""
        return ErrorHandler.ERROR_MESSAGES.get(error_code, default)