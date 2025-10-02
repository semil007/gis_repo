@echo off
REM Quick fix script to rebuild and restart Docker containers (Windows version)

echo 🔧 Fixing Docker deployment...
echo.

REM Stop existing containers
echo ⏹️  Stopping existing containers...
docker-compose down -v

REM Remove old images to force rebuild
echo 🗑️  Removing old images...
docker-compose rm -f

REM Remove old database files if they exist (we'll use Docker volumes instead)
echo 🗑️  Cleaning up old database files...
if exist processing_sessions.db (
    del /f processing_sessions.db
    echo Removed old processing_sessions.db
)

if exist audit_data.db (
    del /f audit_data.db
    echo Removed old audit_data.db
)

REM Create required directories
echo 📁 Creating required directories...
if not exist uploads mkdir uploads
if not exist downloads mkdir downloads
if not exist temp mkdir temp
if not exist logs mkdir logs
if not exist cache mkdir cache

REM Rebuild images
echo 🔨 Rebuilding Docker images...
docker-compose build --no-cache

REM Start services
echo 🚀 Starting services...
docker-compose up -d

REM Wait for services to start
echo ⏳ Waiting for services to start...
timeout /t 15 /nobreak >nul

REM Check if databases were initialized
echo 🗄️  Verifying database initialization...
docker-compose exec -T app ls -lh /app/data/

REM Check status
echo.
echo 📊 Service Status:
docker-compose ps

echo.
echo 📋 Checking logs for errors...
docker-compose logs --tail=50 app

echo.
echo ✅ Fix complete!
echo.
echo Access the application at: http://192.168.1.49:8501
echo.
echo To view logs:
echo   docker-compose logs -f app
echo   docker-compose logs -f worker
echo   docker-compose logs -f redis
echo.
echo To check database files:
echo   docker-compose exec app ls -lh /app/data/
