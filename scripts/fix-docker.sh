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

# Initialize database files on host
echo "🗄️  Initializing database files..."
if [ ! -f "processing_sessions.db" ] || [ ! -s "processing_sessions.db" ]; then
    echo "Creating processing_sessions.db..."
    touch processing_sessions.db
    chmod 666 processing_sessions.db
fi

if [ ! -f "audit_data.db" ] || [ ! -s "audit_data.db" ]; then
    echo "Creating audit_data.db..."
    touch audit_data.db
    chmod 666 audit_data.db
fi

# Create required directories
echo "📁 Creating required directories..."
mkdir -p uploads downloads temp logs cache

# Set proper permissions
echo "🔐 Setting permissions..."
chmod -R 777 uploads downloads temp logs cache
chmod 666 processing_sessions.db audit_data.db

# Rebuild images
echo "🔨 Rebuilding Docker images..."
docker-compose build --no-cache

# Start services
echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Initialize databases inside container
echo "🗄️  Initializing database schemas..."
docker-compose exec -T app python3 init_databases.py

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
