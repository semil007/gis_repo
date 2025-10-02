# Docker Fix Guide - Module Import Error

## 🐛 Problem

You're getting this error:
```
ModuleNotFoundError: No module named 'models'
```

This happens because the Docker container can't find the Python modules.

## ✅ Solution

I've fixed the following files:

1. **Dockerfile** - Added `PYTHONPATH=/app` environment variable
2. **docker-compose.yml** - Added `PYTHONPATH=/app` to both app and worker services
3. **worker.py** - Created proper worker entry point
4. **scripts/fix-docker.sh** - Quick fix script to rebuild containers

## 🚀 Quick Fix (Run This)

On your server, run:

```bash
cd ~/gis_repo

# Option 1: Use the fix script (easiest)
./scripts/fix-docker.sh

# Option 2: Manual steps
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 📋 Step-by-Step Fix

### Step 1: Stop Current Containers

```bash
cd ~/gis_repo
docker-compose down
```

### Step 2: Rebuild Images

```bash
docker-compose build --no-cache
```

This will rebuild the Docker images with the fixes.

### Step 3: Start Services

```bash
docker-compose up -d
```

### Step 4: Verify Services

```bash
# Check if containers are running
docker-compose ps

# Check app logs
docker-compose logs app

# Check worker logs
docker-compose logs worker
```

### Step 5: Test the Application

Open your browser and go to:
```
http://192.168.1.49:8501
```

## 🔍 Verify the Fix

Check if the application is working:

```bash
# Check app container logs for errors
docker-compose logs --tail=100 app | grep -i error

# Check if the app is healthy
curl http://192.168.1.49:8501/_stcore/health

# Check Redis connection
docker-compose exec app python3 -c "
import sys
sys.path.insert(0, '/app')
from services.queue_manager import QueueManager
try:
    qm = QueueManager()
    print('✅ Redis connection successful!')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

## 📝 What Was Fixed

### 1. Dockerfile Changes

**Before:**
```dockerfile
ENV APP_HOME=/app
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata
```

**After:**
```dockerfile
ENV APP_HOME=/app
ENV PYTHONPATH=/app:$PYTHONPATH
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata
```

And changed the command from:
```dockerfile
CMD ["streamlit", "run", "web/streamlit_app.py", ...]
```

To:
```dockerfile
CMD ["streamlit", "run", "app.py", ...]
```

### 2. docker-compose.yml Changes

Added `PYTHONPATH=/app` to both services:

```yaml
environment:
  - PYTHONPATH=/app
  - REDIS_URL=redis://redis:6379/0
  # ... other variables
```

Changed worker command from:
```yaml
command: ["python3", "services/queue_worker.py"]
```

To:
```yaml
command: ["python3", "worker.py"]
```

### 3. Created worker.py

Created a proper entry point for the worker service that:
- Sets up Python path correctly
- Initializes the integration manager
- Handles job processing
- Manages worker lifecycle

## 🧪 Testing After Fix

### Test 1: Check Container Status

```bash
docker-compose ps
```

Expected output:
```
NAME            STATUS
hmo-processor   Up (healthy)
hmo-redis       Up (healthy)
hmo-worker      Up
```

### Test 2: Check Application Logs

```bash
docker-compose logs app | tail -20
```

Should NOT show "ModuleNotFoundError"

### Test 3: Access Web Interface

Open browser: `http://192.168.1.49:8501`

You should see the HMO Document Processing Pipeline interface.

### Test 4: Test File Upload

1. Go to http://192.168.1.49:8501
2. Try uploading a test PDF or DOCX file
3. Check if processing starts without errors

## 🔧 Troubleshooting

### If containers won't start:

```bash
# Check detailed logs
docker-compose logs -f

# Check specific service
docker-compose logs app
docker-compose logs worker
docker-compose logs redis
```

### If still getting import errors:

```bash
# Enter the container and check Python path
docker-compose exec app bash
echo $PYTHONPATH
ls -la /app/models
python3 -c "import sys; print(sys.path)"
```

### If Redis connection fails:

```bash
# Check Redis is running
docker-compose exec redis redis-cli ping

# Check Redis from app container
docker-compose exec app redis-cli -h redis ping
```

### If worker keeps restarting:

```bash
# Check worker logs
docker-compose logs worker

# The worker might be failing to connect to Redis or import modules
# Check the logs for specific errors
```

## 🔄 Clean Rebuild (If Nothing Else Works)

If you're still having issues, do a complete clean rebuild:

```bash
# Stop and remove everything
docker-compose down -v

# Remove all images
docker-compose rm -f
docker rmi $(docker images 'gis_repo*' -q)

# Rebuild from scratch
docker-compose build --no-cache

# Start services
docker-compose up -d

# Watch logs
docker-compose logs -f
```

## 📞 Still Having Issues?

If the fix doesn't work, check:

1. **Docker version**: `docker --version` (should be 20.10+)
2. **Docker Compose version**: `docker-compose --version` (should be 1.29+)
3. **Disk space**: `df -h` (ensure you have enough space)
4. **Permissions**: Ensure your user can run Docker commands

Run this diagnostic:

```bash
# Save diagnostic info
docker-compose logs > docker-logs.txt
docker-compose ps > docker-status.txt
docker images > docker-images.txt

# Check the files for errors
cat docker-logs.txt | grep -i error
```

## ✅ Success Indicators

You'll know it's working when:

1. ✅ All containers show "Up" or "Up (healthy)" status
2. ✅ No "ModuleNotFoundError" in logs
3. ✅ Web interface loads at http://192.168.1.49:8501
4. ✅ You can upload and process files
5. ✅ Worker logs show "Connected to Redis queue"

## 🎉 After Successful Fix

Once everything is working:

1. Test file upload and processing
2. Check the audit interface
3. Verify CSV downloads work
4. Monitor logs for any other issues

```bash
# Monitor all services
docker-compose logs -f

# Or monitor specific service
docker-compose logs -f app
```

---

## Summary

**The fix is simple:**
1. Run `./scripts/fix-docker.sh`
2. Wait for rebuild to complete
3. Access http://192.168.1.49:8501

**Or manually:**
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

The issue was that Python couldn't find the modules because `PYTHONPATH` wasn't set correctly in the Docker containers. This is now fixed.
