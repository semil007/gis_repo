#!/bin/bash

# HMO Document Processing Pipeline - Automated Installation Script
# This script provides one-command installation for Ubuntu servers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/YOUR_USERNAME/hmo-document-processor.git"
APP_DIR="hmo-document-processor"

echo -e "${BLUE}"
echo "🏠 HMO Document Processing Pipeline"
echo "========================================="
echo "Automated Installation Script"
echo -e "${NC}"

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root for security reasons"
   print_info "Please run as a regular user with sudo privileges"
   exit 1
fi

# Check Ubuntu version
if ! command -v lsb_release &> /dev/null; then
    print_error "This script is designed for Ubuntu systems"
    exit 1
fi

UBUNTU_VERSION=$(lsb_release -rs)
print_info "Detected Ubuntu $UBUNTU_VERSION"

# Update system packages
print_info "Updating system packages..."
sudo apt-get update -qq

# Install required system packages
print_info "Installing system dependencies..."
sudo apt-get install -y -qq curl wget git unzip

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_info "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    print_status "Docker installed successfully"
else
    print_status "Docker is already installed"
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_info "Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    print_status "Docker Compose installed successfully"
else
    print_status "Docker Compose is already installed"
fi

# Clone repository if it doesn't exist
if [ ! -d "$APP_DIR" ]; then
    print_info "Cloning repository..."
    git clone $REPO_URL $APP_DIR
    print_status "Repository cloned successfully"
else
    print_info "Repository already exists, updating..."
    cd $APP_DIR
    git pull
    cd ..
    print_status "Repository updated successfully"
fi

# Enter application directory
cd $APP_DIR

# Make scripts executable
print_info "Setting up permissions..."
chmod +x start-docker.sh
chmod +x install.sh

# Create necessary directories
print_info "Creating application directories..."
mkdir -p uploads downloads temp logs cache data
chmod 755 uploads downloads temp logs cache data

# Check if user is in docker group
if ! groups $USER | grep -q docker; then
    print_warning "User $USER is not in the docker group"
    print_info "Adding user to docker group..."
    sudo usermod -aG docker $USER
    print_warning "You need to log out and log back in for group changes to take effect"
    print_info "After logging back in, run: cd $APP_DIR && ./start-docker.sh"
    exit 0
fi

# Start the application
print_info "Starting HMO Document Processing Pipeline..."
./start-docker.sh

# Final instructions
echo ""
echo -e "${GREEN}🎉 Installation completed successfully!${NC}"
echo ""
echo -e "${BLUE}📱 Access your application at:${NC}"
echo "   • Local:  http://localhost:8501"
echo "   • Remote: http://$(hostname -I | awk '{print $1}'):8501"
echo ""
echo -e "${BLUE}🔧 Useful commands:${NC}"
echo "   • View logs:     docker-compose logs -f"
echo "   • Stop services: docker-compose down"
echo "   • Restart:       docker-compose restart"
echo "   • Update app:    git pull && docker-compose up -d --build"
echo ""
echo -e "${BLUE}📚 Documentation:${NC}"
echo "   • README.md for detailed information"
echo "   • UBUNTU_DEPLOYMENT.md for deployment guide"
echo ""

# Check if services are running
sleep 5
if docker-compose ps | grep -q "Up"; then
    print_status "All services are running successfully!"
else
    print_warning "Some services may not be running. Check with: docker-compose ps"
fi

echo -e "${GREEN}Happy processing! 🚀${NC}"