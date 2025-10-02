#!/bin/bash

# Document Processing Pipeline - Stop Script

set -e

echo "🛑 Stopping Document Processing Pipeline..."

# Function to check if Docker Compose is running
check_docker_compose_running() {
    if command -v docker-compose >/dev/null 2>&1 && docker-compose ps | grep -q "Up"; then
        return 0
    else
        return 1
    fi
}

# Check deployment method preference
DEPLOYMENT_METHOD=""
if [ "$1" = "--docker" ] || [ "$1" = "-d" ]; then
    DEPLOYMENT_METHOD="docker"
elif [ "$1" = "--native" ] || [ "$1" = "-n" ]; then
    DEPLOYMENT_METHOD="native"
fi

# Auto-detect deployment method if not specified
if [ -z "$DEPLOYMENT_METHOD" ]; then
    if check_docker_compose_running; then
        echo "🐳 Docker Compose services detected - stopping Docker deployment"
        DEPLOYMENT_METHOD="docker"
    else
        echo "💻 Stopping native deployment"
        DEPLOYMENT_METHOD="native"
    fi
fi

if [ "$DEPLOYMENT_METHOD" = "docker" ]; then
    echo "🐳 Stopping Docker Compose services..."
    
    # Stop and remove containers
    docker-compose down
    
    # Optionally remove volumes (uncomment if needed)
    # echo "🗑️  Removing volumes..."
    # docker-compose down -v
    
    echo "✅ Docker deployment stopped!"
    echo ""
    echo "Useful commands:"
    echo "  Start again: docker-compose up -d"
    echo "  Remove volumes: docker-compose down -v"
    echo "  View stopped containers: docker-compose ps -a"
    
else
    echo "💻 Stopping native deployment..."
    
    # Check if running in Docker container
    if [ -f /.dockerenv ]; then
        echo "🐳 Running in Docker container - cannot stop from inside"
        exit 1
    else
        # Stop the application service
        echo "⚙️  Stopping application service..."
        if systemctl is-active --quiet document-processor.service; then
            sudo systemctl stop document-processor.service
            echo "✅ Application service stopped!"
        else
            echo "ℹ️  Application service was not running"
        fi
        
        # Optionally stop Redis (commented out to avoid affecting other services)
        # echo "🔴 Stopping Redis server..."
        # sudo systemctl stop redis-server
        
        echo "📊 Check status: sudo systemctl status document-processor.service"
    fi
fi

echo ""
echo "🛑 Shutdown complete!"