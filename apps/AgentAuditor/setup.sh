#!/bin/bash

# Cortensor Agent Auditor - Quick Setup Script
# This script automates the initial setup process

set -e

echo "🛡️  Cortensor Agent Auditor - Quick Setup"
echo "=========================================="

# Check prerequisites
echo "✓ Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.10+"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 18+"
    exit 1
fi

if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL not found. Please install PostgreSQL 14+"
    exit 1
fi

echo "✓ All prerequisites found!"

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your credentials before continuing!"
    echo "   Required: PRIVATE_KEY, SESSION_V2_ADDRESS, SESSION_QUEUE_V2_ADDRESS, PINATA_API_KEY"
    read -p "Press Enter once you've updated .env..."
fi

# Create database
echo "🗄️  Setting up database..."
read -p "Enter PostgreSQL database name (default: cortensor_auditor): " DB_NAME
DB_NAME=${DB_NAME:-cortensor_auditor}

# Check if database exists
if psql -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
    echo "⚠️  Database $DB_NAME already exists. Skipping creation."
else
    createdb $DB_NAME
    echo "✓ Database $DB_NAME created"
fi

# Run schema
echo "📊 Applying database schema..."
psql $DB_NAME < database/schema.sql
echo "✓ Schema applied"

# Backend setup
echo "🐍 Setting up Python backend..."

# Create virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✓ Python dependencies installed"

# Frontend setup
echo "⚛️  Setting up React frontend..."
cd frontend

# Install dependencies
echo "📦 Installing Node.js dependencies..."
npm install --silent
echo "✓ Node.js dependencies installed"

cd ..

# Summary
echo ""
echo "=========================================="
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Ensure .env is configured with your credentials"
echo "2. Start backend:  source venv/bin/activate && python -m backend.main"
echo "3. Start frontend: cd frontend && npm run dev"
echo "4. Visit http://localhost:3000"
echo ""
echo "🎉 Happy hacking!"
