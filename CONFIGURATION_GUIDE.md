# Configuration Guide - Manual Setup Required

This document lists all configuration items that need manual setup for the HMO Document Processing Pipeline.

## ✅ Required Configuration (Must Update)

### 1. Redis Configuration
**Location:** `.env` file

Based on your credentials:
```bash
REDIS_URL=redis://192.168.1.49:6379/0
REDIS_PASSWORD=redis12345
REDIS_DB=0
```

**Files that use Redis:**
- `services/queue_manager.py` - Job queue management
- `services/integration_manager.py` - Processing pipeline coordination
- Tests: `tests/test_queue_manager.py`, `tests/test_queue_storage_integration.py`

**Update Required in:**
```bash
# Edit .env file
nano .env

# Or copy from example and edit
cp .env.example .env
nano .env
```

### 2. Security Configuration
**Location:** `.env` file

```bash
# Generate a secure secret key
SECRET_KEY=your-secret-key-here  # CHANGE THIS!
```

**How to generate a secure key:**
```bash
# Option 1: Using Python
python3 -c "import secrets; print(secrets.token_hex(32))"

# Option 2: Using OpenSSL
openssl rand -hex 32
```

### 3. CUDA Configuration (Already Set)
**Location:** Environment variable

You already have:
```bash
CUDA_VISIBLE_DEVICES=-1  # Disables GPU, uses CPU only
```

This is correct if you don't have a GPU or want to use CPU only.

---

## 🔧 Optional Configuration (Review & Adjust)

### 4. File Processing Limits
**Location:** `.env` file

```bash
MAX_FILE_SIZE=104857600  # 100MB - adjust based on your needs
SESSION_TIMEOUT=3600     # 1 hour - adjust based on usage patterns
```

### 5. Worker Concurrency
**Location:** `.env` file

```bash
WORKER_CONCURRENCY=2  # Number of concurrent processing workers
                      # Adjust based on your CPU cores and RAM
```

**Recommendation:**
- 2 workers for 4 CPU cores
- 4 workers for 8+ CPU cores
- Monitor memory usage and adjust accordingly

### 6. Database Paths
**Location:** `.env` file

```bash
DATABASE_URL=sqlite:///processing_sessions.db
AUDIT_DATABASE_URL=sqlite:///audit_data.db
```

**Note:** These are relative paths. If you want absolute paths:
```bash
DATABASE_URL=sqlite:////absolute/path/to/processing_sessions.db
AUDIT_DATABASE_URL=sqlite:////absolute/path/to/audit_data.db
```

### 7. Storage Directories
**Location:** `.env` file

```bash
UPLOAD_DIR=./uploads
DOWNLOAD_DIR=./downloads
TEMP_DIR=./temp
LOG_DIR=./logs
```

**Note:** These directories will be created automatically, but ensure the application has write permissions.

---

## 🌐 Network Configuration (If Needed)

### 8. Remote Access Configuration
**Location:** `.env` file

If you need to access the application from other machines:

```bash
HOST=0.0.0.0  # Listen on all network interfaces
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.49,your-domain.com
CORS_ORIGINS=http://localhost:8501,http://192.168.1.49:8501
```

### 9. Port Configuration
**Location:** `.env` file

```bash
STREAMLIT_PORT=8501  # Web interface port
FASTAPI_PORT=8000    # API port (if using FastAPI)
```

---

## 📝 Complete .env File Template

Here's your complete `.env` file with your Redis credentials:

```bash
# HMO Document Processing Pipeline - Environment Configuration

# Application Settings
APP_NAME=HMO Document Processor
APP_VERSION=1.0.0
DEBUG=false
LOG_LEVEL=INFO

# Server Configuration
STREAMLIT_PORT=8501
FASTAPI_PORT=8000
HOST=0.0.0.0

# Redis Configuration - YOUR CREDENTIALS
REDIS_URL=redis://192.168.1.49:6379/0
REDIS_PASSWORD=redis12345
REDIS_DB=0

# Database Configuration
DATABASE_URL=sqlite:///processing_sessions.db
AUDIT_DATABASE_URL=sqlite:///audit_data.db

# File Storage Configuration
UPLOAD_DIR=./uploads
DOWNLOAD_DIR=./downloads
TEMP_DIR=./temp
LOG_DIR=./logs

# File Processing Limits
MAX_FILE_SIZE=104857600  # 100MB in bytes
SUPPORTED_FORMATS=pdf,docx
SESSION_TIMEOUT=3600     # 1 hour in seconds
CLEANUP_INTERVAL=86400   # 24 hours in seconds

# OCR Configuration
TESSERACT_CMD=tesseract
TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata
OCR_LANGUAGE=eng
OCR_CONFIG=--psm 6

# NLP Configuration
SPACY_MODEL=en_core_web_sm
CONFIDENCE_THRESHOLD=0.7
MIN_CONFIDENCE_FOR_AUTO_ACCEPT=0.85

# Processing Configuration
WORKER_CONCURRENCY=2
MAX_RETRIES=3
RETRY_DELAY=5
CHUNK_SIZE=1000

# Security Configuration - GENERATE YOUR OWN SECRET KEY!
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.49
CORS_ORIGINS=http://localhost:8501,http://127.0.0.1:8501,http://192.168.1.49:8501
SECRET_KEY=CHANGE_THIS_TO_A_SECURE_RANDOM_KEY

# Monitoring and Health Checks
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=10
HEALTH_CHECK_RETRIES=3

# Development Settings
RELOAD=false
WORKERS=1

# CUDA Configuration (Already set via environment)
# CUDA_VISIBLE_DEVICES=-1
```

