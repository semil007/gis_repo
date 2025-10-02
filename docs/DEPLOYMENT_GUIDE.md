# HMO Document Processing Pipeline - Deployment Guide

## Table of Contents
1. [Overview](#overview)
2. [Pre-deployment Planning](#pre-deployment-planning)
3. [Server Preparation](#server-preparation)
4. [Installation Methods](#installation-methods)
5. [Configuration](#configuration)
6. [Security Setup](#security-setup)
7. [Monitoring and Maintenance](#monitoring-and-maintenance)
8. [Backup and Recovery](#backup-and-recovery)
9. [Scaling and Performance](#scaling-and-performance)
10. [Troubleshooting](#troubleshooting)

## Overview

This guide covers deploying the HMO Document Processing Pipeline on Ubuntu servers for production use. The system supports both native Python deployment and containerized Docker deployment.

### Deployment Architecture

```
┌─────────────────────────────────────────────────┐
│                Load Balancer                    │
│              (nginx/Apache)                     │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│            Application Server                   │
│  ┌─────────────┐  ┌─────────────┐              │
│  │  Streamlit  │  │   Worker    │              │
│  │   (8501)    │  │  Processes  │              │
│  └─────────────┘  └─────────────┘              │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│              Data Layer                         │
│  ┌─────────────┐  ┌─────────────┐              │
│  │    Redis    │  │   SQLite    │              │
│  │   (Queue)   │  │ (Sessions)  │              │
│  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────┘
```

## Pre-deployment Planning

### Hardware Requirements

#### Minimum Configuration
- **CPU**: 2 cores, 2.4 GHz
- **RAM**: 4 GB
- **Storage**: 20 GB SSD
- **Network**: 100 Mbps

#### Recommended Configuration
- **CPU**: 4+ cores, 3.0+ GHz
- **RAM**: 8+ GB
- **Storage**: 50+ GB SSD
- **Network**: 1 Gbps

#### High-Load Configuration
- **CPU**: 8+ cores, 3.5+ GHz
- **RAM**: 16+ GB
- **Storage**: 100+ GB NVMe SSD
- **Network**: 10 Gbps

### Software Requirements

#### Operating System
- **Primary**: Ubuntu 22.04 LTS (recommended)
- **Supported**: Ubuntu 20.04 LTS, Ubuntu 18.04 LTS
- **Architecture**: x86_64 (AMD64)

#### Dependencies
- Python 3.8+ (3.9+ recommended)
- Docker 20.10+ (for containerized deployment)
- Redis 6.0+
- Git 2.25+

### Network Requirements

#### Ports
- **8501**: Streamlit web interface
- **8000**: FastAPI endpoints (optional)
- **6379**: Redis (internal)
- **22**: SSH (administration)
- **80/443**: HTTP/HTTPS (with reverse proxy)

#### Firewall Configuration
```bash
# Allow SSH
sudo ufw allow 22

# Allow web traffic
sudo ufw allow 8501
sudo ufw allow 80
sudo ufw allow 443

# Enable firewall
sudo ufw enable
```

## Server Preparation

### Initial Server Setup

#### 1. Update System
```bash
sudo apt update
sudo apt upgrade -y
sudo apt autoremove -y
```

#### 2. Create Application User
```bash
# Create dedicated user for the application
sudo adduser --system --group --home /opt/hmo-processor hmoapp

# Add to necessary groups
sudo usermod -aG docker hmoapp
sudo usermod -aG redis hmoapp
```

#### 3. Configure SSH (if needed)
```bash
# Generate SSH key for deployment
ssh-keygen -t rsa -b 4096 -C "deployment@hmo-processor"

# Add to authorized_keys for automated deployment
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
```

#### 4. Install Basic Tools
```bash
sudo apt install -y curl wget git htop tree unzip \
    software-properties-common apt-transport-https \
    ca-certificates gnupg lsb-release
```

### Security Hardening

#### 1. Configure Fail2Ban
```bash
sudo apt install fail2ban

# Create custom configuration
sudo tee /etc/fail2ban/jail.local > /dev/null <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
EOF

sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

#### 2. Configure Automatic Updates
```bash
sudo apt install unattended-upgrades

# Configure automatic security updates
sudo dpkg-reconfigure -plow unattended-upgrades
```

#### 3. Set Up Log Rotation
```bash
sudo tee /etc/logrotate.d/hmo-processor > /dev/null <<EOF
/opt/hmo-processor/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 hmoapp hmoapp
    postrotate
        systemctl reload document-processor.service
    endscript
}
EOF
```

## Installation Methods

### Method 1: Automated Installation (Recommended)

#### 1. Clone Repository
```bash
cd /opt
sudo git clone https://github.com/your-org/hmo-document-processor.git hmo-processor
sudo chown -R hmoapp:hmoapp hmo-processor
cd hmo-processor
```

#### 2. Run Setup Script
```bash
sudo -u hmoapp ./scripts/setup.sh
```

#### 3. Configure Environment
```bash
sudo -u hmoapp cp .env.example .env
sudo -u hmoapp nano .env
```

### Method 2: Docker Deployment

#### 1. Install Docker
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker hmoapp

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 2. Deploy Application
```bash
cd /opt/hmo-processor
sudo -u hmoapp docker-compose up -d
```

### Method 3: Manual Installation

<details>
<summary>Click to expand manual installation steps</summary>

#### 1. Install System Dependencies
```bash
sudo apt install -y python3 python3-pip python3-venv python3-dev \
    tesseract-ocr tesseract-ocr-eng libtesseract-dev \
    poppler-utils libpoppler-cpp-dev redis-server \
    build-essential libssl-dev libffi-dev libjpeg-dev \
    libpng-dev libopencv-dev python3-opencv
```

#### 2. Set Up Python Environment
```bash
cd /opt/hmo-processor
sudo -u hmoapp python3 -m venv venv
sudo -u hmoapp ./venv/bin/pip install --upgrade pip
sudo -u hmoapp ./venv/bin/pip install -r requirements.txt
sudo -u hmoapp ./venv/bin/python -m spacy download en_core_web_sm
```

#### 3. Configure Services
```bash
# Start Redis
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Create systemd service
sudo tee /etc/systemd/system/document-processor.service > /dev/null <<EOF
[Unit]
Description=HMO Document Processing Pipeline
After=network.target redis.service

[Service]
Type=simple
User=hmoapp
Group=hmoapp
WorkingDirectory=/opt/hmo-processor
Environment=PATH=/opt/hmo-processor/venv/bin
ExecStart=/opt/hmo-processor/venv/bin/streamlit run web/streamlit_app.py --server.port=8501 --server.address=0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable document-processor.service
sudo systemctl start document-processor.service
```

</details>

## Configuration

### Environment Configuration

#### Production .env File
```bash
# Application Settings
APP_NAME=HMO Document Processor
APP_VERSION=1.0.0
DEBUG=false
LOG_LEVEL=INFO

# Server Configuration
STREAMLIT_PORT=8501
FASTAPI_PORT=8000
HOST=0.0.0.0

# Security
SECRET_KEY=your-secure-random-secret-key-here
ALLOWED_HOSTS=your-domain.com,localhost
CORS_ORIGINS=https://your-domain.com

# Database Configuration
DATABASE_URL=sqlite:///data/processing_sessions.db
AUDIT_DATABASE_URL=sqlite:///data/audit_data.db
REDIS_URL=redis://localhost:6379/0

# File Storage
UPLOAD_DIR=/opt/hmo-processor/data/uploads
DOWNLOAD_DIR=/opt/hmo-processor/data/downloads
TEMP_DIR=/opt/hmo-processor/data/temp
LOG_DIR=/opt/hmo-processor/logs

# Processing Limits
MAX_FILE_SIZE=104857600  # 100MB
SESSION_TIMEOUT=7200     # 2 hours
CLEANUP_INTERVAL=86400   # 24 hours
WORKER_CONCURRENCY=4

# OCR Configuration
TESSERACT_CMD=/usr/bin/tesseract
OCR_LANGUAGE=eng
CONFIDENCE_THRESHOLD=0.75

# Monitoring
HEALTH_CHECK_INTERVAL=30
METRICS_ENABLED=true
```

### Reverse Proxy Setup (Nginx)

#### 1. Install Nginx
```bash
sudo apt install nginx
```

#### 2. Configure Virtual Host
```bash
sudo tee /etc/nginx/sites-available/hmo-processor > /dev/null <<EOF
server {
    listen 80;
    server_name your-domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/your-domain.crt;
    ssl_certificate_key /etc/ssl/private/your-domain.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;

    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # File Upload Limits
    client_max_body_size 100M;
    client_body_timeout 300s;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Health Check Endpoint
    location /health {
        proxy_pass http://127.0.0.1:8501/_stcore/health;
        access_log off;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/hmo-processor /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL Certificate Setup

#### Using Let's Encrypt (Recommended)
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## Security Setup

### Application Security

#### 1. File Permissions
```bash
# Set proper ownership
sudo chown -R hmoapp:hmoapp /opt/hmo-processor

# Set directory permissions
sudo find /opt/hmo-processor -type d -exec chmod 755 {} \;

# Set file permissions
sudo find /opt/hmo-processor -type f -exec chmod 644 {} \;

# Make scripts executable
sudo chmod +x /opt/hmo-processor/scripts/*.sh
```

#### 2. Database Security
```bash
# Secure SQLite databases
sudo chmod 600 /opt/hmo-processor/data/*.db
sudo chown hmoapp:hmoapp /opt/hmo-processor/data/*.db
```

#### 3. Redis Security
```bash
# Configure Redis authentication
sudo tee -a /etc/redis/redis.conf > /dev/null <<EOF
# Security
requirepass your-redis-password-here
bind 127.0.0.1
protected-mode yes
EOF

sudo systemctl restart redis-server
```

### Network Security

#### 1. Firewall Rules
```bash
# Default deny
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow specific services
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'

# Rate limiting for SSH
sudo ufw limit ssh

# Enable firewall
sudo ufw enable
```

#### 2. Intrusion Detection
```bash
# Install and configure AIDE
sudo apt install aide
sudo aideinit
sudo mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db

# Schedule daily checks
echo "0 6 * * * root /usr/bin/aide --check" | sudo tee -a /etc/crontab
```

## Monitoring and Maintenance

### System Monitoring

#### 1. Install Monitoring Tools
```bash
sudo apt install htop iotop nethogs
```

#### 2. Set Up Log Monitoring
```bash
# Install logwatch
sudo apt install logwatch

# Configure daily reports
sudo tee /etc/cron.daily/logwatch > /dev/null <<EOF
#!/bin/bash
/usr/sbin/logwatch --output mail --mailto admin@your-domain.com --detail high
EOF

sudo chmod +x /etc/cron.daily/logwatch
```

#### 3. Application Health Checks
```bash
# Create health check script
sudo tee /opt/hmo-processor/scripts/health-check.sh > /dev/null <<EOF
#!/bin/bash
# Health check script for HMO Document Processor

# Check if application is responding
if curl -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
    echo "Application: OK"
else
    echo "Application: FAILED"
    exit 1
fi

# Check Redis
if redis-cli ping > /dev/null 2>&1; then
    echo "Redis: OK"
else
    echo "Redis: FAILED"
    exit 1
fi

# Check disk space
DISK_USAGE=\$(df /opt/hmo-processor | tail -1 | awk '{print \$5}' | sed 's/%//')
if [ \$DISK_USAGE -gt 90 ]; then
    echo "Disk space: WARNING (\${DISK_USAGE}% used)"
else
    echo "Disk space: OK (\${DISK_USAGE}% used)"
fi

echo "Health check completed successfully"
EOF

sudo chmod +x /opt/hmo-processor/scripts/health-check.sh

# Schedule health checks
echo "*/5 * * * * hmoapp /opt/hmo-processor/scripts/health-check.sh" | sudo tee -a /etc/crontab
```

### Performance Monitoring

#### 1. Resource Usage Monitoring
```bash
# Create monitoring script
sudo tee /opt/hmo-processor/scripts/monitor-resources.sh > /dev/null <<EOF
#!/bin/bash
# Resource monitoring script

LOG_FILE="/opt/hmo-processor/logs/resources.log"
DATE=\$(date '+%Y-%m-%d %H:%M:%S')

# CPU Usage
CPU_USAGE=\$(top -bn1 | grep "Cpu(s)" | awk '{print \$2}' | sed 's/%us,//')

# Memory Usage
MEM_USAGE=\$(free | grep Mem | awk '{printf "%.2f", \$3/\$2 * 100.0}')

# Disk Usage
DISK_USAGE=\$(df /opt/hmo-processor | tail -1 | awk '{print \$5}' | sed 's/%//')

# Application Process Count
APP_PROCESSES=\$(pgrep -f streamlit | wc -l)

echo "\$DATE,\$CPU_USAGE,\$MEM_USAGE,\$DISK_USAGE,\$APP_PROCESSES" >> \$LOG_FILE
EOF

sudo chmod +x /opt/hmo-processor/scripts/monitor-resources.sh

# Schedule resource monitoring
echo "*/1 * * * * hmoapp /opt/hmo-processor/scripts/monitor-resources.sh" | sudo tee -a /etc/crontab
```

### Maintenance Tasks

#### 1. Automated Cleanup
```bash
# Create cleanup script
sudo tee /opt/hmo-processor/scripts/cleanup.sh > /dev/null <<EOF
#!/bin/bash
# Cleanup script for temporary files and old data

# Remove temporary files older than 24 hours
find /opt/hmo-processor/data/temp -type f -mtime +1 -delete

# Remove old download files (older than 7 days)
find /opt/hmo-processor/data/downloads -type f -mtime +7 -delete

# Compress old log files
find /opt/hmo-processor/logs -name "*.log" -mtime +1 -exec gzip {} \;

# Remove compressed logs older than 30 days
find /opt/hmo-processor/logs -name "*.gz" -mtime +30 -delete

# Clean up old processing sessions (older than 30 days)
sqlite3 /opt/hmo-processor/data/processing_sessions.db "DELETE FROM processing_sessions WHERE upload_timestamp < datetime('now', '-30 days');"

echo "Cleanup completed at \$(date)"
EOF

sudo chmod +x /opt/hmo-processor/scripts/cleanup.sh

# Schedule daily cleanup
echo "0 2 * * * hmoapp /opt/hmo-processor/scripts/cleanup.sh" | sudo tee -a /etc/crontab
```

#### 2. Database Maintenance
```bash
# Create database maintenance script
sudo tee /opt/hmo-processor/scripts/db-maintenance.sh > /dev/null <<EOF
#!/bin/bash
# Database maintenance script

DB_DIR="/opt/hmo-processor/data"
BACKUP_DIR="/opt/hmo-processor/backups/db"

# Create backup directory
mkdir -p \$BACKUP_DIR

# Backup databases
cp \$DB_DIR/processing_sessions.db \$BACKUP_DIR/processing_sessions_\$(date +%Y%m%d).db
cp \$DB_DIR/audit_data.db \$BACKUP_DIR/audit_data_\$(date +%Y%m%d).db

# Vacuum databases to reclaim space
sqlite3 \$DB_DIR/processing_sessions.db "VACUUM;"
sqlite3 \$DB_DIR/audit_data.db "VACUUM;"

# Remove old backups (older than 7 days)
find \$BACKUP_DIR -name "*.db" -mtime +7 -delete

echo "Database maintenance completed at \$(date)"
EOF

sudo chmod +x /opt/hmo-processor/scripts/db-maintenance.sh

# Schedule weekly database maintenance
echo "0 3 * * 0 hmoapp /opt/hmo-processor/scripts/db-maintenance.sh" | sudo tee -a /etc/crontab
```

## Backup and Recovery

### Backup Strategy

#### 1. Full System Backup
```bash
# Create backup script
sudo tee /opt/hmo-processor/scripts/backup.sh > /dev/null <<EOF
#!/bin/bash
# Full backup script

BACKUP_DIR="/opt/backups/hmo-processor"
DATE=\$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="hmo-processor-backup-\$DATE.tar.gz"

# Create backup directory
mkdir -p \$BACKUP_DIR

# Create backup
tar -czf \$BACKUP_DIR/\$BACKUP_FILE \
    --exclude='/opt/hmo-processor/data/temp/*' \
    --exclude='/opt/hmo-processor/logs/*.log' \
    /opt/hmo-processor

# Remove old backups (keep last 7 days)
find \$BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: \$BACKUP_FILE"
EOF

sudo chmod +x /opt/hmo-processor/scripts/backup.sh

# Schedule daily backups
echo "0 1 * * * root /opt/hmo-processor/scripts/backup.sh" | sudo tee -a /etc/crontab
```

#### 2. Database Backup
```bash
# Automated database backup
echo "0 */6 * * * hmoapp /opt/hmo-processor/scripts/db-maintenance.sh" | sudo tee -a /etc/crontab
```

### Recovery Procedures

#### 1. Application Recovery
```bash
# Stop services
sudo systemctl stop document-processor.service
sudo systemctl stop nginx

# Restore from backup
cd /opt
sudo tar -xzf /opt/backups/hmo-processor/hmo-processor-backup-YYYYMMDD_HHMMSS.tar.gz

# Fix permissions
sudo chown -R hmoapp:hmoapp /opt/hmo-processor

# Start services
sudo systemctl start document-processor.service
sudo systemctl start nginx
```

#### 2. Database Recovery
```bash
# Stop application
sudo systemctl stop document-processor.service

# Restore database
sudo -u hmoapp cp /opt/hmo-processor/backups/db/processing_sessions_YYYYMMDD.db /opt/hmo-processor/data/processing_sessions.db
sudo -u hmoapp cp /opt/hmo-processor/backups/db/audit_data_YYYYMMDD.db /opt/hmo-processor/data/audit_data.db

# Start application
sudo systemctl start document-processor.service
```

## Scaling and Performance

### Horizontal Scaling

#### 1. Load Balancer Configuration
```nginx
upstream hmo_processors {
    server 192.168.1.10:8501;
    server 192.168.1.11:8501;
    server 192.168.1.12:8501;
}

server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://hmo_processors;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

#### 2. Shared Storage Setup
```bash
# Install NFS client on all nodes
sudo apt install nfs-common

# Mount shared storage
sudo mkdir -p /opt/hmo-processor/shared
sudo mount -t nfs 192.168.1.100:/shared /opt/hmo-processor/shared

# Add to fstab for persistence
echo "192.168.1.100:/shared /opt/hmo-processor/shared nfs defaults 0 0" | sudo tee -a /etc/fstab
```

### Performance Optimization

#### 1. System Tuning
```bash
# Increase file limits
sudo tee -a /etc/security/limits.conf > /dev/null <<EOF
hmoapp soft nofile 65536
hmoapp hard nofile 65536
EOF

# Optimize kernel parameters
sudo tee -a /etc/sysctl.conf > /dev/null <<EOF
# Network optimization
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216

# File system optimization
fs.file-max = 2097152
vm.swappiness = 10
EOF

sudo sysctl -p
```

#### 2. Application Tuning
```bash
# Update .env for performance
echo "WORKER_CONCURRENCY=8" >> /opt/hmo-processor/.env
echo "REDIS_MAX_CONNECTIONS=100" >> /opt/hmo-processor/.env
echo "SESSION_TIMEOUT=1800" >> /opt/hmo-processor/.env
```

## Troubleshooting

### Common Deployment Issues

#### 1. Service Won't Start
```bash
# Check service status
sudo systemctl status document-processor.service

# Check logs
sudo journalctl -u document-processor.service -f

# Check configuration
sudo -u hmoapp /opt/hmo-processor/venv/bin/python -c "import streamlit; print('OK')"
```

#### 2. Permission Issues
```bash
# Fix ownership
sudo chown -R hmoapp:hmoapp /opt/hmo-processor

# Fix permissions
sudo chmod -R 755 /opt/hmo-processor
sudo chmod 600 /opt/hmo-processor/.env
sudo chmod +x /opt/hmo-processor/scripts/*.sh
```

#### 3. Database Issues
```bash
# Check database integrity
sudo -u hmoapp sqlite3 /opt/hmo-processor/data/processing_sessions.db "PRAGMA integrity_check;"

# Reset database if corrupted
sudo systemctl stop document-processor.service
sudo -u hmoapp rm /opt/hmo-processor/data/*.db
sudo systemctl start document-processor.service
```

### Performance Issues

#### 1. High Memory Usage
```bash
# Monitor memory usage
watch -n 1 'free -h && ps aux --sort=-%mem | head -10'

# Restart services to clear memory
sudo systemctl restart document-processor.service
```

#### 2. Slow Processing
```bash
# Check CPU usage
htop

# Check I/O usage
iotop

# Optimize worker count
echo "WORKER_CONCURRENCY=2" >> /opt/hmo-processor/.env
sudo systemctl restart document-processor.service
```

### Network Issues

#### 1. Connection Timeouts
```bash
# Check network connectivity
curl -I http://localhost:8501

# Check firewall
sudo ufw status

# Check nginx configuration
sudo nginx -t
```

#### 2. SSL Issues
```bash
# Check certificate validity
openssl x509 -in /etc/ssl/certs/your-domain.crt -text -noout

# Renew Let's Encrypt certificate
sudo certbot renew --dry-run
```

---

## Support and Maintenance Contacts

- **System Administrator**: admin@your-domain.com
- **Technical Support**: support@your-domain.com
- **Emergency Contact**: +1-XXX-XXX-XXXX

**Document Version**: 1.0.0  
**Last Updated**: December 2024