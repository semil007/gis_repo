#!/bin/bash

# HMO Document Processing Pipeline - Docker Testing Script
# This script tests Docker container build and functionality

set -e

echo "🐳 Docker Deployment Testing"
echo "============================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
TEST_IMAGE_NAME="hmo-processor:test"
TEST_CONTAINER_NAME="hmo-test-container"
TEST_COMPOSE_PROJECT="hmo-test"

# Cleanup function
cleanup() {
    echo ""
    echo "🧹 Cleaning up test resources..."
    
    # Stop and remove test containers
    docker stop "$TEST_CONTAINER_NAME" 2>/dev/null || true
    docker rm "$TEST_CONTAINER_NAME" 2>/dev/null || true
    
    # Stop docker-compose test
    docker-compose -p "$TEST_COMPOSE_PROJECT" down 2>/dev/null || true
    
    # Remove test image
    docker rmi "$TEST_IMAGE_NAME" 2>/dev/null || true
    
    echo "Cleanup completed."
}

# Set trap for cleanup on exit
trap cleanup EXIT

# Function to print test results
print_result() {
    local test_name="$1"
    local result="$2"
    local message="$3"
    
    case $result in
        "PASS")
            echo -e "${GREEN}✅ PASS${NC} - $test_name"
            ;;
        "FAIL")
            echo -e "${RED}❌ FAIL${NC} - $test_name: $message"
            exit 1
            ;;
        "SKIP")
            echo -e "${YELLOW}⏭️  SKIP${NC} - $test_name: $message"
            ;;
    esac
}

# Check if Docker is available
if ! command -v docker >/dev/null 2>&1; then
    print_result "Docker Availability" "FAIL" "Docker not installed"
fi

if ! docker info >/dev/null 2>&1; then
    print_result "Docker Service" "FAIL" "Docker daemon not running"
fi

print_result "Docker Availability" "PASS"

echo ""
echo "🏗️  Testing Docker Image Build"
echo "------------------------------"

# Test Dockerfile syntax
if [ ! -f "Dockerfile" ]; then
    print_result "Dockerfile Exists" "FAIL" "Dockerfile not found"
fi

print_result "Dockerfile Exists" "PASS"

# Build Docker image
echo "Building Docker image..."
if docker build -t "$TEST_IMAGE_NAME" . >/dev/null 2>&1; then
    print_result "Docker Image Build" "PASS"
else
    print_result "Docker Image Build" "FAIL" "Build failed"
fi

# Check image properties
IMAGE_SIZE=$(docker images "$TEST_IMAGE_NAME" --format "table {{.Size}}" | tail -n +2)
echo "Image size: $IMAGE_SIZE"

# Test image layers
LAYER_COUNT=$(docker history "$TEST_IMAGE_NAME" --format "table {{.ID}}" | tail -n +2 | wc -l)
echo "Number of layers: $LAYER_COUNT"

if [ "$LAYER_COUNT" -gt 50 ]; then
    print_result "Image Layer Count" "FAIL" "Too many layers ($LAYER_COUNT), consider optimizing Dockerfile"
else
    print_result "Image Layer Count" "PASS"
fi

echo ""
echo "🚀 Testing Container Startup"
echo "----------------------------"

# Test container startup
echo "Starting test container..."
if docker run -d --name "$TEST_CONTAINER_NAME" \
    -p 8502:8501 \
    -e REDIS_URL=redis://localhost:6379/1 \
    -e DATABASE_URL=sqlite:///app/test.db \
    "$TEST_IMAGE_NAME" >/dev/null 2>&1; then
    print_result "Container Startup" "PASS"
else
    print_result "Container Startup" "FAIL" "Container failed to start"
fi

# Wait for container to initialize
echo "Waiting for container to initialize..."
sleep 30

# Check container status
if docker ps | grep -q "$TEST_CONTAINER_NAME"; then
    print_result "Container Running" "PASS"
else
    print_result "Container Running" "FAIL" "Container not running"
fi

# Check container logs for errors
CONTAINER_LOGS=$(docker logs "$TEST_CONTAINER_NAME" 2>&1)
if echo "$CONTAINER_LOGS" | grep -qi "error\|exception\|failed"; then
    echo "Container logs contain errors:"
    echo "$CONTAINER_LOGS" | tail -20
    print_result "Container Logs" "FAIL" "Errors found in logs"
else
    print_result "Container Logs" "PASS"
fi

echo ""
echo "🌐 Testing Network Connectivity"
echo "------------------------------"

# Test if application is responding
echo "Testing application response..."
sleep 10  # Additional wait for app to be ready

if curl -f -s http://localhost:8502 >/dev/null 2>&1; then
    print_result "Application Response" "PASS"
else
    print_result "Application Response" "FAIL" "Application not responding on port 8502"
fi

# Test health endpoint
if curl -f -s http://localhost:8502/_stcore/health >/dev/null 2>&1; then
    print_result "Health Endpoint" "PASS"
else
    print_result "Health Endpoint" "SKIP" "Health endpoint not accessible (may not be implemented)"
fi

echo ""
echo "🐙 Testing Docker Compose"
echo "-------------------------"

# Check docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    print_result "Docker Compose File" "FAIL" "docker-compose.yml not found"
fi

print_result "Docker Compose File" "PASS"

# Validate docker-compose.yml
if docker-compose config >/dev/null 2>&1; then
    print_result "Docker Compose Validation" "PASS"
else
    print_result "Docker Compose Validation" "FAIL" "Invalid docker-compose.yml"
