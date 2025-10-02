# 🏠 HMO Document Processing Pipeline

> **Automated conversion of PDF/DOCX files containing HMO licensing data into standardized CSV format**

[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-green?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🚀 Quick Start (1-Minute Setup)

### For Ubuntu Server (Recommended)

```bash
# 1. Clone and enter directory
git clone <your-repository-url>
cd hmo-document-processor

# 2. One-command deployment
chmod +x start-docker.sh && ./start-docker.sh

# 3. Access application
# Local: http://localhost:8501
# Remote: http://YOUR_SERVER_IP:8501
```

**That's it!** The script automatically installs Docker, builds containers, and starts all services.

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📄 **Multi-Format** | PDF & DOCX support with intelligent detection |
| 🤖 **AI-Powered** | OCR + NLP + ML for accurate extraction |
| 🌐 **Web Interface** | Drag-and-drop Streamlit interface |
| ✅ **Quality Control** | Confidence scoring + manual review |
| 🔧 **Configurable** | Custom column mappings & validation |
| 🐳 **Docker Ready** | One-command deployment |
| 🔄 **Queue System** | Redis-based concurrent processing |
| 📊 **Audit Tools** | Manual review for flagged records |

## 📋 System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **OS** | Ubuntu 18.04+ | Ubuntu 22.04 LTS |
| **CPU** | 2 cores, 2.4 GHz | 4+ cores, 3.0+ GHz |
| **RAM** | 4 GB | 8+ GB |
| **Storage** | 10 GB | 50+ GB SSD |
| **Network** | Internet for setup | Stable connection |

## 🛠️ Installation Options

### Option 1: Automated Docker Deployment (Recommended)

**Perfect for production servers and quick setup:**

```bash
# Clone repository
git clone <your-repository-url>
cd hmo-document-processor

# Make script executable and run
chmod +x start-docker.sh
./start-docker.sh

# Optional: Rebuild with latest changes
./start-docker.sh --rebuild
```

**What this does:**
- ✅ Checks/installs Docker & Docker Compose
- ✅ Creates necessary directories
- ✅ Builds and starts all services (Redis, App, Worker)
- ✅ Shows service status and logs
- ✅ Provides management commands

### Option 2: Manual Docker Setup

```bash
# Install Docker (if needed)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose (if needed)
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Deploy application
git clone <your-repository-url>
cd hmo-document-processor
docker-compose up -d --build

# Check status
docker-compose ps
docker-compose logs
```

### Option 3: Development Setup

<details>
<summary>Click to expand development installation</summary>

```bash
# Install system dependencies
sudo apt-get update && sudo apt-get install -y \
    python3 python3-pip python3-venv tesseract-ocr \
    tesseract-ocr-eng redis-server git curl

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Start Redis
sudo systemctl start redis-server

# Run application
streamlit run app.py --server.port=8501 --server.address=0.0.0.0
```

</details>

## 🎯 Usage Guide

### Basic Workflow

1. **📤 Upload**: Drag & drop PDF/DOCX files
2. **⚙️ Configure**: Set processing options (OCR, confidence threshold)
3. **🚀 Process**: Click "Start Processing"
4. **👀 Review**: Check flagged records in audit interface
5. **📥 Download**: Get standardized CSV output

### Supported Data Fields

| Field | Description | Example |
|-------|-------------|---------|
| `council` | Local authority name | "Birmingham City Council" |
| `reference` | HMO license reference | "HMO/2024/001234" |
| `hmo_address` | Property address | "123 Main St, City, AB1 2CD" |
| `licence_start` | License start date | "2024-01-01" |
| `licence_expiry` | License expiry date | "2025-01-01" |
| `max_occupancy` | Maximum occupants | "5" |
| `hmo_manager_name` | Manager name | "John Smith" |
| `licence_holder_name` | License holder | "Property Ltd" |

## 🔧 Management Commands

### Docker Deployment

```bash
# Start services
docker-compose up -d

# Stop services  
docker-compose down

# View logs
docker-compose logs -f

# Restart specific service
docker-compose restart app

# Update application
git pull && docker-compose up -d --build

# Complete cleanup (removes all data)
docker-compose down -v && docker system prune -a
```

### Service Status

```bash
# Check all services
docker-compose ps

# Check specific service health
docker-compose exec redis redis-cli ping
curl -f http://localhost:8501/_stcore/health

# View resource usage
docker stats
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Interface │    │   Main App      │    │   Worker        │
│   (Streamlit)   │◄──►│   (Python)      │◄──►│   (Background)  │
│   Port: 8501    │    │   Port: 8000    │    │   Processing    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │     Redis       │
                    │   (Queue/Cache) │
                    │   Port: 6379    │
                    └─────────────────┘
```

### Technology Stack

- **Frontend**: Streamlit (Web UI)
- **Backend**: Python, FastAPI
- **Processing**: PyPDF2, python-docx, Tesseract OCR
- **AI/ML**: spaCy, scikit-learn
- **Database**: SQLite, Redis
- **Deployment**: Docker, Docker Compose

## ⚙️ Configuration

### Environment Variables

Key settings in `.env` file:

```bash
# Application
APP_NAME=HMO Document Processor
LOG_LEVEL=INFO
DEBUG=false

# Server
STREAMLIT_PORT=8501
FASTAPI_PORT=8000
HOST=0.0.0.0

# Processing
MAX_FILE_SIZE=104857600  # 100MB
SESSION_TIMEOUT=3600     # 1 hour
CONFIDENCE_THRESHOLD=0.7

# Services
REDIS_URL=redis://redis:6379/0
DATABASE_URL=sqlite:////app/data/processing_sessions.db
AUDIT_DATABASE_URL=sqlite:////app/data/audit_data.db

# OCR
OCR_LANGUAGE=eng
TESSERACT_CMD=tesseract
```

### Custom Column Mapping

Edit `config/column_mappings.json` to customize field extraction:

```json
{
  "council": ["council", "local authority", "authority"],
  "reference": ["reference", "ref", "license number", "licence number"],
  "hmo_address": ["address", "property address", "hmo address"],
  "licence_start": ["start date", "issue date", "from"],
  "licence_expiry": ["expiry date", "end date", "until", "expires"]
}
```

## 🔍 Troubleshooting

### Common Issues & Quick Fixes

#### ❌ "ProcessingPipeline object has no attribute '_register_services'"

**Solution:**
```bash
# Pull latest fixes and rebuild
git pull
docker-compose down
docker-compose up -d --build
```

#### ❌ "Error 111 connecting to localhost:6379. Connection refused"

**Solution:**
```bash
# Check Redis container
docker-compose ps
docker-compose logs redis

# Restart Redis if needed
docker-compose restart redis
```

#### ❌ "Application won't start"

**Solution:**
```bash
# Check port availability
sudo netstat -tlnp | grep :8501

# Kill conflicting process
sudo fuser -k 8501/tcp

# Restart application
docker-compose restart app
```

#### ❌ "Permission denied" errors

**Solution:**
```bash
# Fix directory permissions
sudo chown -R $USER:$USER .
chmod 755 uploads downloads temp logs cache data

# For Docker group access
sudo usermod -aG docker $USER
# Then logout and login again
```

### Diagnostic Commands

```bash
# Check all services
docker-compose ps

# View recent logs
docker-compose logs --tail=50

# Check system resources
free -h && df -h

# Test Redis connection
docker-compose exec redis redis-cli ping

# Test web interface
curl -f http://localhost:8501/_stcore/health
```

### Performance Optimization

| Issue | Solution |
|-------|----------|
| **Slow processing** | Increase RAM, reduce file size, enable chunked processing |
| **High memory usage** | Restart services: `docker-compose restart` |
| **Network timeouts** | Check firewall: `sudo ufw allow 8501` |
| **Disk space** | Clean up: `docker system prune -a` |

### Log Locations

```bash
# Application logs
docker-compose logs app

# Redis logs  
docker-compose logs redis

# Worker logs
docker-compose logs worker

# System logs
sudo journalctl -u docker.service -f
```

## 🚀 Automated Deployment Scripts

### Quick Deployment Commands

```bash
# One-command setup (recommended)
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/hmo-document-processor/main/install.sh | bash

# Or manual clone and run
git clone https://github.com/YOUR_USERNAME/hmo-document-processor.git
cd hmo-document-processor
chmod +x start-docker.sh && ./start-docker.sh
```

### Management Scripts

| Command | Description |
|---------|-------------|
| `./start-docker.sh` | Deploy application with Docker |
| `./start-docker.sh --rebuild` | Rebuild and deploy |
| `docker-compose down` | Stop all services |
| `docker-compose logs -f` | View live logs |
| `docker-compose ps` | Check service status |

### Update Workflow

```bash
# Update to latest version
git pull
docker-compose down
docker-compose up -d --build

# Or use the automated script
./start-docker.sh --rebuild
```

## 📊 Monitoring & Maintenance

### Health Checks

```bash
# Check all services
curl -f http://localhost:8501/_stcore/health
docker-compose exec redis redis-cli ping

# View service status
docker-compose ps
docker stats --no-stream
```

### Backup & Recovery

```bash
# Create backup
docker-compose exec app tar -czf /tmp/backup.tar.gz /app/data
docker cp $(docker-compose ps -q app):/tmp/backup.tar.gz ./backup_$(date +%Y%m%d).tar.gz

# Restore backup
docker cp backup_YYYYMMDD.tar.gz $(docker-compose ps -q app):/tmp/
docker-compose exec app tar -xzf /tmp/backup_YYYYMMDD.tar.gz -C /
```

## 🤝 Contributing

1. **Fork** the repository
2. **Create** feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** changes: `git commit -m 'Add amazing feature'`
4. **Push** to branch: `git push origin feature/amazing-feature`
5. **Open** Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/hmo-document-processor.git
cd hmo-document-processor

# Create development environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest tests/

# Start development server
streamlit run app.py
```

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Getting Help

1. **📖 Check Documentation**: Review this README and troubleshooting section
2. **🔍 Search Issues**: Look for existing solutions in [Issues](../../issues)
3. **💬 Create Issue**: Report bugs or request features
4. **📧 Contact**: For urgent issues, contact the maintainers

### Issue Template

When reporting issues, include:

```
**Environment:**
- OS: Ubuntu 22.04
- Docker: 24.0.0
- Browser: Chrome 120.0

**Error Message:**
[Paste complete error message]

**Steps to Reproduce:**
1. Step one
2. Step two
3. Error occurs

**Expected Behavior:**
[What should happen]

**Logs:**
[Paste relevant logs from docker-compose logs]
```

---

**⭐ Star this repository if it helped you!**

**🔗 Share with others who might benefit from automated HMO document processing**