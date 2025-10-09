#!/bin/bash
# Backend development server startup script

echo "🎵 Music Downloader Backend Launcher"
echo "======================================"
echo "📁 Working directory: $(pwd)"
echo "🐍 Using uv for Python dependency management"
echo ""

# Check if we're in the right directory
if [ ! -f "main_api.py" ]; then
    echo "❌ Error: main_api.py not found"
    echo "   Please run this script from the backend-md directory"
    exit 1
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv is not installed"
    echo "   Please install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if pyproject.toml exists
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: pyproject.toml not found"
    echo "   This doesn't appear to be a valid uv project"
    exit 1
fi

echo "🔍 Validating environment..."

# Install/sync dependencies if needed
echo "📦 Syncing dependencies with uv..."
if ! uv sync --quiet; then
    echo "❌ Failed to sync dependencies"
    echo "   Try running: uv sync --verbose"
    exit 1
fi

echo "✅ Dependencies synced successfully"

# Create downloads directory if it doesn't exist
mkdir -p downloads
echo "📁 Downloads directory ready: ./downloads"

echo ""
echo "🚀 Starting server with enhanced launcher..."
echo ""

# Use the improved server launcher
uv run python run_server.py