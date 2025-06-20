from pathlib import Path
import os
from typing import Dict, Any
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

class Config:
    # Base paths
    BASE_DIR = Path(__file__).resolve().parent
    # Remove UPLOAD_DIR
    OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", os.path.expanduser("~/converter_x_output")))
    LOG_DIR = BASE_DIR / "logs"
    LOG_FILE_PATH = str(LOG_DIR / "audit.log")

    # Create necessary directories
    for directory in [OUTPUT_DIR, LOG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

    # API Settings
    API_V1_PREFIX = "/api/v1"
    PROJECT_NAME = "Excel to XML Converter"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

    # Security
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("No SECRET_KEY set in environment")

    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
    if not ENCRYPTION_KEY:
        raise ValueError("No ENCRYPTION_KEY set in environment")

    # Session
    SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "5"))

    # CORS
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

    # File Upload
    MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
    ALLOWED_EXTENSIONS = {".xls", ".xlsx"}

    # Rate Limiting
    RATE_LIMIT_CALLS = int(os.getenv("RATE_LIMIT_CALLS", "100"))
    RATE_LIMIT_PERIOD = int(os.getenv("RATE_LIMIT_PERIOD", "60"))

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "logs/audit.log")

    # XML Settings
    XML_NAMESPACE = "http://www.example.com/xml/converter"
    XML_SCHEMA_VERSION = "1.0"

    @classmethod
    def get_settings(cls) -> Dict[str, Any]:
        """Get all settings as a dictionary."""
        return {
            name: value for name, value in vars(cls).items()
            if not name.startswith('_') and not callable(value)
        }

    @classmethod
    def validate_file_extension(cls, filename: str) -> bool:
        """Validate if the file extension is allowed."""
        return Path(filename).suffix.lower() in cls.ALLOWED_EXTENSIONS

    @classmethod
    def get_upload_path(cls, filename: str) -> Path:
        """Get the full path for an upload file."""
        return cls.UPLOAD_DIR / filename

    @classmethod
    def get_output_path(cls, filename: str) -> Path:
        """Get the full path for an output file."""
        return cls.OUTPUT_DIR / filename

# Create singleton instance
config = Config()

log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
logging.basicConfig(filename=config.LOG_FILE_PATH, level=log_level)