#!/bin/bash

# TruthLens Deployment Script
# Supports deployment to Vercel (frontend) and Render (backend)

set -e

echo "🚀 TruthLens Deployment Script"
echo "=============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_dependencies() {
    print_status "Checking dependencies..."

    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed. Please install Node.js first."
        exit 1
    fi

    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed. Please install npm first."
        exit 1
    fi

    print_success "Dependencies check passed"
}

# Deploy to Vercel
deploy_vercel() {
    print_status "Deploying frontend to Vercel..."

    if ! command -v vercel &> /dev/null; then
        print_warning "Vercel CLI not found. Installing..."
        npm install -g vercel
    fi

    # Check if already logged in
    if ! vercel whoami &> /dev/null; then
        print_warning "Please login to Vercel first:"
        vercel login
    fi

    # Deploy
    print_status "Building and deploying to Vercel..."
    vercel --prod

    print_success "Frontend deployed to Vercel!"
    print_status "Note: Update vercel.json with your Render backend URL"
}

# Deploy to Render
deploy_render() {
    print_status "Deploying backend to Render..."

    if ! command -v render &> /dev/null; then
        print_warning "Render CLI not found. Installing..."
        npm install -g render-cli
    fi

    # Check if logged in
    if ! render whoami &> /dev/null; then
        print_warning "Please login to Render first:"
        render login
    fi

    # Deploy using render.yaml
    print_status "Deploying using render.yaml configuration..."
    render deploy

    print_success "Backend deployed to Render!"
}

# Deploy using Docker to Render
deploy_docker_render() {
    print_status "Deploying with Docker to Render..."

    # Build Docker image
    print_status "Building Docker image..."
    docker build -t truthlens .

    # Tag for Render
    print_status "Tagging image for Render..."
    docker tag truthlens registry.render.com/truthlens

    # Push to Render registry
    print_status "Pushing to Render registry..."
    docker push registry.render.com/truthlens

    print_success "Docker image pushed to Render!"
    print_status "Create a new Render service with Docker and use: registry.render.com/truthlens"
}

# Main deployment function
main() {
    echo "Select deployment option:"
    echo "1) Deploy frontend to Vercel"
    echo "2) Deploy backend to Render (Node.js)"
    echo "3) Deploy with Docker to Render"
    echo "4) Deploy both (Vercel + Render)"
    echo "5) Exit"

    read -p "Enter your choice (1-5): " choice

    case $choice in
        1)
            check_dependencies
            deploy_vercel
            ;;
        2)
            check_dependencies
            deploy_render
            ;;
        3)
            check_dependencies
            deploy_docker_render
            ;;
        4)
            check_dependencies
            deploy_vercel
            echo ""
            deploy_render
            ;;
        5)
            print_status "Goodbye!"
            exit 0
            ;;
        *)
            print_error "Invalid choice. Please select 1-5."
            main
            ;;
    esac
}

# Run main function
main
