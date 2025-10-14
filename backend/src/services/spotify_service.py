"""
Spotify service using spotdl directly as subprocess
"""

import os
import logging
import subprocess
import json
import tempfile
import shutil
from typing import Optional, List, Dict, Any
from pathlib import Path

from .download_service import DownloadResult, AudioQuality
from ..core.utils import FileUtils

logger = logging.getLogger(__name__)

class SpotifyDownloader:
    """Simple Spotify downloader using spotdl command line tool"""
    
    def __init__(self, output_dir: str = "./downloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def download(self, spotify_url: str, quality: AudioQuality = AudioQuality.HIGH, 
                progress_tracker=None) -> DownloadResult:
        """
        Download from Spotify URL using spotdl directly
        """
        try:
            if progress_tracker:
                progress_tracker.update(10, "initializing", "Iniciando descarga con spotdl...")
            
            # Check if spotdl is available
            if not self._check_spotdl_available():
                return DownloadResult(
                    success=False,
                    error="spotdl no está instalado o no está disponible en PATH"
                )
            
            if progress_tracker:
                progress_tracker.update(20, "processing", "Procesando URL de Spotify...")
            
            # Get track info first
            track_info = self._get_track_info(spotify_url)
            if not track_info:
                return DownloadResult(
                    success=False,
                    error="No se pudo obtener información del track/playlist de Spotify"
                )
            
            # Download using spotdl
            return self._download_with_spotdl(spotify_url, quality, track_info, progress_tracker)
            
        except Exception as e:
            logger.error(f"Error in Spotify download: {e}")
            if progress_tracker:
                progress_tracker.update(0, "error", f"Error: {str(e)}")
            
            return DownloadResult(
                success=False,
                error=f"Error en descarga de Spotify: {str(e)}"
            )
    
    def download_playlist(self, spotify_url: str, quality: AudioQuality = AudioQuality.HIGH,
                         progress_tracker=None) -> List[DownloadResult]:
        """
        Download a Spotify playlist using spotdl
        """
        results = []
        try:
            if progress_tracker:
                progress_tracker.update(5, "initializing", "Iniciando descarga de playlist...")
            
            # Check if spotdl is available
            if not self._check_spotdl_available():
                return [DownloadResult(
                    success=False,
                    error="spotdl no está instalado o no está disponible en PATH"
                )]
            
            # Get playlist info
            playlist_info = self._get_playlist_info(spotify_url)
            if not playlist_info:
                return [DownloadResult(
                    success=False,
                    error="No se pudo obtener información de la playlist"
                )]
            
            if progress_tracker:
                progress_tracker.update(10, "processing", f"Descargando playlist: {playlist_info.get('name', 'Unknown')}")
            
            # Download entire playlist with spotdl
            return self._download_playlist_with_spotdl(spotify_url, quality, playlist_info, progress_tracker)
            
        except Exception as e:
            logger.error(f"Error downloading playlist: {e}")
            if progress_tracker:
                progress_tracker.update(0, "error", f"Error: {str(e)}")
            
            return [DownloadResult(
                success=False,
                error=f"Error descargando playlist: {str(e)}"
            )]
    
    def _get_spotdl_command(self) -> List[str]:
        """Get the correct spotdl command based on environment"""
        # Check if we're running in a uv environment
        if os.environ.get('VIRTUAL_ENV') or os.environ.get('UV_PROJECT_ENVIRONMENT'):
            # We're in a uv environment, use uv run
            return ['uv', 'run', 'spotdl']
        else:
            # Try regular spotdl first
            return ['spotdl']
    
    def _check_spotdl_available(self) -> bool:
        """Check if spotdl is available in system PATH"""
        try:
            cmd = self._get_spotdl_command() + ['--version']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _get_track_info(self, spotify_url: str) -> Optional[Dict[str, Any]]:
        """Get track information using spotdl save command"""
        try:
            # Create temporary file for track info
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Use spotdl save to get track info
            cmd = self._get_spotdl_command() + ['save', spotify_url, '--save-file', temp_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(temp_path):
                with open(temp_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                os.unlink(temp_path)
                
                # Parse the content - spotdl save outputs track info
                if content:
                    # spotdl save typically outputs: "Artist - Track Name"
                    lines = content.split('\n')
                    first_track = lines[0] if lines else content
                    
                    if ' - ' in first_track:
                        artist, title = first_track.split(' - ', 1)
                        return {
                            'artist': artist.strip(),
                            'title': title.strip(),
                            'name': title.strip(),
                            'full_name': first_track.strip()
                        }
                    else:
                        return {
                            'artist': 'Unknown Artist',
                            'title': first_track.strip(),
                            'name': first_track.strip(),
                            'full_name': first_track.strip()
                        }
            
            # Cleanup temp file if it exists
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting track info: {e}")
            return None
    
    def _get_playlist_info(self, spotify_url: str) -> Optional[Dict[str, Any]]:
        """Get playlist information"""
        try:
            # For playlists, we can use the same save method
            info = self._get_track_info(spotify_url)
            if info:
                return {
                    'name': info.get('full_name', 'Spotify Playlist'),
                    'track_count': 1  # We'll update this during download
                }
            return None
        except Exception as e:
            logger.error(f"Error getting playlist info: {e}")
            return None
    
    def _download_with_spotdl(self, spotify_url: str, quality: AudioQuality, 
                             track_info: Dict[str, Any], progress_tracker=None) -> DownloadResult:
        """Download using spotdl command"""
        try:
            if progress_tracker:
                progress_tracker.update(30, "downloading", "Descargando con spotdl...")
            
            # Create temporary directory for download
            temp_dir = tempfile.mkdtemp(prefix="spotdl_download_")
            
            # Build spotdl command
            cmd = self._get_spotdl_command() + [
                spotify_url,
                '--output', temp_dir,
                '--bitrate', str(quality.value),
                '--format', 'mp3'
            ]
            
            # Run spotdl
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                     text=True, bufsize=1, universal_newlines=True)
            
            # Monitor progress
            output_lines = []
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    output_lines.append(output.strip())
                    if progress_tracker:
                        # Update progress based on spotdl output
                        if "%" in output:
                            try:
                                # Extract percentage from spotdl output
                                percentage_str = output.split('%')[0].split()[-1]
                                percentage = int(percentage_str)
                                progress_tracker.update(30 + int(percentage * 0.6), "downloading", 
                                                      f"Descargando: {percentage}%")
                            except:
                                pass
            
            # Wait for completion
            return_code = process.poll()
            stderr = process.stderr.read()
            
            if return_code != 0:
                logger.error(f"spotdl failed with code {return_code}: {stderr}")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return DownloadResult(
                    success=False,
                    error=f"spotdl falló: {stderr}"
                )
            
            if progress_tracker:
                progress_tracker.update(95, "processing", "Procesando archivo descargado...")
            
            # Find downloaded file
            downloaded_files = list(Path(temp_dir).glob("*.mp3"))
            if not downloaded_files:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return DownloadResult(
                    success=False,
                    error="No se encontró archivo descargado"
                )
            
            downloaded_file = downloaded_files[0]
            
            # Move to final location
            final_filename = f"{downloaded_file.stem}_{quality.value}kbps.mp3"
            final_path = self.output_dir / final_filename
            
            shutil.move(str(downloaded_file), str(final_path))
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            # Get file info
            file_size = FileUtils.get_file_size(str(final_path))
            
            if progress_tracker:
                progress_tracker.update(100, "completed", f"Descarga completada: {final_filename}")
            
            return DownloadResult(
                success=True,
                file_path=str(final_path),
                metadata={
                    "title": track_info.get('title', 'Unknown'),
                    "artist": track_info.get('artist', 'Unknown'),
                    "album": "Unknown",
                    "duration": 0,
                    "quality": quality.value,
                    "platform": "spotify",
                    "source_url": spotify_url,
                    "file_hash": FileUtils.get_file_hash(str(final_path))
                },
                file_size=file_size
            )
            
        except Exception as e:
            logger.error(f"Error in spotdl download: {e}")
            if progress_tracker:
                progress_tracker.update(0, "error", f"Error: {str(e)}")
            
            return DownloadResult(
                success=False,
                error=f"Error en descarga: {str(e)}"
            )
    
    def _download_playlist_with_spotdl(self, spotify_url: str, quality: AudioQuality,
                                      playlist_info: Dict[str, Any], progress_tracker=None) -> List[DownloadResult]:
        """Download playlist using spotdl"""
        results = []
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix="spotdl_playlist_")
            
            # Build command for playlist
            cmd = self._get_spotdl_command() + [
                spotify_url,
                '--output', temp_dir,
                '--bitrate', str(quality.value),
                '--format', 'mp3'
            ]
            
            if progress_tracker:
                progress_tracker.update(20, "downloading", "Descargando playlist completa...")
            
            # Run spotdl for playlist
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True, bufsize=1, universal_newlines=True)
            
            # Monitor progress
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output and progress_tracker:
                    # Extract progress info from spotdl output
                    if "complete" in output.lower() and "/" in output:
                        try:
                            # Parse "X/Y complete" format
                            parts = output.split()
                            for part in parts:
                                if "/" in part:
                                    completed, total = part.split("/")
                                    percentage = int((int(completed) / int(total)) * 100)
                                    progress_tracker.update(20 + int(percentage * 0.7), "downloading",
                                                          f"Descargando: {completed}/{total} canciones")
                                    break
                        except:
                            pass
            
            return_code = process.poll()
            stderr = process.stderr.read()
            
            if return_code != 0:
                logger.error(f"spotdl playlist download failed: {stderr}")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return [DownloadResult(
                    success=False,
                    error=f"Error descargando playlist: {stderr}"
                )]
            
            if progress_tracker:
                progress_tracker.update(95, "processing", "Procesando archivos descargados...")
            
            # Process downloaded files
            downloaded_files = list(Path(temp_dir).glob("*.mp3"))
            
            for i, downloaded_file in enumerate(downloaded_files):
                try:
                    # Move each file to final location
                    final_filename = f"{downloaded_file.stem}_{quality.value}kbps.mp3"
                    final_path = self.output_dir / final_filename
                    
                    shutil.move(str(downloaded_file), str(final_path))
                    
                    file_size = FileUtils.get_file_size(str(final_path))
                    
                    results.append(DownloadResult(
                        success=True,
                        file_path=str(final_path),
                        metadata={
                            "title": downloaded_file.stem,
                            "artist": "Unknown",
                            "album": "Unknown",
                            "duration": 0,
                            "quality": quality.value,
                            "platform": "spotify",
                            "source_url": spotify_url,
                            "file_hash": FileUtils.get_file_hash(str(final_path))
                        },
                        file_size=file_size
                    ))
                    
                except Exception as e:
                    logger.error(f"Error processing file {downloaded_file}: {e}")
                    results.append(DownloadResult(
                        success=False,
                        error=f"Error procesando {downloaded_file.name}: {str(e)}"
                    ))
            
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            if progress_tracker:
                progress_tracker.update(100, "completed", f"Playlist descargada: {len(results)} archivos")
            
            return results if results else [DownloadResult(
                success=False,
                error="No se descargaron archivos"
            )]
            
        except Exception as e:
            logger.error(f"Error in playlist download: {e}")
            if progress_tracker:
                progress_tracker.update(0, "error", f"Error: {str(e)}")
            
            return [DownloadResult(
                success=False,
                error=f"Error descargando playlist: {str(e)}"
            )]

# Global instance
spotify_downloader = SpotifyDownloader()
