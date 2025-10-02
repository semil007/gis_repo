#!/bin/bash

# Document Processing Pipeline - Start Script

set -e

echo "🚀 Starting Document Processing Pipeline..."

# Function to check if Docker is available and running
check_docker() {
    if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to check if docker-compose file exists
check_docker_compose() {
    if [ -f "docker-compose.yml" ]; then
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
    if check_docker && check_docker_compose; then
        echo "🐳 Docker detected - using Docker deployment"
        DEPLOYMENT_METHOD="docker"
    else
        echo "💻 Using native Python deployment"
        DEPLOYMENT_METHOD="native"
    fi
fi

if [ "$DEPLOYMENT_METHOD" = "docker" ]; then
    echo "🐳 Starting with Docker Compose..."
    
    # Check if containers are already running
    if docker-compose ps | grep -q "Up"; then
        echo "⚠️  Some containers are already running. Stopping them first..."
        docker-compose down
    fi
    
    # Start services
    docker-compose up -d
    
    # Wait for services to be ready
    echo "⏳ Waiting for services to start..."
    sleep 10
    
    # Check service health
    echo "🔍 Checking service health..."
    docker-compose ps
    
    echo "✅ Docker deployment started!"
    echo "📱 Web interface: http://localhost:8501"
    echo "🔴 Redis: localhost:6379"
    echo ""
    echo "Useful commands:"
    echo "  View logs: docker-compose logs -f"
    echo "  Stop services: docker-compose down"
    echo "  Restart: docker-compose restart"
    
else
    echo "💻 Starting native Python deployment..."
    
    # Check if running in Docker container
    if [ -f /.dockerenv ]; then
        echo "🐳 Running inside Docker container..."
        
        # Start Redis in background if not running
        if ! pgrep -x "redis-server" > /dev/null; then
            redis-server --daemonize yes --bind 0.0.0.0
            sleep 2
        fi
        
        # Start Streamlit app
        exec streamlit run web/streamlit_app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true
    else
        # Activate virtual environment if it exists
        if [ -d "venv" ]; then
            echo "🐍 Activating virtual environment..."
            source venv/bin/activate
        fi
        
        # Check if Redis is running
        if ! pgrep -x "redis-server" > /dev/null; then
            echo "🔴 Starting Redis server..."
            sudo systemctl start redis-server
        fi
        
        # Create necessary directories
        mkdir -p uploads downloads temp logs
        
        # Start the application using systemd service
        echo "⚙️  Starting application service..."
        sudo systemctl start document-processor.service
        
        echo "✅ Native deployment started!"
        echo "📱 Web interface: http://localhost:8501"
        echo "📊 Check status: sudo systemctl status document-processor.service"
        echo "📝 View logs: sudo journalctl -u document-processor.service -f"
    fi
fi

echo ""
echo "🎉 Application is starting up..."
echo "Please wait a moment for all services to be ready."