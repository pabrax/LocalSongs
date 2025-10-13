"""
Playlist download service for albums and playlists.

Handles downloading multiple files with individual progress tracking and error handling.
"""

import os
import tempfile
import shutil
import subprocess
import logging
import json
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from enum import Enum

import yt_dlp

from ..core.utils import URLValidator, FileUtils, QualityManager, ErrorHandler
from ..core.config import settings
from .download_service import AudioQuality, Platform, DownloadResult, MusicDownloader

logger = logging.getLogger(__name__)

class MultiDownloadResult:
    """Result of a multi-file download operation."""
    
    def __init__(self, success: bool, total_files: int = 0, completed_files: int = 0, 
                 failed_files: int = 0, files: List[Dict[str, Any]] = None, 
                 error: str = None, download_folder: str = None):
        self.success = success
        self.total_files = total_files
        self.completed_files = completed_files
        self.failed_files = failed_files
        self.files = files or []
        self.error = error
        self.download_folder = download_folder

class MultiMusicDownloader:
    """Enhanced music downloader for albums and playlists."""
    
    def __init__(self):
        self.single_downloader = MusicDownloader()
        self.max_files_per_download = 50  # Safety limit
        self.max_concurrent_downloads = 1  # Sequential for now
        
    def get_playlist_info(self, url: str) -> Tuple[bool, Dict[str, Any]]:
        """Get information about a playlist/album without downloading."""
        try:
            # Validate URL first
            is_valid, platform = URLValidator.is_valid_url(url)
            if not is_valid:
                return False, {"error": "Invalid URL"}
            
            if platform == "spotify":
                return self._get_spotify_playlist_info(url)
            elif platform in ["youtube", "youtube_music"]:
                return self._get_youtube_playlist_info(url)
            else:
                return False, {"error": "Platform not supported for playlists"}
                
        except Exception as e:
            logger.error(f"Error getting playlist info: {e}")
            return False, {"error": str(e)}
    
    def _get_spotify_playlist_info(self, url: str) -> Tuple[bool, Dict[str, Any]]:
        """Get Spotify playlist/album information."""
        try:
            # Use spotdl save to get playlist info (save doesn't download, just lists)
            temp_file = f"/tmp/spotify_info_{os.getpid()}.txt"
            
            cmd = [
                "spotdl", "save", url, 
                "--save-file", temp_file,
                "--output", "{artist} - {name}"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(temp_file):
                # Read the saved file to get track list
                with open(temp_file, 'r', encoding='utf-8') as f:
                    tracks = [line.strip() for line in f.readlines() if line.strip()]
                
                # Clean up temp file
                try:
                    os.remove(temp_file)
                except:
                    pass
                
                # Determine if it's an album or playlist
                content_type = "album" if "/album/" in url else "playlist" if "/playlist/" in url else "track"
                
                # Extract title from URL or use default
                title = f"Spotify {content_type.title()}"
                if tracks:
                    # Try to extract a common artist or use first track info
                    first_track = tracks[0] if tracks else "Unknown"
                    if " - " in first_track:
                        artist_part = first_track.split(" - ")[0]
                        title = f"{artist_part} - {content_type.title()}"
                
                return True, {
                    "type": content_type,
                    "platform": "spotify",
                    "total_tracks": len(tracks),
                    "tracks": tracks[:self.max_files_per_download],  # Apply limit
                    "url": url,
                    "title": title,
                    "limited": len(tracks) > self.max_files_per_download
                }
            else:
                logger.error(f"Spotdl save error: {result.stderr}")
                # Fallback: try to determine basic info from URL
                content_type = "album" if "/album/" in url else "playlist" if "/playlist/" in url else "track"
                
                return True, {
                    "type": content_type,
                    "platform": "spotify",
                    "total_tracks": 1 if content_type == "track" else 10,  # Estimate
                    "tracks": [f"Track from Spotify {content_type}"],
                    "url": url,
                    "title": f"Spotify {content_type.title()}",
                    "limited": False
                }
                
        except subprocess.TimeoutExpired:
            return False, {"error": "Timeout getting Spotify playlist info"}
        except Exception as e:
            logger.error(f"Error getting Spotify playlist info: {e}")
            # Fallback for any error
            content_type = "album" if "/album/" in url else "playlist" if "/playlist/" in url else "track"
            return True, {
                "type": content_type,
                "platform": "spotify", 
                "total_tracks": 1 if content_type == "track" else 5,  # Conservative estimate
                "tracks": [f"Spotify {content_type} content"],
                "url": url,
                "title": f"Spotify {content_type.title()}",
                "limited": False
            }
    
    def _get_youtube_playlist_info(self, url: str) -> Tuple[bool, Dict[str, Any]]:
        """Get YouTube playlist information."""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,  # Only get playlist info, don't download
                'playlistend': self.max_files_per_download  # Limit playlist size
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if 'entries' in info:
                    # It's a playlist
                    entries = list(info['entries'])
                    tracks = []
                    
                    for entry in entries:
                        if entry:
                            title = entry.get('title', 'Unknown Title')
                            uploader = entry.get('uploader', 'Unknown Artist')
                            tracks.append(f"{uploader} - {title}")
                    
                    return True, {
                        "type": "playlist",
                        "platform": "youtube_music" if "music.youtube.com" in url else "youtube",
                        "total_tracks": len(tracks),
                        "tracks": tracks,
                        "url": url,
                        "title": info.get('title', 'YouTube Playlist'),
                        "uploader": info.get('uploader', 'Unknown'),
                        "limited": len(entries) >= self.max_files_per_download
                    }
                else:
                    # Single video, treat as single track
                    title = info.get('title', 'Unknown Title')
                    uploader = info.get('uploader', 'Unknown Artist')
                    
                    return True, {
                        "type": "track",
                        "platform": "youtube_music" if "music.youtube.com" in url else "youtube",
                        "total_tracks": 1,
                        "tracks": [f"{uploader} - {title}"],
                        "url": url,
                        "title": title,
                        "uploader": uploader,
                        "limited": False
                    }
                    
        except Exception as e:
            logger.error(f"Error getting YouTube playlist info: {e}")
            return False, {"error": str(e)}
    
    def download_multiple(self, url: str, quality: AudioQuality = AudioQuality.HIGH, 
                         progress_tracker=None) -> MultiDownloadResult:
        """Download multiple files from a playlist/album."""
        try:
            # Get playlist information first
            success, info = self.get_playlist_info(url)
            if not success:
                return MultiDownloadResult(
                    success=False,
                    error=info.get("error", "Could not get playlist information")
                )
            
            total_files = info["total_tracks"]
            content_type = info["type"]
            platform = info["platform"]
            
            if total_files == 0:
                return MultiDownloadResult(
                    success=False,
                    error="No tracks found in playlist/album"
                )
            
            if total_files == 1:
                # Single track, use regular downloader
                logger.info("Single track detected, using regular downloader")
                if progress_tracker:
                    progress_tracker.update_overall("downloading", "Descargando track único")
                    progress_tracker.update_current_file(0, info["tracks"][0], 0, "starting")
                
                result = self.single_downloader.download_audio(url, quality)
                
                if result.success:
                    progress_tracker.complete_file(0, info["tracks"][0], True)
                    progress_tracker.update_overall("completed", "Descarga completada")
                    
                    return MultiDownloadResult(
                        success=True,
                        total_files=1,
                        completed_files=1,
                        failed_files=0,
                        files=[{
                            "name": os.path.basename(result.file_path),
                            "path": result.file_path,
                            "size": result.file_size,
                            "metadata": result.metadata
                        }]
                    )
                else:
                    progress_tracker.complete_file(0, info["tracks"][0], False, result.error)
                    progress_tracker.update_overall("failed", "Descarga falló")
                    
                    return MultiDownloadResult(
                        success=False,
                        total_files=1,
                        completed_files=0,
                        failed_files=1,
                        error=result.error
                    )
            
            # Multiple files - create organized folder
            folder_name = self._create_download_folder(info)
            download_folder = os.path.join(self.single_downloader.output_dir, folder_name)
            os.makedirs(download_folder, exist_ok=True)
            
            logger.info(f"Starting multi-download: {total_files} files to {download_folder}")
            
            if progress_tracker:
                progress_tracker.update_overall("starting", f"Iniciando descarga de {total_files} archivos")
            
            # Download based on platform
            if platform == "spotify":
                return self._download_spotify_multiple(url, quality, download_folder, info, progress_tracker)
            else:
                return self._download_youtube_multiple(url, quality, download_folder, info, progress_tracker)
                
        except Exception as e:
            logger.error(f"Error in multi-download: {e}")
            if progress_tracker:
                progress_tracker.update_overall("error", f"Error: {str(e)}", str(e))
            
            return MultiDownloadResult(
                success=False,
                error=str(e)
            )
    
    def _create_download_folder(self, info: Dict[str, Any]) -> str:
        """Create a folder name for the download."""
        title = info.get("title", "Unknown")
        content_type = info.get("type", "playlist")
        platform = info.get("platform", "unknown")
        
        # Sanitize folder name
        folder_name = FileUtils.sanitize_filename(f"{title} [{content_type}] [{platform}]")
        return folder_name
    
    def _download_spotify_multiple(self, url: str, quality: AudioQuality, 
                                 download_folder: str, info: Dict[str, Any], 
                                 progress_tracker=None) -> MultiDownloadResult:
        """Download multiple files from Spotify using spotdl."""
        try:
            total_files = info["total_tracks"]
            completed_files = 0
            failed_files = 0
            files = []
            
            if progress_tracker:
                progress_tracker.update_overall("downloading", f"Descargando {total_files} archivos de Spotify")
            
            # Use spotdl to download entire playlist/album
            download_cmd = [
                "spotdl", "download", url,
                "--output", download_folder,
                "--format", "mp3",
                "--bitrate", f"{quality.value}k",
                "--overwrite", "force"
            ]
            
            logger.info(f"Executing spotdl command: {' '.join(download_cmd)}")
            
            # Execute download with real-time progress
            process = subprocess.Popen(
                download_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                universal_newlines=True
            )
            
            current_file_index = 0
            
            for line in process.stdout:
                line = line.strip()
                if line:
                    logger.info(f"Spotdl output: {line}")
                    
                    # Parse spotdl output for progress
                    if "Downloaded" in line or "Skipping" in line:
                        if progress_tracker and current_file_index < total_files:
                            track_name = info["tracks"][current_file_index] if current_file_index < len(info["tracks"]) else f"Track {current_file_index + 1}"
                            progress_tracker.complete_file(current_file_index, track_name, "Downloaded" in line)
                            
                            if "Downloaded" in line:
                                completed_files += 1
                            else:
                                failed_files += 1
                            
                            current_file_index += 1
                    
                    elif progress_tracker and current_file_index < total_files:
                        # Update current file progress
                        track_name = info["tracks"][current_file_index] if current_file_index < len(info["tracks"]) else f"Track {current_file_index + 1}"
                        progress_tracker.update_current_file(current_file_index, track_name, 50, "downloading", line)
            
            process.wait()
            
            # Collect downloaded files
            if os.path.exists(download_folder):
                for file in os.listdir(download_folder):
                    if file.endswith(('.mp3', '.m4a')):
                        file_path = os.path.join(download_folder, file)
                        # Clean extension if needed
                        clean_path = FileUtils.clean_file_extension(file_path)
                        
                        files.append({
                            "name": os.path.basename(clean_path),
                            "path": clean_path,
                            "size": FileUtils.get_file_size(clean_path),
                            "metadata": {"platform": "spotify", "quality": quality.value}
                        })
            
            success = completed_files > 0
            
            if progress_tracker:
                if success:
                    progress_tracker.update_overall("completed", f"Completado: {completed_files}/{total_files} archivos")
                else:
                    progress_tracker.update_overall("failed", "No se descargó ningún archivo")
            
            return MultiDownloadResult(
                success=success,
                total_files=total_files,
                completed_files=completed_files,
                failed_files=failed_files,
                files=files,
                download_folder=download_folder
            )
            
        except Exception as e:
            logger.error(f"Error downloading Spotify multiple: {e}")
            if progress_tracker:
                progress_tracker.update_overall("error", f"Error: {str(e)}", str(e))
            
            return MultiDownloadResult(
                success=False,
                total_files=info.get("total_tracks", 0),
                error=str(e)
            )
    
    def _download_youtube_multiple(self, url: str, quality: AudioQuality, 
                                 download_folder: str, info: Dict[str, Any], 
                                 progress_tracker=None) -> MultiDownloadResult:
        """Download multiple files from YouTube playlist using yt-dlp."""
        try:
            total_files = info["total_tracks"]
            completed_files = 0
            failed_files = 0
            files = []
            
            if progress_tracker:
                progress_tracker.update_overall("downloading", f"Descargando {total_files} archivos de YouTube")
            
            # Configure yt-dlp for playlist download
            def progress_hook(d):
                if progress_tracker and d['status'] == 'downloading':
                    # Extract current file info
                    filename = d.get('filename', 'Unknown')
                    if 'playlist_index' in d:
                        file_index = d['playlist_index'] - 1
                        if file_index < len(info["tracks"]):
                            track_name = info["tracks"][file_index]
                        else:
                            track_name = f"Track {file_index + 1}"
                        
                        if 'total_bytes' in d and d['total_bytes']:
                            downloaded = d.get('downloaded_bytes', 0)
                            total = d['total_bytes']
                            percentage = int((downloaded / total) * 100)
                            progress_tracker.update_current_file(file_index, track_name, percentage, "downloading")
                
                elif progress_tracker and d['status'] == 'finished':
                    if 'playlist_index' in d:
                        file_index = d['playlist_index'] - 1
                        track_name = info["tracks"][file_index] if file_index < len(info["tracks"]) else f"Track {file_index + 1}"
                        progress_tracker.complete_file(file_index, track_name, True)
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(download_folder, '%(title)s.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': quality.value,
                }],
                'progress_hooks': [progress_hook],
                'quiet': False,
                'no_warnings': False,
                'playlistend': self.max_files_per_download
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # Collect downloaded files
            if os.path.exists(download_folder):
                for file in os.listdir(download_folder):
                    if file.endswith(('.mp3', '.m4a')):
                        file_path = os.path.join(download_folder, file)
                        # Clean extension if needed
                        clean_path = FileUtils.clean_file_extension(file_path)
                        
                        files.append({
                            "name": os.path.basename(clean_path),
                            "path": clean_path,
                            "size": FileUtils.get_file_size(clean_path),
                            "metadata": {"platform": info["platform"], "quality": quality.value}
                        })
                        completed_files += 1
            
            failed_files = total_files - completed_files
            success = completed_files > 0
            
            if progress_tracker:
                if success:
                    progress_tracker.update_overall("completed", f"Completado: {completed_files}/{total_files} archivos")
                else:
                    progress_tracker.update_overall("failed", "No se descargó ningún archivo")
            
            return MultiDownloadResult(
                success=success,
                total_files=total_files,
                completed_files=completed_files,
                failed_files=failed_files,
                files=files,
                download_folder=download_folder
            )
            
        except Exception as e:
            logger.error(f"Error downloading YouTube multiple: {e}")
            if progress_tracker:
                progress_tracker.update_overall("error", f"Error: {str(e)}", str(e))
            
            return MultiDownloadResult(
                success=False,
                total_files=info.get("total_tracks", 0),
                error=str(e)
            )
    
    def create_playlist_zip(self, files: List[Dict[str, Any]], playlist_name: str) -> Optional[str]:
        """
        Create a ZIP file from downloaded playlist files.
        
        Args:
            files: List of file dictionaries with 'path' and 'name' keys
            playlist_name: Name for the ZIP file
            
        Returns:
            Path to created ZIP file or None if failed
        """
        try:
            if not files:
                logger.warning("No files to zip")
                return None
            
            # Get file paths
            file_paths = [file_info["path"] for file_info in files if os.path.exists(file_info["path"])]
            
            if not file_paths:
                logger.warning("No valid file paths found for ZIP creation")
                return None
            
            # Create ZIP in the same directory as the first file
            output_dir = os.path.dirname(file_paths[0])
            zip_path = FileUtils.create_zip_archive(file_paths, playlist_name, output_dir)
            
            if zip_path:
                logger.info(f"Created playlist ZIP: {zip_path}")
                return zip_path
            else:
                logger.error("Failed to create ZIP archive")
                return None
                
        except Exception as e:
            logger.error(f"Error creating playlist ZIP: {e}")
            return None
    
    def cleanup_after_zip(self, files: List[Dict[str, Any]], keep_zip: bool = True) -> int:
        """
        Clean up individual files after ZIP creation.
        
        Args:
            files: List of file dictionaries
            keep_zip: Whether to keep ZIP files
            
        Returns:
            Number of files cleaned up
        """
        try:
            file_paths = [file_info["path"] for file_info in files if os.path.exists(file_info["path"])]
            return FileUtils.cleanup_files(file_paths, keep_zip)
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0
    
    def move_files_to_external(self, files: List[Dict[str, Any]], external_dir: str) -> List[str]:
        """
        Move downloaded files to external directory.
        
        Args:
            files: List of file dictionaries
            external_dir: External directory path
            
        Returns:
            List of new file paths
        """
        try:
            file_paths = [file_info["path"] for file_info in files if os.path.exists(file_info["path"])]
            return FileUtils.move_files_to_external_dir(file_paths, external_dir)
        except Exception as e:
            logger.error(f"Error moving files to external directory: {e}")
            return []

class PlaylistService:
    """
    Service layer for playlist download operations.
    Provides a clean interface for multi-file download functionality.
    """
    
    def __init__(self):
        self._downloader = MultiMusicDownloader()
    
    def get_playlist_info(self, url: str):
        """Get playlist information."""
        return self._downloader.get_playlist_info(url)
    
    def download_multiple(self, url: str, quality: str = "192", progress_tracker=None):
        """Download multiple files from playlist."""
        quality_enum = AudioQuality(quality)
        return self._downloader.download_multiple(url, quality_enum, progress_tracker)
    
    def create_zip(self, files: List[Dict[str, Any]], playlist_name: str):
        """Create ZIP from downloaded files."""
        return self._downloader.create_playlist_zip(files, playlist_name)
    
    def cleanup_files(self, files: List[Dict[str, Any]], keep_zip: bool = True):
        """Cleanup files after ZIP creation."""
        return self._downloader.cleanup_after_zip(files, keep_zip)

# Legacy global instance for backward compatibility
multi_downloader = MultiMusicDownloader()
