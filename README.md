# 🎵 Music Downloader

A modern, full-stack music downloader application that supports YouTube and Spotify, built with FastAPI backend and Next.js frontend.

## ✨ Features

- **Multi-Platform Support**: Download music from YouTube, YouTube Music, and Spotify
- **High-Quality Audio**: Support for 96kbps to 320kbps audio quality
- **International URL Support**: Works with Spotify international URLs (e.g., `/intl-es/`)
- **Clean File Management**: Automatic file naming and extension cleanup
- **Modern UI**: Responsive Next.js frontend with TypeScript
- **Robust Backend**: FastAPI with async operations and timeout handling
- **Error Handling**: Comprehensive error management and logging

## 🏗️ Project Structure

```
audio_downloader/
├── README.md                    # This file
├── backend-md/                  # FastAPI Backend
│   ├── app/                     # Application code
│   ├── downloads/               # Downloaded files
│   ├── main_api.py             # FastAPI application
│   ├── run_server.py           # Server launcher script
│   ├── start.sh                # Quick start script
│   ├── pyproject.toml          # Python dependencies (uv)
│   └── uv.lock                 # Dependency lock file
└── frontend_md/                # Next.js Frontend
    ├── app/                    # Next.js app directory
    ├── components/             # React components
    ├── start.sh                # Quick start script
    ├── package.json            # Node.js dependencies
    └── ...
```

## 🚀 Running the Projects

### Prerequisites
- **Python 3.8+** with [uv](https://github.com/astral-sh/uv) package manager
- **Node.js 18+** with pnpm (recommended) or npm
- **FFmpeg** (for audio conversion)

---

## 🐍 Backend Setup (FastAPI)

### 1. Navigate to backend directory:
```bash
cd backend-md
```

### 2. Install dependencies with uv:
```bash
# Install all dependencies from pyproject.toml
uv sync
```

### 3. Start the backend server:

**Option 1 - Quick start (recommended):**
```bash
./start.sh
```

**Option 2 - Enhanced launcher:**
```bash
uv run python run_server.py
```

**Option 3 - Direct main_api.py:**
```bash
uv run python main_api.py
```

**Option 4 - Manual uvicorn:**
```bash
uv run uvicorn main_api:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at: `http://localhost:8000`
- 📖 **API Documentation**: `http://localhost:8000/docs`
- 🔍 **API Explorer**: `http://localhost:8000/redoc`

---

## ⚛️ Frontend Setup (Next.js)

### 1. Navigate to frontend directory:
```bash
cd frontend_md
```

### 2. Start the development server:

**Quick start (recommended):**
```bash
./start.sh
```

**Manual start:**
```bash
# Using pnpm (recommended)
pnpm install  # if first time
pnpm dev

# Or using npm
npm install   # if first time
npm run dev
```

The frontend will be available at: `http://localhost:3000`

The frontend will be available at: `http://localhost:3000`

---

## 🔧 Configuration

### Backend Configuration
Edit `backend-md/app/settings.py`:
```python
# Download directory
downloads_dir = "./downloads"

# Default audio quality
default_quality = "192"

# Timeout settings
download_timeout = 300  # 5 minutes
info_timeout = 30      # 30 seconds
```

### Environment Variables (Optional)
Create `.env` file in backend directory:
```bash
# Optional: Spotify credentials (for enhanced metadata)
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
```

---

## � API Documentation

### Download Endpoint
```
POST http://localhost:8000/api/download
```

**Request Body:**
```json
{
  "url": "https://open.spotify.com/track/...",
  "quality": "192"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Download completed successfully",
  "file_info": {
    "filename": "Artist - Song [192kbps].mp3",
    "size": 5242880,
    "duration": 210
  },
  "metadata": {
    "title": "Song Title",
    "artist": "Artist Name",
    "platform": "spotify"
  }
}
```

### Supported Quality Options
- `96` - 96 kbps (Low quality)
- `128` - 128 kbps (Standard quality)
- `192` - 192 kbps (High quality) - **Default**
- `320` - 320 kbps (Maximum quality)

### Supported URLs

**Spotify:**
- `https://open.spotify.com/track/...`
- `https://open.spotify.com/intl-es/track/...` (International)
- `https://open.spotify.com/album/...`
- `https://open.spotify.com/playlist/...`

**YouTube:**
- `https://www.youtube.com/watch?v=...`
- `https://youtu.be/...`
- `https://music.youtube.com/watch?v=...`

---

## 🛠️ Development

### Backend Development
```bash
cd backend-md

# Quick start
./start.sh

# Manual start with auto-reload
uv run python run_server.py

# Add new dependencies
uv add package_name

# Update dependencies
uv sync
```

### Frontend Development
```bash
cd frontend_md

# Quick start
./start.sh

# Manual development server with hot reload
pnpm dev

# Type checking
pnpm run type-check

# Linting
pnpm run lint
```

---

## 🚀 Production Deployment

### Backend Production
```bash
cd backend-md

# Install production dependencies
uv sync --no-dev

# Run production server
uv run uvicorn main_api:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend Production
```bash
cd frontend_md

# Build for production
pnpm build

# Start production server
pnpm start
```

# Start production server
pnpm start
```

---

## 📁 Detailed Project Structure

```
audio_downloader/
├── README.md                           # Project documentation
├── backend-md/                         # Python FastAPI Backend
│   ├── app/
│   │   ├── controllers/
│   │   │   └── downloader_controllers.py  # Main download logic
│   │   ├── api/
│   │   │   └── endpoints/
│   │   │       └── download.py            # API endpoints
│   │   ├── models.py                      # Pydantic models
│   │   ├── settings.py                    # Configuration
│   │   └── utils.py                       # Utility functions
│   ├── downloads/                         # Downloaded audio files
│   ├── main_api.py                        # FastAPI application entry
│   ├── run_server.py                      # Server launcher script
│   ├── start.sh                           # Quick start script
│   ├── pyproject.toml                     # uv dependencies
│   └── uv.lock                           # Lock file
└── frontend_md/                          # Next.js Frontend
    ├── app/                              # Next.js 13+ app directory
    │   ├── api/download/                 # API routes
    │   ├── layout.tsx                    # Root layout
    │   └── page.tsx                      # Home page
    ├── components/                       # React components
    ├── lib/                             # Utility libraries
    ├── start.sh                         # Quick start script
    ├── package.json                     # Node dependencies
    └── ...
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## ⚠️ Disclaimer

This tool is for educational and personal use only. Please respect copyright laws and the terms of service of the platforms you're downloading from. Always ensure you have the right to download and use the content.

---

**Built with ❤️ using FastAPI, Next.js, and modern web technologies**