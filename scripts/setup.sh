#!/bin/bash

# Document Processing Pipeline - Ubuntu Setup Script
# This script sets up the application on Ubuntu server

set -e

echo "🚀 Setting up Document Processing Pipeline..."

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please do not run this script as root"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Update system packages
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install required system packages
echo "🔧 Installing system dependencies..."
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    poppler-utils \
    libpoppler-cpp-dev \
    redis-server \
    git \
    curl \
    wget \
    build-essential \
    libssl-dev \
    libffi-dev \
    libjpeg-dev \
    libpng-dev \
    libopencv-dev \
    python3-opencv

# Install Docker if not present
if ! command_exists docker; then
    echo "🐳 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
    sudo usermod -aG docker $USER
fi

# Install Docker Compose if not present
if ! command_exists docker-compose; then
    echo "🐙 Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Start and enable services
echo "🔴 Starting Redis service..."
sudo systemctl start redis-server
sudo systemctl enable redis-server

echo "🐳 Starting Docker service..."
sudo systemctl start docker
sudo systemctl enable docker

# Create environment file from example
if [ ! -f .env ]; then
    echo "📝 Creating environment configuration..."
    cp .env.example .env
    echo "⚠️  Please review and update .env file with your specific configuration"
fi

# Create necessary directories
echo "📁 Creating application directories..."
mkdir -p uploads downloads temp logs

# Set permissions
echo "🔐 Setting permissions..."
chmod +x scripts/*.sh
chmod 755 uploads downloads temp logs

# Option 1: Native Python setup
echo ""
echo "🐍 Setting up Python virtual environment (for native deployment)..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Download spaCy model
echo "🧠 Downloading spaCy English model..."
python -m spacy download en_core_web_sm

# Create systemd service file for native deployment
echo "⚙️  Creating systemd service..."
sudo tee /etc/systemd/system/document-processor.service > /dev/null <<EOF
[Unit]
Description=Document Processing Pipeline
After=network.target redis.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/streamlit run web/streamlit_app.py --server.port=8501 --server.address=0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable document-processor.service

# Build Docker images
echo "🏗️  Building Docker images..."
docker-compose build

echo "✅ Setup complete!"
echo ""
echo "Deployment Options:"
echo "1. Native Python deployment:"
echo "   - Run: ./scripts/start.sh"
echo "   - Access: http://localhost:8501"
echo ""
echo "2. Docker deployment (recommended):"
echo "   - Run: docker-compose up -d"
echo "   - Access: http://localhost:8501"
echo ""
echo "⚠️  Important:"
echo "1. Log out and log back in (or run 'newgrp docker') to use Docker without sudo"
echo "2. Review and update .env file with your configuration"
echo "3. Ensure firewall allows access to port 8501"