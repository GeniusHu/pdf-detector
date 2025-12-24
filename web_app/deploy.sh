#!/bin/bash

# PDF Similarity Detection System - Deployment Script
# This script helps deploy the application in different environments

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="development"
SKIP_BUILD=false
SKIP_MIGRATION=false
DETACH=true

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  PDF Similarity Detection${NC}"
    echo -e "${BLUE}  Deployment Script${NC}"
    echo -e "${BLUE}================================${NC}"
    echo
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -e, --environment ENV   Set environment (development|production) [default: development]"
    echo "  -b, --skip-build        Skip building Docker images"
    echo "  -m, --skip-migration    Skip database migrations"
    echo "  -d, --detach            Run containers in detached mode [default: true]"
    echo "  --no-detach             Run containers in foreground"
    echo "  -h, --help              Show this help message"
    echo
    echo "Examples:"
    echo "  $0                      # Deploy development environment"
    echo "  $0 -e production        # Deploy production environment"
    echo "  $0 -b -e production     # Deploy production without rebuilding"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -b|--skip-build)
            SKIP_BUILD=true
            shift
            ;;
        -m|--skip-migration)
            SKIP_MIGRATION=true
            shift
            ;;
        -d|--detach)
            DETACH=true
            shift
            ;;
        --no-detach)
            DETACH=false
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate environment
if [[ "$ENVIRONMENT" != "development" && "$ENVIRONMENT" != "production" ]]; then
    print_error "Invalid environment: $ENVIRONMENT. Must be 'development' or 'production'"
    exit 1
fi

# Main deployment function
deploy() {
    print_header
    print_status "Starting deployment for $ENVIRONMENT environment..."

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    # Set COMPOSE_FILE based on environment
    if [[ "$ENVIRONMENT" == "production" ]]; then
        export COMPOSE_FILE="docker-compose.yml"
        print_status "Using production configuration"
    else
        export COMPOSE_FILE="docker-compose.dev.yml"
        print_status "Using development configuration"
    fi

    # Create necessary directories
    print_status "Creating necessary directories..."
    mkdir -p uploads exports logs
    chmod 755 uploads exports logs

    # Copy environment files if they don't exist
    if [[ ! -f backend/.env ]]; then
        print_status "Creating backend environment file..."
        cp backend/.env.example backend/.env
        print_warning "Please edit backend/.env with your configuration"
    fi

    if [[ ! -f frontend/.env.local ]]; then
        print_status "Creating frontend environment file..."
        cp .env.example frontend/.env.local
        print_warning "Please edit frontend/.env.local with your configuration"
    fi

    # Build Docker images (if not skipped)
    if [[ "$SKIP_BUILD" = false ]]; then
        print_status "Building Docker images..."
        docker-compose build
    else
        print_status "Skipping Docker image build..."
    fi

    # Stop existing containers
    print_status "Stopping existing containers..."
    docker-compose down

    # Start services
    print_status "Starting services..."
    DETACH_FLAG=""
    if [[ "$DETACH" = true ]]; then
        DETACH_FLAG="-d"
    fi

    docker-compose up $DETACH_FLAG

    # Wait for services to be ready (in detached mode)
    if [[ "$DETACH" = true ]]; then
        print_status "Waiting for services to be ready..."
        sleep 10

        # Check backend health
        print_status "Checking backend health..."
        if curl -f http://localhost:8000/health &> /dev/null; then
            print_status "✅ Backend is healthy"
        else
            print_error "❌ Backend health check failed"
        fi

        # Check frontend health
        print_status "Checking frontend health..."
        if curl -f http://localhost:3000 &> /dev/null; then
            print_status "✅ Frontend is healthy"
        else
            print_error "❌ Frontend health check failed"
        fi
    fi

    # Show deployment summary
    echo
    print_status "🎉 Deployment completed successfully!"
    echo
    echo "Services:"
    echo "  • Frontend: http://localhost:3000"
    echo "  • Backend:  http://localhost:8000"
    echo "  • API Docs: http://localhost:8000/docs"
    echo "  • Redis:    localhost:6379"
    echo
    echo "Useful commands:"
    echo "  • View logs: docker-compose logs -f"
    echo "  • Stop services: docker-compose down"
    echo "  • Restart services: docker-compose restart"
    echo
    echo "Configuration files:"
    echo "  • Backend:  backend/.env"
    echo "  • Frontend: frontend/.env.local"
    echo
}

# Function to show logs
show_logs() {
    print_status "Showing logs for all services..."
    docker-compose logs -f
}

# Function to stop services
stop_services() {
    print_status "Stopping all services..."
    docker-compose down
    print_status "All services stopped."
}

# Function to clean up
cleanup() {
    print_status "Cleaning up Docker resources..."
    docker-compose down -v --rmi all
    docker system prune -f
    print_status "Cleanup completed."
}

# Function to backup data
backup_data() {
    print_status "Creating backup of data..."
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"

    # Backup uploads
    if [[ -d "uploads" ]]; then
        cp -r uploads "$BACKUP_DIR/"
        print_status "✅ Uploads backed up"
    fi

    # Backup exports
    if [[ -d "exports" ]]; then
        cp -r exports "$BACKUP_DIR/"
        print_status "✅ Exports backed up"
    fi

    # Backup logs
    if [[ -d "logs" ]]; then
        cp -r logs "$BACKUP_DIR/"
        print_status "✅ Logs backed up"
    fi

    print_status "Backup created in: $BACKUP_DIR"
}

# Check for specific commands
case "${1:-deploy}" in
    deploy)
        deploy
        ;;
    logs)
        show_logs
        ;;
    stop)
        stop_services
        ;;
    cleanup)
        cleanup
        ;;
    backup)
        backup_data
        ;;
    *)
        deploy
        ;;
esac