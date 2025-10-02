# 🏠 HMO Document Processing Pipeline

> **Automated conversion of PDF/DOCX files containing HMO licensing data into standardized CSV format**

[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-green?logo=python)](https://www.python.org/)
[![Ubuntu](https://img.shields.io/badge/Ubuntu-22.04-orange?logo=ubuntu)](https://ubuntu.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🚀 Quick Start for Ubuntu Server

### Prerequisites
- Ubuntu 18.04+ (Recommended: Ubuntu 22.04 LTS)
- Internet connection for initial setup
- Sudo privileges

### 🎯 Recommended: Automatic Deployment

```bash
# Clone repository and deploy automatically
git clone https://github.com/YOUR_USERNAME/hmo-document-processor.git
cd hmo-document-processor
chmod +x scripts/start.sh && ./scripts/start.sh
```

**What this does:**
- ✅ Auto-detects Docker or native Python deployment
- ✅ Installs dependencies automatically
- ✅ Configures services and databases
- ✅ Starts the application with proper settings
- ✅ Shows management commands and access URLs

### 🐳 Docker Deployment (Recommended for Production)

```bash
# Clone and start with Docker
git clone https://github.com/YOUR_USERNAME/hmo-document-processor.git
cd hmo-document-processor
chmod +x scripts/start.sh && ./scripts/start.sh --docker
```

### 💻 Native Python Deployment (Recommended for Development)

```bash
# Clone and start with native Python
git clone https://github.com/YOUR_USERNAME/hmo-document-processor.git
cd hmo-document-processor
chmod +x scripts/start.sh && ./scripts/start.sh --native
```

### 🔧 Manual Setup (If Automatic Fails)

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/hmo-document-processor.git
cd hmo-document-processor

# 2. Install system dependencies
sudo apt-get update && sudo apt-get install -y \
    python3 python3-pip python3-venv \
    tesseract-ocr tesseract-ocr-eng \
    redis-server git curl wget

# 3. Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# 4. Initialize and start
python fix_setup.py
python start_app.py
```

### 📱 Access Application
- **Local**: http://localhost:8501
- **Remote**: http://YOUR_SERVER_IP:8501
- **SSH Tunnel**: `ssh -L 8501:localhost:8501 user@server_ip`

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

## 🛠️ Deployment Options for Ubuntu Server

### Option 1: Smart Auto-Deployment (Recommended)

**The `scripts/start.sh` automatically detects your environment and chooses the best deployment method:**

```bash
# Clone and auto-deploy
git clone https://github.com/YOUR_USERNAME/hmo-document-processor.git
cd hmo-document-processor
chmod +x scripts/start.sh && ./scripts/start.sh
```

**Auto-detection logic:**
- 🐳 **Docker available + docker-compose.yml exists** → Docker deployment
- 💻 **No Docker or no docker-compose.yml** → Native Python deployment
- 🔧 **Manual override** → Use `--docker` or `--native` flags

### Option 2: Docker Deployment (Production Ready)

```bash
# Force Docker deployment
git clone https://github.com/YOUR_USERNAME/hmo-document-processor.git
cd hmo-document-processor
chmod +x scripts/start.sh && ./scripts/start.sh --docker
```

**Docker deployment includes:**
- ✅ Redis server for queue management
- ✅ Main application container
- ✅ Worker processes for background tasks
- ✅ Persistent data volumes
- ✅ Network isolation and security

### Option 3: Native Python Deployment (Development/Testing)

```bash
# Force native Python deployment
git clone https://github.com/YOUR_USERNAME/hmo-document-processor.git
cd hmo-document-processor
chmod +x scripts/start.sh && ./scripts/start.sh --native
```

**Native deployment includes:**
- ✅ System Redis server
- ✅ Python virtual environment
- ✅ Systemd service integration
- ✅ Direct system access for debugging

### Option 4: Manual Setup (Troubleshooting)

<details>
<summary>Click to expand manual installation steps</summary>

```bash
# 1. Install system dependencies
sudo apt-get update && sudo apt-get install -y \
    python3 python3-pip python3-venv python3-dev \
    tesseract-ocr tesseract-ocr-eng \
    redis-server git curl wget build-essential \
    sqlite3 libsqlite3-dev

# 2. Clone repository
git clone https://github.com/YOUR_USERNAME/hmo-document-processor.git
cd hmo-document-processor

# 3. Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# 4. Initialize system
python fix_setup.py

# 5. Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# 6. Start application
python start_app.py
```

</details>

### Option 5: Development Environment

```bash
# Development setup with hot reload
git clone https://github.com/YOUR_USERNAME/hmo-document-processor.git
cd hmo-document-processor

# Install development tools
sudo apt-get install -y python3-dev python3-setuptools
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run in development mode
export DEBUG=true
streamlit run app.py --server.port=8501 --server.address=0.0.0.0
```

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

## 🔧 Management Commands for Ubuntu Server

### Using the Start Script

```bash
# Start application (auto-detects deployment method)
./scripts/start.sh

# Force Docker deployment
./scripts/start.sh --docker

# Force native Python deployment  
./scripts/start.sh --native

# Check what deployment method will be used
./scripts/start.sh --help
```

### Docker Deployment Management

```bash
# View service status
docker-compose ps

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Update and restart
git pull && docker-compose up -d --build

# Scale workers (if needed)
docker-compose up -d --scale worker=3
```

### Native Deployment Management

```bash
# Check service status
sudo systemctl status document-processor

# Start/stop/restart service
sudo systemctl start document-processor
sudo systemctl stop document-processor
sudo systemctl restart document-processor

# Enable/disable auto-start on boot
sudo systemctl enable document-processor
sudo systemctl disable document-processor

# View live logs
sudo journalctl -u document-processor -f

# View recent logs
sudo journalctl -u document-processor --since "1 hour ago"
```

### Application Updates

```bash
# Update from GitHub (works for both deployment methods)
cd /path/to/hmo-document-processor
git pull

# For Docker deployment
docker-compose down && docker-compose up -d --build

# For native deployment
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart document-processor
```

### Health Checks and Monitoring

```bash
# Check application health
curl -f http://localhost:8501/_stcore/health

# Check Redis (Docker)
docker-compose exec redis redis-cli ping

# Check Redis (Native)
redis-cli ping

# System resource monitoring
htop                           # Interactive process viewer
free -h                        # Memory usage
df -h                          # Disk usage
netstat -tlnp | grep 8501     # Check port usage

# Application-specific monitoring
python test_simple.py         # Run system test
tail -f logs/app.log          # Application logs (if configured)
```

### Troubleshooting Commands

```bash
# Check what's running on port 8501
sudo lsof -i :8501

# Kill processes on port 8501 (if needed)
sudo fuser -k 8501/tcp

# Check Docker status (if using Docker)
docker system df              # Docker disk usage
docker system prune           # Clean up unused Docker resources

# Check system logs
sudo journalctl --since "1 hour ago" | grep -i error

# Network connectivity test
curl -I http://localhost:8501
telnet localhost 8501
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

## 🔍 Troubleshooting for Ubuntu Server

### Common Issues & Solutions

#### ❌ "Processing Error - Unknown Error"

**Cause:** System components initialization failure

**Solutions:**
```bash
# 1. Pull latest fixes
git pull origin main

# 2. Restart application
./scripts/start.sh

# 3. If using Docker
docker-compose down && docker-compose up -d --build

# 4. If using native deployment
sudo systemctl restart document-processor
```

#### ❌ "Redis Connection Failed"

**For Docker Deployment:**
```bash
# Check Redis container
docker-compose ps
docker-compose logs redis

# Restart Redis
docker-compose restart redis
```

**For Native Deployment:**
```bash
# Check Redis service
sudo systemctl status redis-server

# Start Redis if stopped
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test Redis connection
redis-cli ping
```

#### ❌ "Port 8501 Already in Use"

**Solution:**
```bash
# Find what's using the port
sudo lsof -i :8501

# Kill the process (replace PID with actual process ID)
sudo kill -9 PID

# Or kill all processes on port 8501
sudo fuser -k 8501/tcp

# Restart application
./scripts/start.sh
```

#### ❌ "Permission Denied" Errors

**Solution:**
```bash
# Fix file permissions
sudo chown -R $USER:$USER .
chmod +x scripts/start.sh

# Fix directory permissions
chmod 755 uploads downloads temp logs cache data sample_outputs

# For Docker group access (if using Docker)
sudo usermod -aG docker $USER
# Then logout and login again
```

#### ❌ "Python Module Not Found"

**Solution:**
```bash
# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Test installation
python test_simple.py
```

#### ❌ "Streamlit Won't Start"

**Solution:**
```bash
# Check if Streamlit is installed
source venv/bin/activate
streamlit --version

# Reinstall Streamlit
pip install --upgrade streamlit

# Start manually for debugging
streamlit run app.py --server.port=8501 --server.address=0.0.0.0
```

### Ubuntu-Specific Diagnostics

```bash
# Check Ubuntu version and compatibility
lsb_release -a

# Check system resources
free -h                    # Memory usage
df -h                      # Disk usage
htop                       # Process monitor
iostat 1 5                 # I/O statistics

# Check network configuration
ip addr show               # Network interfaces
ss -tulpn | grep 8501     # Port usage
sudo ufw status           # Firewall status

# Check system services
systemctl --failed        # Failed services
journalctl --since "1 hour ago" | grep -i error  # System errors
```

### Application-Specific Diagnostics

```bash
# Test system components
python test_simple.py

# Check application health
curl -f http://localhost:8501/_stcore/health

# Verify file permissions
ls -la uploads/ downloads/ temp/ logs/

# Check Python environment
source venv/bin/activate
python --version
pip list | grep -E "(streamlit|pandas|spacy)"

# Test database connectivity
python -c "
import sqlite3
conn = sqlite3.connect('processing_sessions.db')
print('Database connection: OK')
conn.close()
"
```

### Performance Optimization for Ubuntu

| Issue | Ubuntu Solution |
|-------|----------------|
| **Slow processing** | `sudo sysctl vm.swappiness=10` (reduce swap usage) |
| **High memory usage** | `sudo systemctl restart document-processor` |
| **Disk I/O bottleneck** | Move to SSD, or `sudo ionice -c 1 -n 4 python app.py` |
| **Network timeouts** | `sudo ufw allow 8501/tcp` |
| **Too many open files** | `ulimit -n 4096` |

### Log Analysis

```bash
# Application logs (Docker)
docker-compose logs -f --tail=100

# Application logs (Native)
sudo journalctl -u document-processor -f

# System logs
sudo journalctl --since "1 hour ago" | grep -E "(error|fail|exception)"

# Streamlit logs
tail -f ~/.streamlit/logs/streamlit.log

# Custom application logs (if configured)
tail -f logs/app.log
```

### Emergency Recovery

```bash
# Complete reset (Docker)
docker-compose down -v
docker system prune -a
git pull origin main
./scripts/start.sh --docker

# Complete reset (Native)
sudo systemctl stop document-processor
rm -rf venv/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python fix_setup.py
./scripts/start.sh --native

# Database reset (if needed)
rm -f processing_sessions.db audit_data.db
python fix_setup.py
```

### Getting Help

1. **Check logs first**: `sudo journalctl -u document-processor -f`
2. **Run system test**: `python test_simple.py`
3. **Check GitHub Issues**: Search for similar problems
4. **Create detailed issue** with:
   - Ubuntu version: `lsb_release -a`
   - Error messages from logs
   - Steps to reproduce
   - System resources: `free -h && df -h`

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

## 👥 Team Collaboration & GitHub Workflow

### For Team Members (Pulling and Deploying)

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/hmo-document-processor.git
cd hmo-document-processor

# 2. Deploy automatically (recommended)
chmod +x scripts/start.sh && ./scripts/start.sh

# 3. Access the application
# Local: http://localhost:8501
# Remote: http://YOUR_SERVER_IP:8501
```

### Development Workflow

```bash
# 1. Pull latest changes
git pull origin main

# 2. Create feature branch
git checkout -b feature/your-feature-name

# 3. Make changes and test
source venv/bin/activate  # If using native deployment
python test_simple.py     # Run tests

# 4. Commit and push
git add .
git commit -m "Add: your feature description"
git push origin feature/your-feature-name

# 5. Create Pull Request on GitHub
```

### Production Deployment Workflow

```bash
# 1. SSH to Ubuntu server
ssh user@your-server-ip

# 2. Navigate to application directory (or clone if first time)
cd hmo-document-processor || git clone https://github.com/YOUR_USERNAME/hmo-document-processor.git && cd hmo-document-processor

# 3. Pull latest changes
git pull origin main

# 4. Deploy/restart application
./scripts/start.sh

# 5. Verify deployment
curl -f http://localhost:8501/_stcore/health
```

### Environment-Specific Configurations

Create environment-specific configuration files:

```bash
# Development environment
cp .env.example .env.development

# Production environment  
cp .env.example .env.production

# Staging environment
cp .env.example .env.staging
```

### 🤝 Contributing Guidelines

1. **Fork** the repository on GitHub
2. **Clone** your fork: `git clone https://github.com/YOUR_USERNAME/hmo-document-processor.git`
3. **Create** feature branch: `git checkout -b feature/amazing-feature`
4. **Setup** development environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```
5. **Make** your changes and test thoroughly
6. **Run** tests: `python test_simple.py`
7. **Commit** changes: `git commit -m 'Add: amazing feature'`
8. **Push** to branch: `git push origin feature/amazing-feature`
9. **Open** Pull Request with detailed description

### Code Quality Standards

```bash
# Run linting (if configured)
flake8 .

# Run type checking (if configured)
mypy .

# Run security checks (if configured)
bandit -r .

# Run all tests
python -m pytest tests/ -v
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

## 📚 Quick Reference

### Essential Commands

```bash
# 🚀 Deploy application
git clone https://github.com/YOUR_USERNAME/hmo-document-processor.git
cd hmo-document-processor
chmod +x scripts/start.sh && ./scripts/start.sh

# 🔄 Update application
git pull origin main && ./scripts/start.sh

# 🔍 Check status
curl -f http://localhost:8501/_stcore/health

# 📊 View logs
sudo journalctl -u document-processor -f  # Native
docker-compose logs -f                    # Docker

# 🛑 Stop application
sudo systemctl stop document-processor    # Native
docker-compose down                       # Docker

# 🧪 Test system
python test_simple.py
```

### File Structure

```
hmo-document-processor/
├── app.py                 # Main Streamlit application
├── scripts/start.sh       # Smart deployment script
├── fix_setup.py          # System initialization
├── test_simple.py        # System testing
├── requirements.txt      # Python dependencies
├── docker-compose.yml    # Docker configuration
├── services/             # Core processing services
├── models/               # Data models
├── web/                  # Web interface components
├── temp/                 # Temporary files
├── sample_outputs/       # Generated CSV files
└── logs/                 # Application logs
```

### Environment Variables

```bash
# Application settings
export DEBUG=false
export LOG_LEVEL=INFO
export MAX_FILE_SIZE=104857600

# Server settings
export STREAMLIT_PORT=8501
export HOST=0.0.0.0

# Database settings
export DATABASE_URL=sqlite:///processing_sessions.db
export AUDIT_DATABASE_URL=sqlite:///audit_data.db
```

### Useful URLs

- **Application**: http://localhost:8501
- **Health Check**: http://localhost:8501/_stcore/health
- **GitHub Repository**: https://github.com/YOUR_USERNAME/hmo-document-processor
- **Issues**: https://github.com/YOUR_USERNAME/hmo-document-processor/issues

---

## 📞 Support & Contact

### Getting Support

1. **📖 Documentation**: Check this README and troubleshooting section
2. **🔍 Search Issues**: Look for existing solutions in [GitHub Issues](../../issues)
3. **💬 Create Issue**: Report bugs or request features with detailed information
4. **📧 Contact Team**: For urgent production issues

### Issue Reporting Template

```markdown
**Environment:**
- OS: Ubuntu 22.04
- Deployment: Docker/Native
- Python: 3.x.x
- Browser: Chrome/Firefox

**Error Description:**
[Clear description of the issue]

**Steps to Reproduce:**
1. Step one
2. Step two
3. Error occurs

**Expected vs Actual Behavior:**
Expected: [What should happen]
Actual: [What actually happens]

**Logs:**
```
[Paste relevant logs here]
```

**Additional Context:**
[Any other relevant information]
```

---

**⭐ Star this repository if it helped you!**

**🔗 Share with colleagues who need automated HMO document processing**

**🤝 Contribute to make it even better for the community**