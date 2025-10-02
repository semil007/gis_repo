#!/bin/bash

# Document Processing Pipeline - Update Script
# Updates the application from Git repository

set -e

echo "🔄 Updating Document Processing Pipeline..."

# Function to check if Docker Compose is available
check_docker_compose() {
    if command -v docker-compose >/dev/null 2>&1 && [ -f "docker-compose.yml" ]; then
        return 0
    else
        return 1
    fi
}

# Function to check if we're in a git repository
check_git_repo() {
    if git rev-parse --git-dir > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Check if we're in a git repository
if ! check_git_repo; then
    echo "❌ Not in a Git repository. Please ensure you're in the project directory."
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "⚠️  You have uncommitted changes. Please commit or stash them before updating."
    git status --porcelain
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Determine deployment method
DEPLOYMENT_METHOD=""
if [ "$1" = "--docker" ] || [ "$1" = "-d" ]; then
    DEPLOYMENT_METHOD="docker"
elif [ "$1" = "--native" ] || [ "$1" = "-n" ]; then
    DEPLOYMENT_METHOD="native"
else
    # Auto-detect based on what's running
    if check_docker_compose && docker-compose ps | grep -q "Up"; then
        DEPLOYMENT_METHOD="docker"
        echo "🐳 Docker deployment detected"
    else
        DEPLOYMENT_METHOD="native"
        echo "💻 Native deployment detected"
    fi
fi

# Stop the application
echo "🛑 Stopping application..."
./scripts/stop.sh $DEPLOYMENT_METHOD

# Backup current state
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
echo "💾 Creating backup in $BACKUP_DIR..."
mkdir -p "$BACKUP_DIR"
cp -r uploads downloads logs *.db "$BACKUP_DIR/" 2>/dev/null || true

# Pull latest changes from Git
echo "📥 Pulling latest changes from Git..."
CURRENT_BRANCH=$(git branch --show-current)
git fetch origin
git pull origin "$CURRENT_BRANCH"

# Update based on deployment method
if [ "$DEPLOYMENT_METHOD" = "docker" ]; then
    echo "🐳 Updating Docker deployment..."
    
    # Rebuild Docker images
    echo "🏗️  Rebuilding Docker images..."
    docker-compose build --no-cache
    
    # Update environment file if needed
    if [ -f ".env.example" ] && [ ! -f ".env" ]; then
        echo "📝 Creating environment file..."
        cp .env.example .env
        echo "⚠️  Please review .env file for any new configuration options"
    fi
    
else
    echo "💻 Updating native deployment..."
    
    # Activate virtual environment if it exists
    if [ -d "venv" ]; then
        echo "🐍 Activating virtual environment..."
        source venv/bin/activate
        
        # Update Python dependencies
        echo "📚 Updating Python dependencies..."
        pip install --upgrade -r requirements.txt
        
        # Update spaCy model if needed
        echo "🧠 Updating spaCy model..."
        python -m spacy download en_core_web_sm
    else
        echo "⚠️  Virtual environment not found. Please run setup.sh first."
    fi
fi

# Set permissions for scripts
echo "🔐 Setting script permissions..."
chmod +x scripts/*.sh

# Create necessary directories
mkdir -p uploads downloads temp logs

# Restore data from backup
echo "🔄 Restoring data from backup..."
cp -r "$BACKUP_DIR"/* . 2>/dev/null || true

# Update systemd service if needed (for native deployment)
if [ "$DEPLOYMENT_METHOD" = "native" ]; then
    echo "⚙️  Updating systemd service..."
    sudo systemctl daemon-reload
fi

# Restart the application
echo "🚀 Restarting application..."
./scripts/start.sh $DEPLOYMENT_METHOD

echo "✅ Update complete!"
echo "📱 Web interface available at: http://localhost:8501"
echo "💾 Backup created in: $BACKUP_DIR"
echo ""
echo "If you encounter issues, you can restore from backup:"
echo "  cp -r $BACKUP_DIR/* ."