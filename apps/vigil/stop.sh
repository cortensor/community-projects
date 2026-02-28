#!/bin/bash

echo "🛑 Stopping Vigil services..."

# Stop backend
if [ -f backend/backend.pid ]; then
    PID=$(cat backend/backend.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        echo "✅ Backend stopped (PID: $PID)"
    fi
    rm backend/backend.pid
fi

# Stop frontend
if [ -f frontend/frontend.pid ]; then
    PID=$(cat frontend/frontend.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        echo "✅ Frontend stopped (PID: $PID)"
    fi
    rm frontend/frontend.pid
fi

# Kill any remaining processes
pkill -f "tsx src/index.ts" 2>/dev/null
pkill -f "vite" 2>/dev/null

echo "✅ All services stopped"
