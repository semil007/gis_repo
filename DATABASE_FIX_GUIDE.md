# Database Error Fix Guide

## Problem
You're getting the error: **"Application error: unable to open database file"** when deploying with Docker.

## Root Cause
The issue occurs because:
1. SQLite database files need proper initialization inside Docker containers
2. Volume mounting can cause permission issues
3. Database paths need to be correctly configured for Docker environment

## Solution Applied

### Changes Made

#### 1. **Docker Compose Configuration** (`docker-compose.yml`)
- Changed from mounting individual database files to using a Docker volume
- Database files now stored in `/app/data/` directory inside container
- Added `app_data` volume for persistent database storage

**Before:**
```yaml
volumes:
  - ./processing_sessions.db:/app/processing_sessions.db
  - ./audit_data.db:/app/audit_data.db
```

**After:**
```yaml
volumes:
  - app_data:/app/data
```

#### 2. **Dockerfile Updates**
- Added `/app/data` directory creation
- Enhanced startup script to:
  - Create data directory if it doesn't exist
  - Initialize database files with proper permissions
  - Run database initialization script
  - Set correct ownership for appuser

#### 3. **Database Path Handling** (`init_databases.py`, `services/integration_manager.py`)
- Fixed handling of `sqlite:////` prefix (4 slashes for absolute paths in Docker)
- Properly strips both `sqlite:///` and `sqlite:////` prefixes

#### 4. **Fix Scripts**
- Updated `scripts/fix-docker.sh` (Linux/Mac)
- Created `scripts/fix-docker.bat` (Windows)

## How to Apply the Fix

### On Windows (Your System):

1. **Navigate to your project directory:**
   ```cmd
   cd C:\path\to\gis_repo
   ```

2. **Run the Windows fix script:**
   ```cmd
   scripts\fix-docker.bat
   ```

   Or manually run these commands:
   ```cmd
   docker-compose down -v
   docker-compose rm -f
   del /f processing_sessions.db audit_data.db
   docker-compose build --no-cache
   docker-compose up -d
   ```

### On Linux/Mac:

1. **Navigate to your project directory:**
   ```bash
   cd ~/gis_repo
   ```

2. **Run the fix script:**
   ```bash
   chmod +x scripts/fix-docker.sh
   ./scripts/fix-docker.sh
   ```

## Verification Steps

After running the fix script, verify everything is working:

1. **Check container status:**
   ```cmd
   docker-compose ps
   ```
   All services should show "Up" status.

2. **Check database files were created:**
   ```cmd
   docker-compose exec app ls -lh /app/data/
   ```
   You should see:
   - `processing_sessions.db`
   - `audit_data.db`

3. **Check application logs:**
   ```cmd
   docker-compose logs app
   ```
   Look for:
   - "Initialized database at /app/data/processing_sessions.db"
   - "Initialized database at /app/data/audit_data.db"
   - "Starting Streamlit application..."

4. **Access the application:**
   Open your browser to: `http://192.168.1.49:8501`

## Troubleshooting

### If you still see database errors:

1. **Check database initialization logs:**
   ```cmd
   docker-compose logs app | findstr "database"
   ```

2. **Manually initialize databases:**
   ```cmd
   docker-compose exec app python3 init_databases.py
   ```

3. **Check file permissions inside container:**
   ```cmd
   docker-compose exec app ls -la /app/data/
   ```
   Files should be owned by `appuser:appuser`

4. **Restart the application:**
   ```cmd
   docker-compose restart app
   ```

### If containers won't start:

1. **Check Docker logs:**
   ```cmd
   docker-compose logs --tail=100
   ```

2. **Remove all volumes and start fresh:**
   ```cmd
   docker-compose down -v
   docker volume prune -f
   docker-compose up -d
   ```

### If you need to reset everything:

```cmd
docker-compose down -v
docker system prune -a -f
docker volume prune -f
docker-compose build --no-cache
docker-compose up -d
```

## Key Improvements

1. **Persistent Data**: Database files are now stored in a Docker volume, ensuring data persists across container restarts
2. **Automatic Initialization**: Databases are automatically created and initialized on first startup
3. **Proper Permissions**: Files are created with correct ownership and permissions
4. **Better Error Handling**: Enhanced error messages and logging for troubleshooting

## Environment Variables

The application uses these environment variables for database paths:
- `DATABASE_URL=sqlite:////app/data/processing_sessions.db`
- `AUDIT_DATABASE_URL=sqlite:////app/data/audit_data.db`

Note: The 4 slashes (`////`) indicate an absolute path in SQLite URI format.

## Additional Commands

**View real-time logs:**
```cmd
docker-compose logs -f app
```

**Access container shell:**
```cmd
docker-compose exec app bash
```

**Check database contents:**
```cmd
docker-compose exec app sqlite3 /app/data/processing_sessions.db ".tables"
```

**Backup databases:**
```cmd
docker cp hmo-processor:/app/data/processing_sessions.db ./backup_sessions.db
docker cp hmo-processor:/app/data/audit_data.db ./backup_audit.db
```

## Support

If you continue to experience issues:
1. Check the logs: `docker-compose logs app`
2. Verify Docker is running: `docker ps`
3. Ensure ports 8501, 8000, and 6379 are not in use
4. Check disk space: `docker system df`
