# 🔧 Troubleshooting Guide

## Database Errors

### Error: "unable to open database file"

**Symptoms:**
- Application shows: "Application error: unable to open database file"
- App fails to start or crashes when accessing data

**Causes:**
1. Database files don't exist
2. Incorrect file permissions
3. Database path misconfiguration
4. Database file corruption

**Solutions:**

#### Quick Fix (Recommended)
```bash
python init_databases.py
```

This will:
- Create both required database files
- Initialize all tables and indexes
- Verify database connectivity
- Show database statistics

#### Manual Fix
If the quick fix doesn't work:

1. **Check if databases exist:**
   ```bash
   # Windows
   dir *.db
   
   # Linux/Mac
   ls -la *.db
   ```

2. **Check environment variables:**
   ```bash
   # View your .env file
   type .env    # Windows
   cat .env     # Linux/Mac
   ```
   
   Should contain:
   ```
   DATABASE_URL=sqlite:///processing_sessions.db
   AUDIT_DATABASE_URL=sqlite:///audit_data.db
   ```

3. **Check file permissions:**
   ```bash
   # Windows - ensure you have write access to the directory
   icacls processing_sessions.db
   
   # Linux/Mac
   chmod 664 *.db
   ```

4. **Delete and recreate databases:**
   ```bash
   # Backup first if you have data
   copy processing_sessions.db processing_sessions.db.backup
   copy audit_data.db audit_data.db.backup
   
   # Delete corrupted databases
   del processing_sessions.db
   del audit_data.db
   
   # Recreate
   python init_databases.py
   ```

#### Docker-Specific Issues

If running in Docker:

1. **Check volume mounts:**
   ```bash
   docker-compose down
   docker volume ls
   docker volume rm docs_data_app_data  # If needed
   docker-compose up -d
   ```

2. **Check container logs:**
   ```bash
   docker-compose logs app
   docker-compose logs worker
   ```

3. **Exec into container and check:**
   ```bash
   docker-compose exec app bash
   ls -la *.db
   python init_databases.py
   exit
   ```

---

## Redis Connection Errors

### Error: "Connection refused" or "Redis not available"

**Solutions:**

1. **Check if Redis is running:**
   ```bash
   # Windows (if installed locally)
   redis-cli ping
   
   # Docker
   docker-compose ps redis
   ```

2. **Check Redis URL in .env:**
   ```
   REDIS_URL=redis://localhost:6379/0
   # or for Docker
   REDIS_URL=redis://redis:6379/0
   ```

3. **Restart Redis:**
   ```bash
   # Docker
   docker-compose restart redis
   
   # Local Windows service
   net stop Redis
   net start Redis
   ```

---

## Module Import Errors

### Error: "ModuleNotFoundError: No module named 'X'"

**Solutions:**

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Check Python path:**
   ```bash
   python -c "import sys; print('\n'.join(sys.path))"
   ```

3. **For Docker:**
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

---

## File Upload Errors

### Error: "File too large" or "Invalid file format"

**Solutions:**

1. **Check file size limit in .env:**
   ```
   MAX_FILE_SIZE=104857600  # 100MB
   ```

2. **Check supported formats:**
   ```
   SUPPORTED_FORMATS=pdf,docx
   ```

3. **Ensure upload directory exists:**
   ```bash
   mkdir uploads
   mkdir downloads
   mkdir temp
   ```

---

## OCR/Tesseract Errors

### Error: "Tesseract not found" or OCR fails

**Solutions:**

1. **Install Tesseract:**
   ```bash
   # Windows - Download from: https://github.com/UB-Mannheim/tesseract/wiki
   # Then add to PATH
   
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr
   
   # macOS
   brew install tesseract
   ```

2. **Configure Tesseract path in .env:**
   ```
   TESSERACT_CMD=tesseract
   # or full path on Windows
   TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
   ```

---

## Performance Issues

### App is slow or unresponsive

**Solutions:**

1. **Check worker concurrency:**
   ```
   WORKER_CONCURRENCY=2  # Reduce if system is slow
   ```

2. **Clear cache:**
   ```bash
   # Delete cache directories
   rmdir /s /q __pycache__
   rmdir /s /q .pytest_cache
   ```

3. **Check system resources:**
   ```bash
   # Windows
   taskmgr
   
   # Linux
   top
   htop
   ```

4. **Optimize database:**
   ```bash
   python -c "import sqlite3; conn = sqlite3.connect('processing_sessions.db'); conn.execute('VACUUM'); conn.close()"
   ```

---

## Port Already in Use

### Error: "Address already in use" or port conflict

**Solutions:**

1. **Find process using the port:**
   ```bash
   # Windows
   netstat -ano | findstr :8501
   
   # Linux/Mac
   lsof -i :8501
   ```

2. **Kill the process:**
   ```bash
   # Windows (use PID from netstat)
   taskkill /PID <PID> /F
   
   # Linux/Mac
   kill -9 <PID>
   ```

3. **Change port in .env:**
   ```
   STREAMLIT_PORT=8502
   ```

---

## Docker Issues

### Containers won't start or keep restarting

**Solutions:**

1. **Check logs:**
   ```bash
   docker-compose logs --tail=50 app
   docker-compose logs --tail=50 worker
   docker-compose logs --tail=50 redis
   ```

2. **Rebuild containers:**
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

3. **Check Docker resources:**
   - Ensure Docker has enough memory (4GB+ recommended)
   - Check disk space: `docker system df`
   - Clean up: `docker system prune -a`

4. **Reset everything:**
   ```bash
   docker-compose down -v
   docker system prune -a --volumes
   docker-compose up -d
   ```

---

## Getting Help

If none of these solutions work:

1. **Check logs:**
   ```bash
   # Application logs
   type logs\app.log
   
   # Docker logs
   docker-compose logs --tail=100
   ```

2. **Run diagnostics:**
   ```bash
   python -c "from services.integration_manager import IntegrationManager; im = IntegrationManager(); status = im.validate_system_components(); print(status)"
   ```

3. **Collect information:**
   - Error message (full text)
   - Session ID (if available)
   - Steps to reproduce
   - System information (OS, Python version)
   - Log files

4. **Contact support with:**
   - Error details
   - Log excerpts
   - Configuration (without sensitive data)
