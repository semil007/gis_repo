#!/bin/bash
# Quick fix script to rebuild and restart Docker containers

echo "🔧 Fixing Docker deployment..."
echo ""

# Stop existing containers
echo "⏹️  Stopping existing containers..."
docker-compose down -v

# Remove old images to force rebuild
echo "🗑️  Removing old images..."
docker-compose rm -f

# Remove old database files if they exist (we'll use Docker volumes instead)
echo "🗑️  Cleaning up old database files..."
if [ -f "processing_sessions.db" ]; then
    rm -f processing_sessions.db
    echo "Removed old processing_sessions.db"
fi

if [ -f "audit_data.db" ]; then
    rm -f audit_data.db
    echo "Removed old audit_data.db"
fi

# Create required directories
echo "📁 Creating required directories..."
mkdir -p uploads downloads temp logs cache

# Set proper permissions
echo "🔐 Setting permissions..."
chmod -R 777 uploads downloads temp logs cache

# Rebuild images
echo "🔨 Rebuilding Docker images..."
docker-compose build --no-cache

# Start services
echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 15

# Check if databases were initialized
echo "🗄️  Verifying database initialization..."
docker-compose exec -T app ls -lh /app/data/

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
echo ""
echo "To check database files:"
echo "  docker-compose exec app ls -lh /app/data/"
