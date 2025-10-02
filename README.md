# Document Processing Pipeline

An automated document processing system that converts semi-structured and unstructured PDF/DOCX files containing HMO (Houses in Multiple Occupation) licensing data into standardized CSV format.

## Features

- 📄 **Multi-format Support**: Process PDF and DOCX files with intelligent format detection
- 🤖 **Intelligent Extraction**: Uses OCR, NLP, and ML for accurate data extraction
- 🌐 **Web Interface**: Simple drag-and-drop interface built with Streamlit
- ✅ **Quality Assurance**: Confidence scoring and manual review capabilities
- 🔧 **Configurable**: Customizable column mappings and validation rules
- 🐳 **Docker Ready**: Easy deployment with Docker containers
- 🔄 **Queue Processing**: Redis-based queue system for concurrent processing
- 📊 **Audit Interface**: Manual review system for flagged records
- 🆓 **Open Source**: Built entirely with free and open-source technologies

## System Requirements

### Minimum Requirements
- **OS**: Ubuntu 20.04+ (recommended), Ubuntu 18.04+ (supported)
- **CPU**: 2 cores, 2.4 GHz
- **RAM**: 4 GB (8 GB recommended for large files)
- **Storage**: 10 GB free space
- **Network**: Internet connection for initial setup

### Recommended for Production
- **OS**: Ubuntu 22.04 LTS
- **CPU**: 4+ cores, 3.0+ GHz
- **RAM**: 8+ GB
- **Storage**: 50+ GB SSD
- **Network**: Stable internet connection

## Installation Guide

