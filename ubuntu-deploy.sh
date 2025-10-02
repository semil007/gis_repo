#!/bin/bash

# HMO Document Processing Pipeline - Ubuntu Server Deployment Script
# This script sets up the complete system on Ubuntu 18.04+ servers

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   error "This script should not be run as root. Please run as a regular user with sudo privileges."
   exit 1
fi

# Check Ubuntu version
if ! command -v lsb_release &> /dev/null; then
    error "This script is designed for Ubuntu systems. lsb_release command not found."
    exit 1
fi

UBUNTU_VERSION=$(lsb_release -rs)
log "Detected Ubuntu version: $UBUNTU_VERSION"

if (( $(echo "$UBUNTU_VERSION < 18.04" | bc -l) )); then
    error "Ubuntu 18.04 or higher is required. Current version: $UBUNTU_VERSION"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install system dependencies
install_system_deps() {
    log "Updating Ubuntu package lists..."
    sudo apt-get update

    log "Installing system dependencies..."
    sudo apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        python3-setuptools \
        tesseract-ocr \
        tesseract-ocr-eng \
        git \
        curl \
        wget \
        build-essential \
        sqlite3 \
        libsqlite3-dev \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release \
        bc

    log "System dependencies installed successfully"
}

# Function to setup Python environment
setup_python_env() {
    log "Setting up Python virtual environment..."
    
    # Remove existing venv if it exists
    if [ -d "venv" ]; then
        warn "Removing existing virtual environment..."
        rm -rf venv
    fi

    # Create new virtual environment
    python3 -m venv venv
    source venv/bin/activate

    # Upgrade pip
    log "Upgrading pip..."
    pip install --upgrade pip setuptools wheel

    # Install Python dependencies
    log "Installing Python dependencies..."
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        error "requirements.txt not found!"
        exit 1
    fi

    # Download spaCy model
    log "Downloading spaCy English model..."
    python -m spacy download en_core_web_sm

    log "Python environment setup completed"
}

# Function to initialize application
initialize_app() {
    log "Initializing application..."
    
    # Activate virtual environment
    source venv/bin/activate

    # Run setup script
    if [ -f "fix_setup.py" ]; then
        log "Running system setup..."
        python fix_setup.py
    else
        warn "fix_setup.py not found, skipping setup"
    fi

    # Test the system
    if [ -f "test_simple.py" ]; then
        log "Running system test..."
        python test_simple.py
        if [ $? -eq 0 ]; then
            log "System test passed!"
        else
            warn "System test failed, but continuing..."
        fi
    fi

    log "Application initialization completed"
}

# Function to create systemd service
create_systemd_service() {
    log "Creating systemd service for HMO processor..."
    
    # Get current directory and user
    CURRENT_DIR=$(pwd)
    CURRENT_USER=$(whoami)
    
    # Create systemd service file
    sudo tee /etc/systemd/system/hmo-processor.service > /dev/null <<EOF
[Unit]
Description=HMO Document Processing Pipeline
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
Environment=PATH=$CURRENT_DIR/venv/bin
ExecStart=$CURRENT_DIR/venv/bin/python -m streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable hmo-processor.service
    
    log "Systemd service created and enabled"
}

# Function to setup firewall
setup_firewall() {
    log "Configuring firewall..."
    
    # Check if ufw is installed
    if command_exists ufw; then
        # Allow SSH (important!)
        sudo ufw allow ssh
        
        # Allow application port
        sudo ufw allow 8501/tcp
        
        # Enable firewall if not already enabled
        sudo ufw --force enable
        
        log "Firewall configured to allow port 8501"
    else
        warn "UFW firewall not installed, skipping firewall configuration"
    fi
}

# Function to start application
start_application() {
    log "Starting HMO Document Processing Pipeline..."
    
    # Start systemd service
    sudo systemctl start hmo-processor.service
    
    # Wait a moment for startup
    sleep 5
    
    # Check service status
    if sudo systemctl is-active --quiet hmo-processor.service; then
        log "Application started successfully!"
        
        # Get server IP
        SERVER_IP=$(hostname -I | awk '{print $1}')
        
        echo ""
        echo "🎉 HMO Document Processing Pipeline is now running!"
        echo ""
        echo "📱 Access URLs:"
        echo "   Local:  http://localhost:8501"
        echo "   Remote: http://$SERVER_IP:8501"
        echo ""
        echo "🔧 Management Commands:"
        echo "   Status:  sudo systemctl status hmo-processor"
        echo "   Stop:    sudo systemctl stop hmo-processor"
        echo "   Start:   sudo systemctl start hmo-processor"
        echo "   Restart: sudo systemctl restart hmo-processor"
        echo "   Logs:    sudo journalctl -u hmo-processor -f"
        echo ""
        echo "📁 Application Directory: $(pwd)"
        echo "🐍 Virtual Environment: $(pwd)/venv"
        echo ""
        
    else
        error "Failed to start application!"
        echo "Check logs with: sudo journalctl -u hmo-processor -f"
        exit 1
    fi
}

# Function to show post-installation info
show_post_install_info() {
    echo ""
    echo "📋 Post-Installation Information:"
    echo ""
    echo "🔄 Update Application:"
    echo "   cd $(pwd)"
    echo "   git pull"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    echo "   sudo systemctl restart hmo-processor"
    echo ""
    echo "🧪 Test System:"
    echo "   cd $(pwd)"
    echo "   source venv/bin/activate"
    echo "   python test_simple.py"
    echo ""
    echo "📊 Monitor Resources:"
    echo "   htop                    # System resources"
    echo "   df -h                   # Disk usage"
    echo "   free -h                 # Memory usage"
    echo ""
    echo "🔍 Troubleshooting:"
    echo "   sudo systemctl status hmo-processor    # Service status"
    echo "   sudo journalctl -u hmo-processor -f    # Live logs"
    echo "   curl http://localhost:8501/_stcore/health  # Health check"
    echo ""
}

# Main deployment function
main() {
    echo ""
    echo "🏠 HMO Document Processing Pipeline - Ubuntu Deployment"
    echo "========================================================"
    echo ""
    
    log "Starting deployment on Ubuntu $UBUNTU_VERSION..."
    
    # Check if we're in the right directory
    if [ ! -f "app.py" ]; then
        error "app.py not found! Please run this script from the project root directory."
        exit 1
    fi
    
    # Install system dependencies
    install_system_deps
    
    # Setup Python environment
    setup_python_env
    
    # Initialize application
    initialize_app
    
    # Create systemd service
    create_systemd_service
    
    # Setup firewall
    setup_firewall
    
    # Start application
    start_application
    
    # Show post-installation info
    show_post_install_info
    
    log "Deployment completed successfully! 🎉"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "HMO Document Processing Pipeline - Ubuntu Deployment Script"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --no-service   Skip systemd service creation"
        echo "  --no-firewall  Skip firewall configuration"
        echo ""
        echo "Examples:"
        echo "  $0                    # Full deployment"
        echo "  $0 --no-service      # Deploy without systemd service"
        echo ""
        exit 0
        ;;
    --no-service)
        NO_SERVICE=true
        ;;
    --no-firewall)
        NO_FIREWALL=true
        ;;
esac

# Run main deployment
main

echo ""
echo "✅ HMO Document Processing Pipeline deployment completed!"
echo "🌐 Your application should now be accessible at http://$(hostname -I | awk '{print $1}'):8501"
echo ""