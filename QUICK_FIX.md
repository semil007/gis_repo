# 🚀 QUICK FIX GUIDE

## Common Issues & Solutions

### Issue 1: Database Error
```
Application error: unable to open database file
```

**Solution (10 seconds):**
```bash
python init_databases.py
```

Then restart your app:
```bash
streamlit run app.py
```

---

### Issue 2: Module Import Error
```
ModuleNotFoundError: No module named 'models'
```

## The Solution (30 seconds)

Run this on your server:

```bash
cd ~/gis_repo
./scripts/fix-docker.sh
```

**That's it!** Wait 2-3 minutes for rebuild, then access:
```
http://192.168.1.49:8501
```

---

## Alternative (Manual Fix)

If the script doesn't work:

```bash
cd ~/gis_repo
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## What Was Fixed

✅ Added `PYTHONPATH=/app` to Dockerfile  
✅ Added `PYTHONPATH=/app` to docker-compose.yml  
✅ Changed app command to use `app.py` instead of `web/streamlit_app.py`  
✅ Created proper `worker.py` entry point  
✅ Fixed worker command in docker-compose.yml  

---

## Verify It's Working

```bash
# Check containers are running
docker-compose ps

# Should show all containers as "Up" or "Up (healthy)"
```

Then open browser: `http://192.168.1.49:8501`

---

## If Still Not Working

See detailed guide: `DOCKER_FIX_GUIDE.md`

Or check logs:
```bash
docker-compose logs app
docker-compose logs worker
```

---

## Files Modified

1. `Dockerfile` - Added PYTHONPATH
2. `docker-compose.yml` - Added PYTHONPATH to services
3. `worker.py` - Created (new file)
4. `scripts/fix-docker.sh` - Created (new file)

All changes are already in your repository. Just rebuild!
