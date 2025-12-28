#!/bin/bash
# Run Xea locally for development

set -e

echo "🔮 Starting Xea Governance Oracle..."

# Navigate to project root
cd "$(dirname "$0")/../.."

# Check for .env file
if [ ! -f .env ]; then
    echo "📋 Creating .env from .env.example..."
    cp .env.example .env
fi

# Start services
echo "🐳 Starting Docker services..."
docker-compose up --build -d

echo ""
echo "✅ Xea is running!"
echo ""
echo "📍 Services:"
echo "   Backend API:  http://localhost:8000"
echo "   API Docs:     http://localhost:8000/docs"
echo "   Frontend:     http://localhost:3000"
echo "   Redis:        localhost:6379"
echo ""
echo "📋 Useful commands:"
echo "   View logs:    docker-compose logs -f"
echo "   Stop:         docker-compose down"
echo "   Rebuild:      docker-compose up --build"
echo ""
