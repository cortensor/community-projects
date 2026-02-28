#!/bin/bash

# Vigil Agent - Startup Script

set -e

echo "🚀 Starting Vigil Agent"
echo "===================================="
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

echo "✅ Node.js version: $(node --version)"
echo ""

# Check if backend dependencies are installed
if [ ! -d "backend/node_modules" ]; then
    echo "📦 Installing backend dependencies..."
    cd backend
    npm install
    cd ..
    echo "✅ Backend dependencies installed"
    echo ""
fi

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
    echo "✅ Frontend dependencies installed"
    echo ""
fi

# Check if .env exists
if [ ! -f "backend/.env" ]; then
    echo "⚠️  No .env file found. Creating from example..."
    cp backend/.env.example backend/.env
    echo "✅ Created backend/.env - Please edit with your credentials"
    echo ""
fi

# Create data directory
mkdir -p backend/data

echo "🎯 Starting services..."
echo ""
echo "Backend will run on: http://localhost:3001"
echo "Frontend will run on: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    if [ -f backend/backend.pid ]; then
        kill $(cat backend/backend.pid) 2>/dev/null
        rm backend/backend.pid
    fi
    if [ -f frontend/frontend.pid ]; then
        kill $(cat frontend/frontend.pid) 2>/dev/null
        rm frontend/frontend.pid
    fi
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
cd backend
nohup npm run dev > backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > backend.pid
cd ..

# Wait for backend to start
sleep 3

# Start frontend
cd frontend
nohup npm run dev > frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > frontend.pid
cd ..

# Wait for both processes
echo ""
echo "✅ Services started!"
echo ""
echo "View logs:"
echo "  Backend:  tail -f backend/backend.log"
echo "  Frontend: tail -f frontend/frontend.log"
echo ""
echo "To stop services, run: ./stop.sh"
echo ""

# Keep script running and monitor processes
while true; do
    if [ -f backend/backend.pid ] && ! ps -p $(cat backend/backend.pid) > /dev/null 2>&1; then
        echo "⚠️  Backend stopped unexpectedly"
        break
    fi
    if [ -f frontend/frontend.pid ] && ! ps -p $(cat frontend/frontend.pid) > /dev/null 2>&1; then
        echo "⚠️  Frontend stopped unexpectedly"
        break
    fi
    sleep 2
done
