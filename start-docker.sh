#!/bin/bash

# HMO Document Processing Pipeline - Docker Startup Script
# For Ubuntu Server Deployment

set -e

echo "🏠 HMO Document Processing Pipeline - Docker Deployment"
echo "========================================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first:"
    echo "   curl -fsSL https://get.docker.com -o get-docker.sh"
    echo "   sudo sh get-docker.sh"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first:"
    echo "   sudo curl -L \"https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose"
    echo "   sudo chmod +x /usr/local/bin/docker-compose"
    exit 1
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p uploads downloads temp logs cache data

# Set proper permissions
echo "🔐 Setting directory permissions..."
chmod 755 uploads downloads temp logs cache data

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down --remove-orphans || true

# Remove old images if requested
if [ "$1" = "--rebuild" ]; then
    echo "🔄 Rebuilding Docker images..."
    docker-compose build --no-cache
fi

# Pull latest images and build
echo "📦 Building and starting containers..."
docker-compose up -d --build

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🔍 Checking service health..."

# Check Redis
if docker-compose exec redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is running"
else
    echo "❌ Redis is not responding"
fi

# Check main application
if curl -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
    echo "✅ Main application is running"
else
    echo "⚠️  Main application is starting up..."
fi

# Show container status
echo ""
echo "📊 Container Status:"
docker-compose ps

# Show logs if there are any errors
echo ""
echo "📋 Recent logs:"
docker-compose logs --tail=20

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "📱 Access the application at:"
echo "   http://localhost:8501"
echo "   http://$(hostname -I | awk '{print $1}'):8501"
echo ""
echo "🔧 Useful commands:"
echo "   View logs:           docker-compose logs -f"
echo "   Stop services:       docker-compose down"
echo "   Restart services:    docker-compose restart"
echo "   Update application:  ./start-docker.sh --rebuild"
echo ""