"""
Application settings and configuration.
"""

from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    """Application settings loaded from environment variables or defaults."""
    
    app_name: str = "Media Downloader Backend"
    
    # Download configuration
    default_output_dir: str = os.getenv("OUTPUT_DIR", "./downloads")
    downloads_dir: str = os.getenv("DOWNLOADS_DIR", "./downloads")
    external_storage_dir: str = os.getenv("EXTERNAL_STORAGE_DIR", "../external_downloads")
    max_file_size_mb: int = 100
    allowed_formats: list = ["mp3", "wav", "flac"]
    
    # Cleanup configuration
    auto_cleanup_after_zip: bool = True
    keep_files_hours: int = 24  # Mantener archivos por 24 horas
    
    # Default quality configuration
    default_quality: str = "192"  # kbps
    
    class Config:
        env_file = ".env"

settings = Settings()