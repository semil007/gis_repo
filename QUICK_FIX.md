# 🚀 QUICK FIX GUIDE

## ⚠️ IMPORTANT: Run on Ubuntu Server, NOT WSL

**You MUST run these commands on your Ubuntu server (192.168.1.49), not from WSL on Windows!**

### Step-by-Step Instructions:

**1. SSH into your Ubuntu server:**
```bash
ssh abdul09@192.168.1.49
```

**2. Navigate to your project:**
```bash
cd ~/gis_repo
```

**3. Run the fix script:**
```bash
chmod +x scripts/fix-docker.sh
./scripts/fix-docker.sh
```

**4. Wait 2-3 minutes, then check:**
```bash
docker-compose ps
```

**5. Access your app:**
Open browser: `http://192.168.1.49:8501`

## Common Issues & Solutions

### Issue 1: Database Error
```
Application error: unable to open database file
```

**Solution for Ubuntu Server (30 seconds):**

```bash
cd ~/gis_repo
chmod +x scripts/fix-docker.sh
./scripts/fix-docker.sh
```

**That's it!** Wait 2-3 minutes for rebuild, then access:
```
http://192.168.1.49:8501
```

---

### Issue 2: Module Import Error
```
ModuleNotFoundError: No module named 'models'
```

**Solution:** Same as above - run the fix script:

```bash
cd ~/gis_repo
./scripts/fix-docker.sh
```

---

## ⚠️ Common Mistake: Running from WSL

**DO NOT run from WSL/Windows!** If you see errors like:
- `SIGBUS: bus error`
- `Input/output error`
- `/mnt/c/Users/...` in paths

You're running from the wrong location. SSH into the Ubuntu server instead:

```bash
# From Windows/WSL, connect to your server:
ssh abdul09@192.168.1.49

# Then run the fix:
cd ~/gis_repo
./scripts/fix-docker.sh
```

---

## Alternative (Manual Fix)

If the script doesn't work on the Ubuntu server, run these commands:

```bash
cd ~/gis_repo

# Stop containers
docker-compose down

# Remove old database files
rm -f processing_sessions.db audit_data.db

# Create fresh database files
touch processing_sessions.db audit_data.db
chmod 666 processing_sessions.db audit_data.db

# Create directories
mkdir -p uploads downloads temp logs cache
chmod -R 777 uploads downloads temp logs cache

# Rebuild and start
docker-compose build --no-cache
docker-compose up -d

# Wait for startup (30 seconds)
sleep 30

# Initialize databases
docker-compose exec app python3 init_databases.py

# Restart to apply changes
docker-compose restart app worker

# Check status
docker-compose ps
docker-compose logs app | tail -20
```

---

## What Was Fixed

✅ Database files are created before container starts  
✅ Proper permissions set for database files (666)  
✅ Required directories created (uploads, downloads, temp, logs, cache)  
✅ Database schemas initialized automatically on startup  
✅ Added `PYTHONPATH=/app` to Dockerfile and docker-compose.yml  
✅ Created startup script to handle database initialization  

---

## Verify It's Working

```bash
# Check containers are running
docker-compose ps

# Should show all containers as "Up" or "Up (healthy)"

# Check database files exist
ls -lh *.db

# Should show:
# -rw-rw-rw- 1 user user [size] [date] audit_data.db
# -rw-rw-rw- 1 user user [size] [date] processing_sessions.db
```

Then open browser: `http://192.168.1.49:8501`

---

## If Still Not Working

**Check logs for specific errors:**
```bash
docker-compose logs app
docker-compose logs worker
```

**Common issues:**

1. **Permission denied on database files:**
   ```bash
   chmod 666 processing_sessions.db audit_data.db
   docker-compose restart app worker
   ```

2. **Database files are empty:**
   ```bash
   docker-compose exec app python3 init_databases.py
   docker-compose restart app
   ```

3. **Containers not starting:**
   ```bash
   docker-compose down
   docker system prune -f
   ./scripts/fix-docker.sh
   ```

See detailed guide: `DOCKER_FIX_GUIDE.md`

---

## Files Modified

1. `Dockerfile` - Added startup script for database initialization
2. `docker-compose.yml` - Volume mounts for database files
3. `scripts/fix-docker.sh` - Database creation and initialization
4. `QUICK_FIX.md` - Updated with Ubuntu server instructions

All changes are in your repository. Just run the fix script!

---

## Understanding the Fix

The "unable to open database file" error occurs because:

1. **Database files don't exist** - The SQLite database files need to be created on the host before Docker mounts them
2. **Wrong permissions** - Database files need read/write permissions (666) for the container user
3. **Empty database files** - Even if files exist, they need proper schema initialization

**What the fix does:**

1. Creates empty database files on the host system
2. Sets proper permissions (666) so Docker containers can read/write
3. Creates required directories (uploads, downloads, temp, logs, cache)
4. Rebuilds Docker images with updated configuration
5. Initializes database schemas inside the container
6. Starts all services with proper environment variables

**Why it works:**

- Docker volume mounts require files to exist on the host first
- The startup script checks if databases are empty and initializes them
- Proper permissions allow the non-root container user to access files
- Environment variables point to the correct database paths inside containers
