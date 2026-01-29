# config.py - Top Camera Configuration
import os
from pathlib import Path
import logging

# Base paths
BASE_DIR = Path(__file__).parent
SAVE_FOLDER = BASE_DIR / "top_camera_frames"
DB_PATH = BASE_DIR / "top_camera_detection.db"
MODEL_PATH = BASE_DIR / "model"

# Create directories
SAVE_FOLDER.mkdir(exist_ok=True)

# ========== DATABASE CONFIGURATION ==========
DB_CONFIG = {
    'timeout': 10.0,
    'custom_pallet_table': 'custom_pallets',
    'custom_keg_table': 'custom_keg_locations'
}

# ========== CAMERA CONFIGURATION (UPDATED) ==========
TOP_CAMERA_CONFIG = {
    'type': 'v4l2',   # Explicitly marking as V4L2 for Linux
    'device': 10,     # UPDATED: Matches your working test script (/dev/video10)
    'width': 1920,    # UPDATED: Full HD
    'height': 1080,   # UPDATED: Full HD
    'fps': 30,
    'purpose': 'top_camera'
}

# ========== SYSTEM CONFIGURATION ==========
SYSTEM_CONFIG = {
    'forklift_id': "TOP-CAM-001",
    'mac_id': "3C:6D:66:01:5A:F0",  
    'log_level': "INFO",
    'test_mode': False
}

# ========== API ENDPOINTS ==========
API_CONFIG = {
    'customer_api_url': "http://143.110.186.93:5001/api/kegs/customers-for-cam",
    'pallet_create_url': "http://143.110.186.93:5001/api/kegs/custom-palette-dispatch",
    'api_timeout': 10,
    'max_retries': 3
}

# ========== WEBSOCKET CONFIGURATION ==========
WEBSOCKET_CONFIG = {
    "url": "http://143.110.186.93:5001", 
    "reconnection_delay": 5
}

# ========== UI COLORS ==========
COLOR_SCHEME = {
    'bg_dark': (0.12, 0.12, 0.12, 1),
    'primary': (0.0, 0.4, 0.6, 1),
    'accent': (1, 0.5, 0.0, 1),
    'danger': (0.9, 0.1, 0.1, 1),
    'success': (0.0, 0.7, 0.0, 1),
    'text_primary': (1, 1, 1, 1),
    'text_secondary': (0.8, 0.8, 0.8, 1)
}

QRCODE_MODEL_PATH = MODEL_PATH / "best.pt"

# ========== LOGGING SETUP ==========
def setup_logging():
    logging.basicConfig(
        level=getattr(logging, SYSTEM_CONFIG['log_level']),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('top_camera.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()