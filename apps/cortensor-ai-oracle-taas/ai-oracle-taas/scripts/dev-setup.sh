#!/bin/bash

# Development Setup Script
echo "🛠️  Setting up AI Oracle for development..."

# Check Node.js version
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version 18+ is required. Current version: $(node -v)"
    exit 1
fi

echo "✅ Node.js version: $(node -v)"

# Start infrastructure services only
echo "🐳 Starting infrastructure services (PostgreSQL, Redis)..."
docker-compose up -d postgres redis

# Wait for services
echo "⏳ Waiting for infrastructure services..."
sleep 10

# Install backend dependencies
echo "📦 Installing backend dependencies..."
cd backend
npm install

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd ..
npm install

# Create development .env
if [ ! -f .env.local ]; then
    echo "📝 Creating .env.local for development..."
    cat > .env.local << EOL
# Development Environment
NODE_ENV=development

# Database
DATABASE_URL=postgresql://ai_oracle_user:ai_oracle_pass@localhost:5432/ai_oracle

# Redis
REDIS_URL=redis://localhost:6379

# Cortensor Network (Development)
CORTENSOR_API_ENDPOINT=http://localhost:8080
CORTENSOR_API_KEY=dev_api_key

# JWT
JWT_SECRET=dev-secret-key-change-in-production

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:4000
NEXT_PUBLIC_WS_URL=ws://localhost:4000
EOL
    echo "✅ Created .env.local for development"
fi

echo ""
echo "🎉 Development setup complete!"
echo ""
echo "🚀 To start development:"
echo "   1. Backend: cd backend && npm run dev"
echo "   2. Frontend: npm run dev"
echo ""
echo "📍 Development URLs:"
echo "   Frontend: http://localhost:3000"
echo "   Backend: http://localhost:4000"
echo ""
echo "🔧 Useful commands:"
echo "   Database logs: docker-compose logs postgres"
echo "   Redis logs: docker-compose logs redis"
echo "   Stop infrastructure: docker-compose down"
echo ""
