#!/bin/bash

# HMO Document Processing Pipeline - Deployment Validation Script
# This script validates that the deployment is working correctly

set -e

echo "🔍 HMO Document Processing Pipeline - Deployment Validation"
echo "============================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Function to print test results
print_result() {
    local test_name="$1"
    local result="$2"
    local message="$3"
    
    case $result in
        "PASS")
            echo -e "${GREEN}✅ PASS${NC} - $test_name"
            ((TESTS_PASSED++))
            ;;
        "FAIL")
            echo -e "${RED}❌ FAIL${NC} - $test_name: $message"
            ((TESTS_FAILED++))
            ;;
        "SKIP")
            echo -e "${YELLOW}⏭️  SKIP${NC} - $test_name: $message"
            ((TESTS_SKIPPED++))
            ;;
    esac
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if service is running
service_running() {
    if systemctl is-active --quiet "$1"; then
        return 0
    else
        return 1
    fi
}

# Function to check if Docker container is running
docker_container_running() {
    if docker ps --format "table {{.Names}}" | grep -q "$1"; then
        return 0
    else
        return 1
    fi
}

echo ""
echo "🔧 System Requirements Check"
echo "----------------------------"

# Check Operating System
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [[ "$ID" == "ubuntu" ]]; then
        print_result "Operating System (Ubuntu)" "PASS"
    else
        print_result "Operating System" "FAIL" "Not Ubuntu (found: $ID)"
    fi
else
    print_result "Operating System" "FAIL" "Cannot determine OS"
fi

# Check Python version
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
        print_result "Python Version ($PYTHON_VERSION)" "PASS"
    else
        print_result "Python Version" "FAIL" "Requires Python 3.8+ (found: $PYTHON_VERSION)"
    fi
else
    print_result "Python Installation" "FAIL" "Python3 not found"
fi

# Check Git
if command_exists git; then
    GIT_VERSION=$(git --version | cut -d' ' -f3)
    print_result "Git ($GIT_VERSION)" "PASS"
else
    print_result "Git Installation" "FAIL" "Git not found"
fi

# Check Docker
if command_exists docker; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | sed 's/,//')
    print_result "Docker ($DOCKER_VERSION)" "PASS"
else
    print_result "Docker Installation" "SKIP" "Docker not installed (optional)"
fi

# Check Docker Compose
if command_exists docker-compose; then
    COMPOSE_VERSION=$(docker-compose --version | cut -d' ' -f3 | sed 's/,//')
    print_result "Docker Compose ($COMPOSE_VERSION)" "PASS"
else
    print_result "Docker Compose" "SKIP" "Docker Compose not installed (optional)"
fi

echo ""
echo "📦 System Dependencies Check"
echo "----------------------------"

# Check Tesseract OCR
if command_exists tesseract; then
    TESSERACT_VERSION=$(tesseract --version 2>&1 | head -n1 | cut -d' ' -f2)
    print_result "Tesseract OCR ($TESSERACT_VERSION)" "PASS"
else
    print_result "Tesseract OCR" "FAIL" "Tesseract not installed"
fi

# Check Redis
if command_exists redis-server; then
    REDIS_VERSION=$(redis-server --version | cut -d' ' -f3 | cut -d'=' -f2)
    print_result "Redis Server ($REDIS_VERSION)" "PASS"
else
    print_result "Redis Server" "FAIL" "Redis not installed"
fi

# Check Redis CLI
if command_exists redis-cli; then
    print_result "Redis CLI" "PASS"
else
    print_result "Redis CLI" "FAIL" "Redis CLI not installed"
fi

echo ""
echo "📁 Project Structure Check"
echo "--------------------------"

