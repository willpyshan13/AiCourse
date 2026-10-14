"""Application paths and security settings."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"
PRACTICE_UPLOAD_DIR = UPLOAD_DIR / "practices"
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_EXCEL_BYTES = 5 * 1024 * 1024
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "").split(",") if origin.strip()]