---

## 🔄 Code Files That Need Redis Configuration Update

### Update `services/queue_manager.py`

The QueueManager needs to read Redis credentials from environment:

```python
# Current initialization (line ~82-90)
def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379, 
             redis_db: int = 0, queue_name: str = 'document_processing'):
```

**Needs to be updated to:**

```python
import os

def __init__(self, redis_url: str = None, queue_name: str = 'document_processing'):
    # Parse Redis URL from environment or use provided
    redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    redis_password = os.getenv('REDIS_PASSWORD', '')
    
    # Parse Redis URL
    from urllib.parse import urlparse
    parsed = urlparse(redis_url)
    
    self.redis_client = redis.Redis(
        host=parsed.hostname or 'localhost',
        port=parsed.port or 6379,
        db=int(parsed.path.lstrip('/')) if parsed.path else 0,
        password=redis_password if redis_password else None,
        decode_responses=True
    )
```

---

## 📋 Setup Checklist

- [ ] **Step 1:** Copy `.env.example` to `.env`
  ```bash
  cp .env.example .env
  ```

- [ ] **Step 2:** Update Redis configuration in `.env`
  ```bash
  REDIS_URL=redis://192.168.1.49:6379/0
  REDIS_PASSWORD=redis12345
  ```

- [ ] **Step 3:** Generate and set SECRET_KEY in `.env`
  ```bash
  python3 -c "import secrets; print(secrets.token_hex(32))"
  # Copy output to SECRET_KEY in .env
  ```

- [ ] **Step 4:** Update `services/queue_manager.py` to read Redis credentials from environment (see code above)

- [ ] **Step 5:** Test Redis connection
  ```bash
  redis-cli -h 192.168.1.49 -p 6379 -a redis12345 ping
  # Should return: PONG
  ```

- [ ] **Step 6:** Adjust WORKER_CONCURRENCY based on your system resources

- [ ] **Step 7:** If remote access needed, update HOST and ALLOWED_HOSTS

- [ ] **Step 8:** Review and adjust file size limits if needed

---

## 🧪 Testing Configuration

After updating configuration, test it:

```bash
# Test Redis connection
python3 -c "
import redis
import os
from urllib.parse import urlparse

redis_url = 'redis://192.168.1.49:6379/0'
redis_password = 'redis12345'

parsed = urlparse(redis_url)
client = redis.Redis(
    host=parsed.hostname,
    port=parsed.port,
    db=int(parsed.path.lstrip('/')),
    password=redis_password,
    decode_responses=True
)

try:
    client.ping()
    print('✅ Redis connection successful!')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
"
```

---

## 🚨 Security Notes

1. **Never commit `.env` file to Git** - It's already in `.gitignore`
2. **Keep Redis password secure** - Don't share it publicly
3. **Generate a strong SECRET_KEY** - Use the commands provided above
4. **Restrict Redis access** - Ensure Redis is not exposed to the internet without proper security
5. **Use firewall rules** - Only allow trusted IPs to access Redis port 6379

---

## 📞 Support

If you encounter issues:

1. Check Redis is running: `redis-cli -h 192.168.1.49 -p 6379 -a redis12345 ping`
2. Check application logs: `tail -f logs/app.log`
3. Verify environment variables are loaded: `python3 -c "import os; print(os.getenv('REDIS_URL'))"`
4. Test with minimal configuration first, then add complexity

---

## 🔍 No Other Credentials Needed

Based on the codebase analysis:

- ✅ **No API keys required** - All processing is done locally
- ✅ **No cloud service credentials** - Uses local SQLite database
- ✅ **No email/SMTP configuration** - No email functionality
- ✅ **No OAuth/SSO** - No authentication system implemented
- ✅ **No external AI/ML APIs** - Uses local spaCy models
- ✅ **No payment gateway** - No payment processing

The only external service is **Redis**, which you've already provided credentials for.
