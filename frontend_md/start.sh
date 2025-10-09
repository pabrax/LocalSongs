#!/bin/bash
# Frontend development server startup script

echo "⚛️ Starting Music Downloader Frontend..."
echo "📁 Working directory: $(pwd)"
echo "📦 Using pnpm for Node.js dependency management"
echo ""

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found"
    echo "   Please run this script from the frontend_md directory"
    exit 1
fi

# Check if pnpm is installed, fallback to npm
if command -v pnpm &> /dev/null; then
    PACKAGE_MANAGER="pnpm"
elif command -v npm &> /dev/null; then
    PACKAGE_MANAGER="npm"
else
    echo "❌ Error: Neither pnpm nor npm is installed"
    echo "   Please install Node.js and npm/pnpm"
    exit 1
fi

echo "📦 Using package manager: $PACKAGE_MANAGER"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    $PACKAGE_MANAGER install
fi

# Start the development server
echo "🎨 Starting Next.js development server..."
echo "   Frontend will be available at: http://localhost:3000"
echo "   Press Ctrl+C to stop"
echo ""

if [ "$PACKAGE_MANAGER" = "pnpm" ]; then
    pnpm dev
else
    npm run dev
fi