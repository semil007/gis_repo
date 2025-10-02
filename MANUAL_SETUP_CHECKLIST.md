# Manual Setup Checklist

## 🎯 Quick Summary

Based on your credentials:
- **Redis Host:** 192.168.1.49
- **Redis Port:** 6379
- **Redis Password:** redis12345
- **CUDA:** Disabled (CPU only)

## ✅ What You MUST Do Manually

### Option 1: Automated Setup (Recommended)

Run the configuration script:

```bash
python3 scripts/configure_redis.py
```

This will:
- Test your Redis connection
- Create `.env` file with your credentials
- Generate a secure SECRET_KEY
- Verify everything is working

### Option 2: Manual Setup

1. **Create .env file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit .env file and update these lines:**
   ```bash
   nano .env
   ```
   
   Update:
   ```bash
   REDIS_URL=redis://192.168.1.49:6379/0
   REDIS_PASSWORD=redis12345
   SECRET_KEY=<generate-a-random-key>
   ```

3. **Generate SECRET_KEY:**
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```
   Copy the output and paste it as SECRET_KEY in .env

4. **Test Redis connection:**
   ```bash
   redis-cli -h 192.168.1.49 -p 6379 -a redis12345 ping
   ```
   Should return: `PONG`

## 🔧 What's Already Configured

✅ **CUDA Configuration** - Already set to CPU-only mode  
✅ **Code Updated** - `services/queue_manager.py` now reads from .env  
✅ **Integration Manager** - Uses environment variables  
✅ **Error Handling** - Comprehensive error handling implemented  
✅ **Performance Optimization** - Caching and monitoring in place  

## 📋 No Other Credentials Needed

The system does NOT require:
- ❌ API keys (all processing is local)
- ❌ Cloud service credentials (uses local SQLite)
- ❌ Email/SMTP configuration
- ❌ OAuth/SSO credentials
- ❌ Payment gateway credentials
- ❌ External AI/ML API keys

**Only Redis credentials are needed**, which you've already provided.

## 🚀 After Configuration

Once you've set up the .env file:

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the application:**
   ```bash
   streamlit run app.py
   ```

3. **Or use Docker:**
   ```bash
   docker-compose up -d
   ```

## 🧪 Verify Setup

Test that everything is configured correctly:

```bash
# Test Redis connection
python3 -c "
import os
os.environ['REDIS_URL'] = 'redis://192.168.1.49:6379/0'
os.environ['REDIS_PASSWORD'] = 'redis12345'

from services.queue_manager import QueueManager
try:
    qm = QueueManager()
    print('✅ Redis connection successful!')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
"
```

## 📁 Files Modified for Your Setup

1. **services/queue_manager.py** - Now reads Redis credentials from environment
2. **CONFIGURATION_GUIDE.md** - Complete configuration documentation
3. **scripts/configure_redis.py** - Automated setup script
4. **.env** - You need to create this (see above)

## 🔍 Configuration Files Location

- **Template:** `.env.example` (don't edit this)
- **Your config:** `.env` (create and edit this)
- **Documentation:** `CONFIGURATION_GUIDE.md` (detailed guide)
- **This checklist:** `MANUAL_SETUP_CHECKLIST.md` (you're reading it)

## ⚠️ Important Notes

1. **Never commit .env to Git** - It contains sensitive credentials
2. **Keep Redis password secure** - Don't share publicly
3. **Firewall rules** - Ensure Redis port 6379 is accessible from your application server
4. **Test connection first** - Before starting the full application

## 🆘 Troubleshooting

### Redis Connection Failed

```bash
# Check if Redis is running
redis-cli -h 192.168.1.49 -p 6379 -a redis12345 ping

# Check firewall
telnet 192.168.1.49 6379

# Check Redis logs
# (on Redis server)
tail -f /var/log/redis/redis-server.log
```

### Application Can't Read .env

```bash
# Verify .env exists
ls -la .env

# Check .env content (be careful not to expose password)
grep REDIS_URL .env

# Verify environment variables are loaded
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('REDIS_URL'))"
```

### Permission Issues

```bash
# Ensure .env is readable
chmod 600 .env

# Ensure application has write access to directories
chmod 755 uploads downloads temp logs
```

## 📞 Need Help?

1. Check `CONFIGURATION_GUIDE.md` for detailed documentation
2. Review application logs: `tail -f logs/app.log`
3. Test individual components with the verification scripts above
4. Ensure Redis server is accessible from your application server

---

## ✨ Summary

**You only need to:**
1. Run `python3 scripts/configure_redis.py` (easiest)
   
   OR
   
2. Manually create `.env` file with your Redis credentials

**That's it!** No other manual configuration is required.
