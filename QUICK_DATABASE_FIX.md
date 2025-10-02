# Quick Database Fix - Windows

## The Problem
Getting error: **"Application error: unable to open database file"**

## The Solution (3 Steps)

### Step 1: Stop and Clean
```cmd
docker-compose down -v
```

### Step 2: Remove Old Database Files
```cmd
del /f processing_sessions.db
del /f audit_data.db
```

### Step 3: Rebuild and Start
```cmd
docker-compose build --no-cache
docker-compose up -d
```

## Or Use the Fix Script

Simply run:
```cmd
scripts\fix-docker.bat
```

## What Changed?

✅ Databases now use Docker volumes (persistent storage)  
✅ Automatic database initialization on startup  
✅ Fixed permission issues  
✅ Proper path handling for Docker environment  

## Verify It Works

1. **Check status:**
   ```cmd
   docker-compose ps
   ```

2. **Check databases:**
   ```cmd
   docker-compose exec app ls -lh /app/data/
   ```

3. **Open app:**
   ```
   http://192.168.1.49:8501
   ```

## Still Having Issues?

Run this to see what's wrong:
```cmd
docker-compose logs app
```

Look for database initialization messages.

---

**Need more details?** See `DATABASE_FIX_GUIDE.md`
