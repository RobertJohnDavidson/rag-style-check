#!/bin/bash
# Build script for Docker deployment

set -e

echo "🏗️  Building CBC News Style Checker"
echo "=================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found. Create one with GOOGLE_API_KEY=your_key"
fi

# Build the Docker image
echo ""
echo "📦 Building Docker image..."
docker build -t cbc-style-checker:latest .

echo ""
echo "✅ Build complete!"
echo ""
echo "To run the container:"
echo "  docker compose up -d"
echo ""
echo "Or run directly:"
echo "  docker run -d -p 8000:8000 -v \$(pwd)/db:/app/db --env-file .env cbc-style-checker:latest"
echo ""
echo "Access the application at: http://localhost:8000"