### Option 1: Automated Setup (Recommended)

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd document-processing-pipeline
   ```

2. **Run the automated setup:**
   ```bash
   chmod +x scripts/*.sh
   ./scripts/setup.sh
   ```

3. **Configure environment (optional):**
   ```bash
   cp .env.example .env
   nano .env  # Edit configuration as needed
   ```

4. **Start the application:**
   ```bash
   ./scripts/start.sh
   ```

5. **Access the web interface:**
   Open your browser and navigate to `http://localhost:8501`

### Option 2: Docker Deployment (Production Ready)

1. **Prerequisites:**
   ```bash
   # Install Docker and Docker Compose
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   
   # Install Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   
   # Log out and back in to apply Docker group membership
   ```

2. **Deploy with Docker:**
   ```bash
   git clone <repository-url>
   cd document-processing-pipeline
   
   # Configure environment
   cp .env.example .env
   nano .env  # Update configuration
   
   # Build and start services
   docker-compose up -d
   
   # Check service status
   docker-compose ps
   ```

3. **Access the application:**
   - Web Interface: `http://localhost:8501`
   - Redis: `localhost:6379` (internal use)

### Option 3: Manual Installation

<details>
<summary>Click to expand manual installation steps</summary>

1. **Install system dependencies:**
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3 python3-pip python3-venv python3-dev \
       tesseract-ocr tesseract-ocr-eng libtesseract-dev \
       poppler-utils libpoppler-cpp-dev redis-server git curl \
       build-essential libssl-dev libffi-dev libjpeg-dev libpng-dev \
       libopencv-dev python3-opencv
   ```

2. **Create Python virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```

3. **Start services:**
   ```bash
   sudo systemctl start redis-server
   sudo systemctl enable redis-server
   ```

4. **Run the application:**
   ```bash
   streamlit run web/streamlit_app.py --server.port=8501 --server.address=0.0.0.0
   ```

</details>

## Usage

1. **Upload Documents**: Drag and drop PDF or DOCX files containing HMO licensing data
2. **Configure Columns**: Optionally customize column mappings for your specific format
3. **Process**: Click "Convert" to start the automated extraction process
4. **Review**: Check flagged records in the audit interface if needed
5. **Download**: Get your standardized CSV file

## Project Structure

```
document-processing-pipeline/
├── models/              # Data models and schemas
├── services/            # Business logic and service layer
├── processors/          # Document processing engines
├── web/                # Streamlit web interface
├── config/             # Configuration management
├── utils/              # Utility functions
├── tests/              # Test suite
├── scripts/            # Deployment and management scripts
├── requirements.txt    # Python dependencies
├── Dockerfile         # Docker configuration
└── docker-compose.yml # Multi-service Docker setup
```

## Management Commands

- **Start**: `./scripts/start.sh`
- **Stop**: `./scripts/stop.sh`
- **Update**: `./scripts/update.sh` (pulls from Git and restarts)
- **Status**: `sudo systemctl status document-processor.service`
- **Logs**: `sudo journalctl -u document-processor.service -f`

## Configuration

The system supports configurable column mappings for different document formats. Default columns include:

- council
- reference
- hmo_address
- licence_start
- licence_expiry
- max_occupancy
- hmo_manager_name
- hmo_manager_address
- licence_holder_name
- licence_holder_address
- number_of_households
- number_of_shared_kitchens
- number_of_shared_bathrooms
- number_of_shared_toilets
- number_of_storeys

## Technology Stack

- **Frontend**: Streamlit
- **Backend**: FastAPI
- **Document Processing**: PyPDF2, python-docx, Tesseract OCR
- **NLP/ML**: spaCy, scikit-learn
- **Database**: SQLite, Redis
- **Deployment**: Docker, Ubuntu Server

## Development

### Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run tests
pytest tests/

# Run with coverage
pytest --cov=. tests/
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .
```

## Deployment Management

### Service Management

#### Native Deployment
```bash
# Start application
./scripts/start.sh --native

# Stop application
./scripts/stop.sh --native

# Update from Git
./scripts/update.sh --native

# Check service status
sudo systemctl status document-processor.service

# View logs
sudo journalctl -u document-processor.service -f
```

#### Docker Deployment
```bash
# Start services
./scripts/start.sh --docker
# or directly: docker-compose up -d

# Stop services
./scripts/stop.sh --docker
# or directly: docker-compose down

# Update application
./scripts/update.sh --docker

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### Configuration Management

The application uses environment variables for configuration. Key settings:

```bash
# .env file configuration
APP_NAME=HMO Document Processor
DEBUG=false
LOG_LEVEL=INFO

# Server settings
STREAMLIT_PORT=8501
FASTAPI_PORT=8000
HOST=0.0.0.0

# File processing
MAX_FILE_SIZE=104857600  # 100MB
SESSION_TIMEOUT=3600     # 1 hour
CLEANUP_INTERVAL=86400   # 24 hours

# OCR settings
OCR_LANGUAGE=eng
CONFIDENCE_THRESHOLD=0.7

# Database
DATABASE_URL=sqlite:///processing_sessions.db
REDIS_URL=redis://localhost:6379/0
```

## Troubleshooting

### Installation Issues

#### 1. Docker Installation Problems
```bash
# Check Docker installation
docker --version
docker-compose --version

# Test Docker without sudo
docker run hello-world

# If permission denied, add user to docker group
sudo usermod -aG docker $USER
# Then log out and back in
```

#### 2. Python Dependencies Issues
```bash
# Update pip and setuptools
pip install --upgrade pip setuptools wheel

# Install with verbose output to see errors
pip install -v -r requirements.txt

# For Ubuntu 18.04, you might need:
sudo apt-get install python3.8-dev
```

#### 3. Tesseract OCR Issues
```bash
# Install additional language packs
sudo apt-get install tesseract-ocr-all

# Check Tesseract installation
tesseract --version
tesseract --list-langs

# Test OCR functionality
echo "test" | tesseract stdin stdout
```

### Runtime Issues

#### 1. Application Won't Start
```bash
# Check port availability
sudo netstat -tlnp | grep :8501

# Kill process using port 8501
sudo fuser -k 8501/tcp

# Check system resources
free -h
df -h
```

#### 2. Redis Connection Errors
```bash
# Check Redis status
sudo systemctl status redis-server

# Start Redis if stopped
sudo systemctl start redis-server

# Test Redis connection
redis-cli ping

# Check Redis logs
sudo journalctl -u redis-server -f
```

#### 3. File Processing Errors
```bash
# Check file permissions
ls -la uploads/ downloads/ temp/

# Fix permissions if needed
chmod 755 uploads downloads temp logs
chown -R $USER:$USER uploads downloads temp logs

# Check disk space
df -h

# Monitor processing logs
tail -f logs/app.log
```

#### 4. Memory Issues
```bash
# Check memory usage
free -h
top -p $(pgrep -f streamlit)

# For large files, increase swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Performance Issues

#### 1. Slow Processing
- **Large files**: Enable chunked processing in configuration
- **Low memory**: Increase system RAM or swap space
- **CPU bottleneck**: Reduce worker concurrency in `.env`

#### 2. High Memory Usage
```bash
# Monitor memory usage
watch -n 1 'free -h && ps aux --sort=-%mem | head -10'

# Restart services to clear memory
./scripts/stop.sh && ./scripts/start.sh
```

### Network Issues

#### 1. Cannot Access Web Interface
```bash
# Check if service is listening
sudo netstat -tlnp | grep :8501

# Check firewall settings
sudo ufw status
sudo ufw allow 8501

# For remote access, bind to all interfaces
# Edit .env: HOST=0.0.0.0
```

#### 2. Docker Network Issues
```bash
# Check Docker networks
docker network ls

# Restart Docker daemon
sudo systemctl restart docker

# Recreate Docker network
docker-compose down
docker network prune
docker-compose up -d
```

### Log Analysis

#### Application Logs
```bash
# Native deployment
sudo journalctl -u document-processor.service -f --since "1 hour ago"

# Docker deployment
docker-compose logs -f --tail=100 app

# Specific service logs
docker-compose logs -f redis
docker-compose logs -f worker
```

#### System Logs
```bash
# System messages
sudo tail -f /var/log/syslog

# Docker daemon logs
sudo journalctl -u docker.service -f

# Kernel messages
dmesg | tail -20
```

### Data Recovery

#### 1. Backup and Restore
```bash
# Create backup
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz \
    uploads/ downloads/ logs/ *.db .env

# Restore from backup
tar -xzf backup_YYYYMMDD_HHMMSS.tar.gz
```

#### 2. Database Issues
```bash
# Check database integrity
sqlite3 processing_sessions.db "PRAGMA integrity_check;"

# Backup database
cp processing_sessions.db processing_sessions.db.backup

# Reset database (will lose data)
rm processing_sessions.db audit_data.db
# Restart application to recreate
```

### Getting Help

If you encounter issues not covered here:

1. **Check logs** for specific error messages
2. **Search existing issues** in the repository
3. **Create a new issue** with:
   - Operating system and version
   - Python version (`python3 --version`)
   - Docker version (if using Docker)
   - Complete error message
   - Steps to reproduce the problem
   - Relevant log excerpts

#### Useful Diagnostic Commands
```bash
# System information
uname -a
lsb_release -a
python3 --version
docker --version
free -h
df -h

# Service status
sudo systemctl status document-processor.service
docker-compose ps

# Network status
sudo netstat -tlnp | grep -E ':(8501|6379|8000)'
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is open source and available under the [MIT License](LICENSE).

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the logs for error messages
3. Create an issue in the repository with detailed information about the problem