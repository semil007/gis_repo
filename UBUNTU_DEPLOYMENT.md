# Ubuntu Server Deployment Guide

## Quick Start

1. **Clone the repository** (if not already done):
   ```bash
   git clone <your-repo-url>
   cd hmo-document-processor
   ```

2. **Make the startup script executable**:
   ```bash
   chmod +x start-docker.sh
   ```

3. **Start the application**:
   ```bash
   ./start-docker.sh
   ```

4. **Access the application**:
   - Local: http://localhost:8501
   - Remote: http://YOUR_SERVER_IP:8501

## Prerequisites

### Install Docker (if not installed)
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

### Install Docker Compose (if not installed)
```bash
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## Manual Deployment Steps

If you prefer manual deployment:

1. **Create directories**:
   ```bash
   mkdir -p uploads downloads temp logs cache data
   chmod 755 uploads downloads temp logs cache data
   ```

2. **Build and start services**:
   ```bash
   docker-compose up -d --build
   ```

3. **Check status**:
   ```bash
   docker-compose ps
   docker-compose logs
   ```

## Troubleshooting

### Check if services are running:
```bash
docker-compose ps
```

### View logs:
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs app
docker-compose logs redis
docker-compose logs worker
```

### Restart services:
```bash
docker-compose restart
```

### Rebuild if needed:
```bash
docker-compose down
docker-compose up -d --build
```

### Check Redis connection:
```bash
docker-compose exec redis redis-cli ping
```

## Port Configuration

- **8501**: Streamlit web interface
- **8000**: FastAPI endpoints (if used)
- **6379**: Redis (internal only)

## Firewall Configuration

If you have a firewall enabled, allow the necessary ports:

```bash
sudo ufw allow 8501
sudo ufw allow 8000  # if using FastAPI
```

## Environment Variables

The application uses these key environment variables (configured in docker-compose.yml):

- `REDIS_URL=redis://redis:6379/0`
- `DATABASE_URL=sqlite:////app/data/processing_sessions.db`
- `AUDIT_DATABASE_URL=sqlite:////app/data/audit_data.db`

## Data Persistence

Data is persisted in Docker volumes:
- `redis_data`: Redis data
- `app_data`: Application databases
- Local directories: `uploads`, `downloads`, `temp`, `logs`, `cache`

## Updating the Application

To update with new code:

```bash
git pull
./start-docker.sh --rebuild
```

## Stopping the Application

```bash
docker-compose down
```

## Complete Cleanup (removes all data)

```bash
docker-compose down -v
docker system prune -a
```

## System Requirements

- **RAM**: Minimum 2GB, recommended 4GB+
- **Storage**: Minimum 10GB free space
- **CPU**: 2+ cores recommended
- **OS**: Ubuntu 18.04+ or similar Linux distribution