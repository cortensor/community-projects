#!/bin/bash

# AI Oracle Setup Script
echo "🚀 Setting up AI Oracle (Truth Machine - TaaS)..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOL
# Database
DATABASE_URL=postgresql://ai_oracle_user:ai_oracle_pass@postgres:5432/ai_oracle

# Redis
REDIS_URL=redis://redis:6379

# Cortensor Network
CORTENSOR_API_ENDPOINT=http://localhost:8080
CORTENSOR_API_KEY=your_cortensor_api_key_here

# JWT
JWT_SECRET=$(openssl rand -base64 32)

# Web3 (Optional)
WEB3_PROVIDER_URL=https://mainnet.infura.io/v3/your-project-id
BLOCKCHAIN_PRIVATE_KEY=your_private_key_here

# Frontend
NEXT_PUBLIC_API_URL=http://backend:4000
NEXT_PUBLIC_WS_URL=ws://backend:4000
EOL
    echo "✅ Created .env file with default values"
    echo "⚠️  Please update the CORTENSOR_API_KEY and other values as needed"
else
    echo "✅ .env file already exists"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p backend/logs
mkdir -p ssl

# Pull Docker images
echo "📦 Pulling Docker images..."
docker-compose pull

# Build and start services
echo "🏗️  Building and starting services..."
docker-compose up -d --build

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check service health
echo "🔍 Checking service health..."

# Check backend health
if curl -f http://localhost:4000/health > /dev/null 2>&1; then
    echo "✅ Backend is healthy"
else
    echo "❌ Backend health check failed"
fi

# Check database connection
if docker-compose exec -T postgres pg_isready -U ai_oracle_user -d ai_oracle > /dev/null 2>&1; then
    echo "✅ Database is ready"
else
    echo "❌ Database connection failed"
fi

# Check Redis connection
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is ready"
else
    echo "❌ Redis connection failed"
fi

echo ""
echo "🎉 AI Oracle setup complete!"
echo ""
echo "📍 Access points:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:4000"
echo "   API Health: http://localhost:4000/health"
echo ""
echo "🔧 Management commands:"
echo "   View logs: docker-compose logs -f"
echo "   Stop services: docker-compose down"
echo "   Restart services: docker-compose restart"
echo ""
echo "📚 Next steps:"
echo "   1. Update your .env file with real API keys"
echo "   2. Visit http://localhost:3000 to use the Oracle"
echo "   3. Check the README.md for detailed documentation"
echo ""
