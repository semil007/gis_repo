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

# Create fresh database files on host
echo "🗄️  Creating database files..."
rm -f processing_sessions.db audit_data.db
touch processing_sessions.db audit_data.db
chmod 666 processing_sessions.db audit_data.db
echo "Created: processing_sessions.db"
echo "Created: audit_data.db"

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
sleep 30

# Initialize databases
echo "🗄️  Initializing database schemas..."
docker-compose exec -T app python3 init_databases.py

# Restart services to ensure everything is loaded
echo "🔄 Restarting services..."
docker-compose restart app worker

# Wait a bit more
sleep 10

# Check status
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "📋 Checking logs for errors..."
docker-compose logs --tail=30 app

echo ""
echo "🗄️  Database files:"
ls -lh *.db

echo ""
echo "✅ Fix complete!"
echo ""
echo "Access the application at: http://192.168.1.49:8501"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f app"
echo "  docker-compose logs -f worker"
echo "  docker-compose logs -f redis"
