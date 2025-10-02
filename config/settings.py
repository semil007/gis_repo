"""
Configuration settings for the Document Processing Pipeline
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent

# File upload settings
MAX_FILE_SIZE_MB = 100
ALLOWED_EXTENSIONS = ['.pdf', '.docx']
UPLOAD_DIR = BASE_DIR / 'uploads'
DOWNLOAD_DIR = BASE_DIR / 'downloads'
TEMP_DIR = BASE_DIR / 'temp'

# Database settings
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{BASE_DIR}/data/app.db')

# Redis settings
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

# Processing settings
CONFIDENCE_THRESHOLD = 0.7
MAX_PROCESSING_TIME_SECONDS = 300
CHUNK_SIZE_MB = 10

# OCR settings
TESSERACT_CONFIG = '--oem 3 --psm 6'
OCR_LANGUAGES = ['eng']

# NLP settings
SPACY_MODEL = 'en_core_web_sm'

# Default column mappings
DEFAULT_COLUMNS = [
    'council',
    'reference', 
    'hmo_address',
    'licence_start',
    'licence_expiry',
    'max_occupancy',
    'hmo_manager_name',
    'hmo_manager_address',
    'licence_holder_name',
    'licence_holder_address',
    'number_of_households',
    'number_of_shared_kitchens',
    'number_of_shared_bathrooms',
    'number_of_shared_toilets',
    'number_of_storeys'
]

# Logging settings
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_DIR = BASE_DIR / 'logs'

# Web interface settings
STREAMLIT_PORT = 8501
FASTAPI_PORT = 8000