# Check required files
REQUIRED_FILES=(
    "requirements.txt"
    "Dockerfile"
    "docker-compose.yml"
    ".env.example"
    "README.md"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_result "File: $file" "PASS"
    else
        print_result "File: $file" "FAIL" "File not found"
    fi
done

# Check required directories
REQUIRED_DIRS=(
    "scripts"
    "web"
    "models"
    "services"
    "processors"
    "tests"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        print_result "Directory: $dir" "PASS"
    else
        print_result "Directory: $dir" "FAIL" "Directory not found"
    fi
done

# Check script permissions
SCRIPTS=(
    "scripts/setup.sh"
    "scripts/start.sh"
    "scripts/stop.sh"
    "scripts/update.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        if [ -x "$script" ]; then
            print_result "Script executable: $script" "PASS"
        else
            print_result "Script executable: $script" "FAIL" "Not executable"
        fi
    else
        print_result "Script exists: $script" "FAIL" "Script not found"
    fi
done

echo ""
echo "🐍 Python Environment Check"
echo "---------------------------"

# Check virtual environment
if [ -d "venv" ]; then
    print_result "Virtual Environment" "PASS"
    
    # Check if virtual environment is functional
    if [ -f "venv/bin/activate" ]; then
        print_result "Virtual Environment Activation" "PASS"
    else
        print_result "Virtual Environment Activation" "FAIL" "Activation script not found"
    fi
else
    print_result "Virtual Environment" "SKIP" "Not using virtual environment"
fi

# Check Python packages (if venv exists)
if [ -d "venv" ]; then
    source venv/bin/activate 2>/dev/null || true
    
    CRITICAL_PACKAGES=(
        "streamlit"
        "fastapi"
        "pandas"
        "spacy"
        "redis"
    )
    
    for package in "${CRITICAL_PACKAGES[@]}"; do
        if pip show "$package" >/dev/null 2>&1; then
            VERSION=$(pip show "$package" | grep Version | cut -d' ' -f2)
            print_result "Python Package: $package ($VERSION)" "PASS"
        else
            print_result "Python Package: $package" "FAIL" "Package not installed"
        fi
    done
fi

echo ""
echo "🔧 Service Status Check"
echo "-----------------------"

# Check Redis service
if service_running "redis-server"; then
    print_result "Redis Service" "PASS"
else
    print_result "Redis Service" "FAIL" "Redis service not running"
fi

# Check application service (native deployment)
if service_running "document-processor"; then
    print_result "Application Service (Native)" "PASS"
else
    print_result "Application Service (Native)" "SKIP" "Service not configured or not running"
fi

# Check Docker containers (Docker deployment)
if command_exists docker; then
    if docker_container_running "hmo-processor"; then
        print_result "Application Container" "PASS"
    else
        print_result "Application Container" "SKIP" "Container not running"
    fi
    
    if docker_container_running "hmo-redis"; then
        print_result "Redis Container" "PASS"
    else
        print_result "Redis Container" "SKIP" "Container not running"
    fi
fi

echo ""
echo "🌐 Network Connectivity Check"
echo "-----------------------------"

# Check if ports are available
check_port() {
    local port=$1
    local service=$2
    
    if netstat -tlnp 2>/dev/null | grep -q ":$port "; then
        print_result "Port $port ($service)" "PASS"
    else
        print_result "Port $port ($service)" "FAIL" "Port not in use"
    fi
}

check_port "8501" "Streamlit"
check_port "6379" "Redis"

# Check web interface accessibility
if command_exists curl; then
    if curl -f -s http://localhost:8501 >/dev/null 2>&1; then
        print_result "Web Interface Accessibility" "PASS"
    else
        print_result "Web Interface Accessibility" "FAIL" "Cannot access http://localhost:8501"
    fi
else
    print_result "Web Interface Accessibility" "SKIP" "curl not available"
fi

# Check health endpoint
if command_exists curl; then
    if curl -f -s http://localhost:8501/_stcore/health >/dev/null 2>&1; then
        print_result "Health Endpoint" "PASS"
    else
        print_result "Health Endpoint" "SKIP" "Health endpoint not accessible"
    fi
fi

echo ""
echo "💾 Database Connectivity Check"
echo "------------------------------"

# Check Redis connectivity
if command_exists redis-cli; then
    if redis-cli ping >/dev/null 2>&1; then
        print_result "Redis Connectivity" "PASS"
    else
        print_result "Redis Connectivity" "FAIL" "Cannot connect to Redis"
    fi
fi

# Check SQLite databases
if [ -f "processing_sessions.db" ]; then
    if sqlite3 processing_sessions.db "SELECT name FROM sqlite_master WHERE type='table';" >/dev/null 2>&1; then
        print_result "SQLite Database (Sessions)" "PASS"
    else
        print_result "SQLite Database (Sessions)" "FAIL" "Database corrupted or inaccessible"
    fi
else
    print_result "SQLite Database (Sessions)" "SKIP" "Database not created yet"
fi

if [ -f "audit_data.db" ]; then
    if sqlite3 audit_data.db "SELECT name FROM sqlite_master WHERE type='table';" >/dev/null 2>&1; then
        print_result "SQLite Database (Audit)" "PASS"
    else
        print_result "SQLite Database (Audit)" "FAIL" "Database corrupted or inaccessible"
    fi
else
    print_result "SQLite Database (Audit)" "SKIP" "Database not created yet"
fi

echo ""
echo "🔐 Security Check"
echo "-----------------"

# Check file permissions
check_permissions() {
    local file=$1
    local expected_perm=$2
    local description=$3
    
    if [ -f "$file" ]; then
        ACTUAL_PERM=$(stat -c "%a" "$file" 2>/dev/null || stat -f "%A" "$file" 2>/dev/null)
        if [ "$ACTUAL_PERM" = "$expected_perm" ]; then
            print_result "Permissions: $description" "PASS"
        else
            print_result "Permissions: $description" "FAIL" "Expected $expected_perm, got $ACTUAL_PERM"
        fi
    else
        print_result "Permissions: $description" "SKIP" "File not found"
    fi
}

check_permissions ".env" "600" ".env file"
check_permissions "processing_sessions.db" "644" "Database files"

# Check directory permissions
if [ -d "uploads" ]; then
    UPLOAD_PERM=$(stat -c "%a" "uploads" 2>/dev/null || stat -f "%A" "uploads" 2>/dev/null)
    if [ "$UPLOAD_PERM" = "755" ] || [ "$UPLOAD_PERM" = "775" ]; then
        print_result "Directory Permissions: uploads" "PASS"
    else
        print_result "Directory Permissions: uploads" "FAIL" "Incorrect permissions: $UPLOAD_PERM"
    fi
else
    print_result "Directory Permissions: uploads" "SKIP" "Directory not found"
fi

echo ""
echo "🧪 Functional Tests"
echo "-------------------"

# Run Python deployment tests if available
if [ -f "tests/test_deployment.py" ]; then
    if command_exists pytest; then
        echo "Running Python deployment tests..."
        if python3 -m pytest tests/test_deployment.py -v --tb=short >/dev/null 2>&1; then
            print_result "Python Deployment Tests" "PASS"
        else
            print_result "Python Deployment Tests" "FAIL" "Some tests failed"
        fi
    else
        print_result "Python Deployment Tests" "SKIP" "pytest not available"
    fi
else
    print_result "Python Deployment Tests" "SKIP" "Test file not found"
fi

echo ""
echo "📊 Summary"
echo "=========="
echo -e "Tests Passed:  ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed:  ${RED}$TESTS_FAILED${NC}"
echo -e "Tests Skipped: ${YELLOW}$TESTS_SKIPPED${NC}"
echo ""

# Overall result
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 Deployment validation completed successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Access the web interface at: http://localhost:8501"
    echo "2. Upload a test document to verify functionality"
    echo "3. Check the audit interface for manual review capabilities"
    echo "4. Monitor logs for any issues: sudo journalctl -u document-processor.service -f"
    exit 0
else
    echo -e "${RED}❌ Deployment validation failed with $TESTS_FAILED error(s).${NC}"
    echo ""
    echo "Please address the failed tests before proceeding."
    echo "Check the deployment guide for troubleshooting steps."
    exit 1
fi