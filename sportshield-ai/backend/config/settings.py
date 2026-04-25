# SportShield AI | Google Solution Challenge 2026 | First Prize Target

"""
Configuration settings for the SportShield AI platform.
Loads environment variables and sets up global application settings.
"""

import os
import tempfile
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Optional integration vars. The app should still boot locally even if one
# of these services is not configured yet.
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '').strip()
FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID', '').strip()
FIREBASE_CREDENTIALS_JSON = os.environ.get('FIREBASE_CREDENTIALS_JSON', '').strip()

# OPTIONAL vars with defaults
GOOGLE_CSE_KEY = os.environ.get('GOOGLE_CSE_KEY', '')
GOOGLE_CSE_CX = os.environ.get('GOOGLE_CSE_CX', '')
FACT_CHECK_API_KEY = os.environ.get('FACT_CHECK_API_KEY', '')
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')
SENDGRID_FROM_EMAIL = os.environ.get('SENDGRID_FROM_EMAIL', '')

# Application Config
HAMMING_THRESHOLD = int(os.environ.get('HAMMING_THRESHOLD', '10'))
MAX_FILE_SIZE_MB = int(os.environ.get('MAX_FILE_SIZE_MB', '50'))
DEMO_MODE = os.environ.get('DEMO_MODE', 'false').lower() == 'true'
PORT = int(os.environ.get('PORT', '8080'))
TMP_DIR = os.environ.get('TMP_DIR', os.path.join(tempfile.gettempdir(), 'sportshield'))

# Ensure the temporary directory exists
os.makedirs(TMP_DIR, exist_ok=True)

# RIGHTS_VALUE_USD dict
RIGHTS_VALUE_USD = {
    'IPL': 500,
    'Cricket': 400,
    'FIFA': 800,
    'Olympics': 1000,
    'NBA': 600,
    'F1': 700,
    'Athletics': 350,
    'Wrestling': 300,
    'Hockey': 300,
    'Other': 250
}

# Allowed Types
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
ALLOWED_VIDEO_TYPES = {'video/mp4', 'video/quicktime', 'video/mov'}
ALLOWED_ALL_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES
