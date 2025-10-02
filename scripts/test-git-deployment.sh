#!/bin/bash

# HMO Document Processing Pipeline - Git Deployment Workflow Test
# This script tests Git-based deployment and update workflows

set -e

echo "📦 Git Deployment Workflow Testing"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
TEST_DIR="/tmp/hmo-deployment-test"
ORIGINAL_DIR=$(pwd)

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

# Cleanup function
cleanup() {
    echo ""
    echo "🧹 Cleaning up test environment..."
    cd "$ORIGINAL_DIR"
    rm -rf "$TEST_DIR" 2>/dev/null || true
    echo "Cleanup completed."
}

# Set trap for cleanup on exit
trap cleanup EXIT

echo ""
echo "🔍 Pre-deployment Checks"
echo "------------------------"

# Check if we're in a Git repository
if ! git rev-parse --git-dir >/dev/null 2>&1; then
    print_result "Git Repository" "FAIL" "Not in a Git repository"
fi

print_result "Git Repository" "PASS"

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    print_result "Clean Working Directory" "FAIL" "Uncommitted changes detected"
fi

print_result "Clean Working Directory" "PASS"

# Check required files exist
REQUIRED_FILES=(
    "README.md"
    "requirements.txt"
    "Dockerfile"
    "docker-compose.yml"
    ".gitignore"
    "scripts/setup.sh"
    "scripts/start.sh"
    "scripts/stop.sh"
    "scripts/update.sh"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_result "Required File: $file" "PASS"
    else
        print_result "Required File: $file" "FAIL" "File not found"
    fi
done

echo ""
echo "📋 Repository Structure Validation"
echo "----------------------------------"

# Check .gitignore configuration
if [ -f ".gitignore" ]; then
    GITIGNORE_CONTENT=$(cat .gitignore)
    
    IMPORTANT_PATTERNS=(
        "__pycache__"
        "*.pyc"
        ".env"
        "*.log"
        "uploads/"
        "downloads/"
        "temp/"
        "*.db"
    )
    
    for pattern in "${IMPORTANT_PATTERNS[@]}"; do
        if echo "$GITIGNORE_CONTENT" | grep -q "$pattern"; then
            print_result "Gitignore Pattern: $pattern" "PASS"
        else
            print_result "Gitignore Pattern: $pattern" "FAIL" "Pattern not found in .gitignore"
        fi
    done
fi

# Check that sensitive files are not tracked
SENSITIVE_FILES=(
    ".env"
    "*.log"
    "processing_sessions.db"
    "audit_data.db"
)

for pattern in "${SENSITIVE_FILES[@]}"; do
    if git ls-files | grep -q "$pattern"; then
        print_result "Sensitive File Check: $pattern" "FAIL" "Sensitive file is tracked by Git"
    else
        print_result "Sensitive File Check: $pattern" "PASS"
    fi
done

echo ""
echo "🚀 Simulated Fresh Deployment"
echo "-----------------------------"

# Create test deployment directory
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

# Get current repository URL (if available)
REPO_URL=$(git -C "$ORIGINAL_DIR" config --get remote.origin.url 2>/dev/null || echo "")

if [ -n "$REPO_URL" ]; then
    echo "Testing clone from: $REPO_URL"
    
    # Test git clone
    if git clone "$REPO_URL" hmo-processor >/dev/null 2>&1; then
        print_result "Git Clone" "PASS"
    else
        print_result "Git Clone" "FAIL" "Failed to clone repository"
    fi
    
    cd hmo-processor
else
    # If no remote URL, copy files for testing
    echo "No remote repository configured, copying files for testing..."
    cp -r "$ORIGINAL_DIR" hmo-processor
    cd hmo-processor
    print_result "File Copy (Simulated Clone)" "PASS"
fi

# Test setup script execution (dry run)
if [ -f "scripts/setup.sh" ]; then
    # Check script syntax
    if bash -n scripts/setup.sh; then
        print_result "Setup Script Syntax" "PASS"
    else
        print_result "Setup Script Syntax" "FAIL" "Syntax errors in setup.sh"
    fi
    
    # Test script permissions
    if [ -x "scripts/setup.sh" ]; then
        print_result "Setup Script Permissions" "PASS"
    else
        print_result "Setup Script Permissions" "FAIL" "setup.sh not executable"
    fi
fi

echo ""
echo "🔄 Update Workflow Testing"
echo "-------------------------"

# Test update script syntax
if [ -f "scripts/update.sh" ]; then
    if bash -n scripts/update.sh; then
        print_result "Update Script Syntax" "PASS"
    else
        print_result "Update Script Syntax" "FAIL" "Syntax errors in update.sh"
    fi
    
    # Check update script contains required operations
    UPDATE_CONTENT=$(cat scripts/update.sh)
    
    REQUIRED_OPERATIONS=(
        "git pull"
        "pip install"
        "systemctl\|docker-compose"
    )
    
    for operation in "${REQUIRED_OPERATIONS[@]}"; do
        if echo "$UPDATE_CONTENT" | grep -q "$operation"; then
            print_result "Update Operation: $operation" "PASS"
        else
            print_result "Update Operation: $operation" "FAIL" "Operation not found in update script"
        fi
    done
fi

echo ""
echo "🐳 Docker Deployment Workflow"
echo "-----------------------------"

# Test Docker Compose configuration
if [ -f "docker-compose.yml" ]; then
    if command -v docker-compose >/dev/null 2>&1; then
        if docker-compose config >/dev/null 2>&1; then
            print_result "Docker Compose Config" "PASS"
        else
            print_result "Docker Compose Config" "FAIL" "Invalid docker-compose.yml"
        fi
    else
        print_result "Docker Compose Config" "SKIP" "docker-compose not available"
    fi
fi

# Test Dockerfile
if [ -f "Dockerfile" ]; then
    # Check Dockerfile syntax (basic)
    DOCKERFILE_CONTENT=$(cat Dockerfile)
    
    DOCKERFILE_CHECKS=(
        "FROM ubuntu:"
        "COPY requirements.txt"
        "RUN pip3 install"
        "EXPOSE 8501"
        "CMD.*streamlit"
    )
    
    for check in "${DOCKERFILE_CHECKS[@]}"; do
        if echo "$DOCKERFILE_CONTENT" | grep -q "$check"; then
            print_result "Dockerfile Check: $check" "PASS"
        else
            print_result "Dockerfile Check: $check" "FAIL" "Required instruction not found"
        fi
    done
fi

echo ""
echo "🔧 Configuration Management"
echo "---------------------------"

# Test environment configuration
if [ -f ".env.example" ]; then
    print_result "Environment Template" "PASS"
    
    # Check for required configuration keys
    ENV_CONTENT=$(cat .env.example)
    
    REQUIRED_CONFIG=(
        "APP_NAME"
        "LOG_LEVEL"
        "STREAMLIT_PORT"
        "REDIS_URL"
        "DATABASE_URL"
        "MAX_FILE_SIZE"
    )
    
    for config in "${REQUIRED_CONFIG[@]}"; do
        if echo "$ENV_CONTENT" | grep -q "$config"; then
            print_result "Config Key: $config" "PASS"
        else
            print_result "Config Key: $config" "FAIL" "Required configuration not found"
        fi
    done
else
    print_result "Environment Template" "FAIL" ".env.example not found"
fi

echo ""
echo "📝 Documentation Validation"
echo "---------------------------"

# Test README.md
if [ -f "README.md" ]; then
    README_CONTENT=$(cat README.md)
    
    README_SECTIONS=(
        "Installation"
        "Usage"
        "Docker"
        "Troubleshooting"
    )
    
    for section in "${README_SECTIONS[@]}"; do
        if echo "$README_CONTENT" | grep -qi "$section"; then
            print_result "README Section: $section" "PASS"
        else
            print_result "README Section: $section" "FAIL" "Section not found in README"
        fi
    done
    
    # Check for installation commands
    if echo "$README_CONTENT" | grep -q "git clone\|docker-compose up"; then
        print_result "Installation Commands" "PASS"
    else
        print_result "Installation Commands" "FAIL" "Installation commands not found"
    fi
else
    print_result "README Documentation" "FAIL" "README.md not found"
fi

echo ""
echo "🔐 Security Validation"
echo "----------------------"

# Check for hardcoded secrets
SECURITY_PATTERNS=(
    "password.*="
    "secret.*="
    "key.*="
    "token.*="
)

SECURITY_ISSUES=0
for pattern in "${SECURITY_PATTERNS[@]}"; do
    if git grep -i "$pattern" -- '*.py' '*.sh' '*.yml' '*.yaml' >/dev/null 2>&1; then
        echo "⚠️  Potential hardcoded secret found: $pattern"
        ((SECURITY_ISSUES++))
    fi
done

if [ $SECURITY_ISSUES -eq 0 ]; then
    print_result "Hardcoded Secrets Check" "PASS"
else
    print_result "Hardcoded Secrets Check" "FAIL" "$SECURITY_ISSUES potential issues found"
fi

# Check file permissions in repository
EXECUTABLE_FILES=$(find . -name "*.sh" -type f)
for file in $EXECUTABLE_FILES; do
    if [ -x "$file" ]; then
        print_result "Script Executable: $file" "PASS"
    else
        print_result "Script Executable: $file" "FAIL" "Script not executable"
    fi
done

echo ""
echo "🧪 Deployment Simulation"
echo "------------------------"

# Simulate deployment steps
echo "Simulating deployment process..."

# Step 1: Environment setup
if cp .env.example .env 2>/dev/null; then
    print_result "Environment Setup" "PASS"
else
    print_result "Environment Setup" "SKIP" "No .env.example file"
fi

# Step 2: Directory creation
REQUIRED_DIRS=("uploads" "downloads" "temp" "logs")
for dir in "${REQUIRED_DIRS[@]}"; do
    if mkdir -p "$dir" 2>/dev/null; then
        print_result "Directory Creation: $dir" "PASS"
    else
        print_result "Directory Creation: $dir" "FAIL" "Cannot create directory"
    fi
done

# Step 3: Script permissions
if chmod +x scripts/*.sh 2>/dev/null; then
    print_result "Script Permissions Setup" "PASS"
else
    print_result "Script Permissions Setup" "FAIL" "Cannot set script permissions"
fi

echo ""
echo "📊 Deployment Readiness Summary"
echo "==============================="

# Check overall readiness
READINESS_SCORE=0
TOTAL_CHECKS=10

# Critical checks
if [ -f "requirements.txt" ]; then ((READINESS_SCORE++)); fi
if [ -f "Dockerfile" ]; then ((READINESS_SCORE++)); fi
if [ -f "docker-compose.yml" ]; then ((READINESS_SCORE++)); fi
if [ -f "scripts/setup.sh" ] && [ -x "scripts/setup.sh" ]; then ((READINESS_SCORE++)); fi
if [ -f "scripts/start.sh" ] && [ -x "scripts/start.sh" ]; then ((READINESS_SCORE++)); fi
if [ -f "scripts/stop.sh" ] && [ -x "scripts/stop.sh" ]; then ((READINESS_SCORE++)); fi
if [ -f "scripts/update.sh" ] && [ -x "scripts/update.sh" ]; then ((READINESS_SCORE++)); fi
if [ -f ".env.example" ]; then ((READINESS_SCORE++)); fi
if [ -f "README.md" ]; then ((READINESS_SCORE++)); fi
if [ -f ".gitignore" ]; then ((READINESS_SCORE++)); fi

READINESS_PERCENT=$((READINESS_SCORE * 100 / TOTAL_CHECKS))

echo "Deployment Readiness: $READINESS_SCORE/$TOTAL_CHECKS ($READINESS_PERCENT%)"

if [ $READINESS_PERCENT -ge 90 ]; then
    echo -e "${GREEN}🎉 Deployment is ready for production!${NC}"
elif [ $READINESS_PERCENT -ge 70 ]; then
    echo -e "${YELLOW}⚠️  Deployment is mostly ready, but some improvements needed.${NC}"
else
    echo -e "${RED}❌ Deployment needs significant work before production use.${NC}"
fi

echo ""
echo "✅ Git Deployment Testing Complete"
echo "=================================="

echo ""
echo "Deployment workflow validation completed successfully!"
echo ""
echo "To deploy from Git:"
echo "1. git clone <repository-url>"
echo "2. cd hmo-document-processor"
echo "3. ./scripts/setup.sh"
echo "4. ./scripts/start.sh"
echo ""
echo "To update deployment:"
echo "1. ./scripts/update.sh"
echo ""
echo "For Docker deployment:"
echo "1. docker-compose up -d"