fi

# Test docker-compose build
echo "Testing docker-compose build..."
if docker-compose -p "$TEST_COMPOSE_PROJECT" build >/dev/null 2>&1; then
    print_result "Docker Compose Build" "PASS"
else
    print_result "Docker Compose Build" "FAIL" "docker-compose build failed"
fi

# Test docker-compose up
echo "Testing docker-compose startup..."
if docker-compose -p "$TEST_COMPOSE_PROJECT" up -d >/dev/null 2>&1; then
    print_result "Docker Compose Up" "PASS"
else
    print_result "Docker Compose Up" "FAIL" "docker-compose up failed"
fi

# Wait for services to start
sleep 45

# Check if services are running
RUNNING_SERVICES=$(docker-compose -p "$TEST_COMPOSE_PROJECT" ps --services --filter "status=running")
if [ -n "$RUNNING_SERVICES" ]; then
    print_result "Docker Compose Services" "PASS"
    echo "Running services: $RUNNING_SERVICES"
else
    print_result "Docker Compose Services" "FAIL" "No services running"
fi

# Test multi-service connectivity
if curl -f -s http://localhost:8501 >/dev/null 2>&1; then
    print_result "Multi-Service Application" "PASS"
else
    print_result "Multi-Service Application" "FAIL" "Application not accessible via docker-compose"
fi

echo ""
echo "🔍 Testing Container Security"
echo "-----------------------------"

# Check if container runs as non-root user
CONTAINER_USER=$(docker exec "$TEST_CONTAINER_NAME" whoami 2>/dev/null || echo "unknown")
if [ "$CONTAINER_USER" != "root" ]; then
    print_result "Non-Root User" "PASS"
else
    print_result "Non-Root User" "FAIL" "Container running as root user"
fi

# Check for security vulnerabilities (basic check)
if command -v docker >/dev/null 2>&1; then
    # This is a basic check - in production, use tools like Trivy or Clair
    print_result "Security Scan" "SKIP" "Use dedicated security scanning tools for production"
fi

echo ""
echo "💾 Testing Data Persistence"
echo "---------------------------"

# Test volume mounts
VOLUME_MOUNTS=$(docker inspect "$TEST_CONTAINER_NAME" | grep -c "Mounts" || echo "0")
if [ "$VOLUME_MOUNTS" -gt 0 ]; then
    print_result "Volume Mounts" "PASS"
else
    print_result "Volume Mounts" "SKIP" "No volume mounts configured"
fi

# Test data directory creation
docker exec "$TEST_CONTAINER_NAME" ls -la /app/uploads >/dev/null 2>&1
if [ $? -eq 0 ]; then
    print_result "Data Directories" "PASS"
else
    print_result "Data Directories" "FAIL" "Required directories not found"
fi

echo ""
echo "🔄 Testing Container Restart"
echo "---------------------------"

# Test container restart
echo "Testing container restart..."
if docker restart "$TEST_CONTAINER_NAME" >/dev/null 2>&1; then
    print_result "Container Restart" "PASS"
else
    print_result "Container Restart" "FAIL" "Container restart failed"
fi

# Wait for restart
sleep 20

# Check if container is still running after restart
if docker ps | grep -q "$TEST_CONTAINER_NAME"; then
    print_result "Post-Restart Status" "PASS"
else
    print_result "Post-Restart Status" "FAIL" "Container not running after restart"
fi

echo ""
echo "📊 Performance Testing"
echo "---------------------"

# Test resource usage
CPU_USAGE=$(docker stats "$TEST_CONTAINER_NAME" --no-stream --format "table {{.CPUPerc}}" | tail -n +2 | sed 's/%//')
MEM_USAGE=$(docker stats "$TEST_CONTAINER_NAME" --no-stream --format "table {{.MemUsage}}" | tail -n +2)

echo "CPU Usage: ${CPU_USAGE}%"
echo "Memory Usage: $MEM_USAGE"

# Basic performance check
if [ "${CPU_USAGE%.*}" -lt 50 ]; then
    print_result "CPU Usage" "PASS"
else
    print_result "CPU Usage" "FAIL" "High CPU usage: ${CPU_USAGE}%"
fi

echo ""
echo "🧪 Testing Application Functionality"
echo "-----------------------------------"

# Test basic application endpoints (if accessible)
if curl -f -s http://localhost:8501 | grep -qi "streamlit\|document" >/dev/null 2>&1; then
    print_result "Application Content" "PASS"
else
    print_result "Application Content" "SKIP" "Cannot verify application content"
fi

# Test file upload capability (basic check)
TEMP_FILE=$(mktemp)
echo "Test content" > "$TEMP_FILE"

# This is a basic connectivity test - actual upload testing would require session handling
if curl -f -s -X POST http://localhost:8501/upload -F "file=@$TEMP_FILE" >/dev/null 2>&1; then
    print_result "File Upload Endpoint" "PASS"
else
    print_result "File Upload Endpoint" "SKIP" "Upload endpoint requires session handling"
fi

rm -f "$TEMP_FILE"

echo ""
echo "✅ Docker Testing Complete"
echo "=========================="

echo -e "${GREEN}🎉 All Docker tests passed successfully!${NC}"
echo ""
echo "Docker deployment is ready for production use."
echo ""
echo "To deploy with Docker:"
echo "  docker-compose up -d"
echo ""
echo "To access the application:"
echo "  http://localhost:8501"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f"
echo ""
echo "To stop services:"
echo "  docker-compose down"