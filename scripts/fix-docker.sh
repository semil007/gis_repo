#!/bin/bash
# Quick fix script to rebuild and restart Docker containers

echo "🔧 Fixing Docker deployment..."
echo ""

# Stop existing containers
echo "⏹️  Stopping existing containers..."
docker-compose down

# Remove old images to force rebuild
echo "🗑️  Removing old images..."
docker-compose rm -f

# Rebuild images
echo "🔨 Rebuilding Docker images..."
docker-compose build --no-cache

# Start services
echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Check status
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "📋 Checking logs for errors..."
docker-compose logs --tail=50 app

echo ""
echo "✅ Fix complete!"
echo ""
echo "Access the application at: http://192.168.1.49:8501"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f app"
echo "  docker-compose logs -f worker"
echo "  docker-compose logs -f redis"
