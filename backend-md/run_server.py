#!/usr/bin/env python3
"""
Development Server Launcher

This script ensures proper environment setup and launches the FastAPI server
with optimal settings for development. It handles dependency validation,
environment setup, and provides clear feedback about the server status.
"""

import os
import sys
import logging
from pathlib import Path


def setup_environment():
    """Setup the Python path and validate environment."""
    # Add current directory to Python path
    current_dir = Path(__file__).parent.absolute()
    sys.path.insert(0, str(current_dir))
    
    # Validate Python version
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8+ is required")
        sys.exit(1)
    
    return current_dir


def validate_dependencies():
    """Validate that all required dependencies are available."""
    required_packages = [
        "fastapi",
        "uvicorn", 
        "pydantic_settings",
        "yt_dlp",
        "spotdl"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n💡 Install missing packages with: uv sync")
        return False
    
    return True


def print_startup_info():
    """Print startup information and instructions."""
    print("🎵 Music Downloader Backend")
    print("=" * 50)
    print("✅ Environment validated")
    print("✅ Dependencies available")
    print("🚀 Starting FastAPI server...")
    print("")
    print("📊 Server Information:")
    print("   🌐 URL: http://localhost:8000")
    print("   📖 API Docs: http://localhost:8000/docs")
    print("   🔄 Auto-reload: Enabled")
    print("   📁 Downloads: ./downloads")
    print("")
    print("🎯 Supported Platforms:")
    print("   🎵 Spotify (tracks, albums, playlists)")
    print("   📹 YouTube (videos, music)")
    print("   🎼 YouTube Music")
    print("")
    print("⏹️  Press Ctrl+C to stop the server")
    print("=" * 50)
    print("")


def main():
    """Main server launcher function."""
    try:
        # Setup environment
        current_dir = setup_environment()
        
        # Validate dependencies
        if not validate_dependencies():
            sys.exit(1)
        
        # Import FastAPI app
        try:
            from main_api import app
        except ImportError as e:
            print(f"❌ Failed to import FastAPI app: {e}")
            print("💡 Make sure you're in the correct directory")
            sys.exit(1)
        
        # Print startup info
        print_startup_info()
        
        # Import and run uvicorn
        import uvicorn
        
        # Configure logging for uvicorn
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        
        # Start the server
        uvicorn.run(
            "main_api:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=[str(current_dir)],
            log_level="info",
            access_log=False  # Disable access logs for cleaner output
        )
        
    except KeyboardInterrupt:
        print("\n⏹️  Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()