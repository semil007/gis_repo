# Use Ubuntu 22.04 as base image for better compatibility
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV APP_HOME=/app
ENV PYTHONPATH=/app:$PYTHONPATH
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    poppler-utils \
    libpoppler-cpp-dev \
    redis-server \
    git \
    curl \
    wget \
    build-essential \
    libssl-dev \
    libffi-dev \
    libjpeg-dev \
    libpng-dev \
    libopencv-dev \
    python3-opencv \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR $APP_HOME

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Download spaCy English model
RUN python3 -m spacy download en_core_web_sm

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/uploads /app/downloads /app/temp /app/logs /app/cache /app/data

# Set permissions
RUN chmod +x scripts/*.sh

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser $APP_HOME
USER appuser

# Expose ports
EXPOSE 8501 8000 6379

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Create startup script
USER root
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "Starting HMO Processor..."\n\
\n\
# Ensure data directory and database files exist with proper permissions\n\
mkdir -p /app/data\n\
for db_file in /app/data/processing_sessions.db /app/data/audit_data.db; do\n\
    if [ ! -f "$db_file" ]; then\n\
        echo "Creating $db_file..."\n\
        touch "$db_file"\n\
    fi\n\
done\n\
chown -R appuser:appuser /app/data\n\
chmod -R 775 /app/data\n\
\n\
# Initialize databases if they are empty or not properly initialized\n\
echo "Initializing databases..."\n\
su - appuser -c "cd /app && python3 /app/init_databases.py" || true\n\
\n\
# Ensure proper ownership\n\
chown -R appuser:appuser /app/data /app/uploads /app/downloads /app/temp /app/logs /app/cache\n\
\n\
# Start the application as appuser\n\
echo "Starting Streamlit application..."\n\
exec su - appuser -c "cd /app && streamlit run app.py --server.port=8501 --server.address=0.0.0.0"\n\
' > /app/start.sh && chmod +x /app/start.sh

# Default command
CMD ["/app/start.sh"]