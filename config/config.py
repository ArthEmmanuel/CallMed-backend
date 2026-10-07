import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent


def load_config():
    load_dotenv(BASE_DIR / ".env")

    origins = os.getenv("CORS_ORIGINS", "*")
    if origins != "*":
        origins = [origin.strip() for origin in origins.split(",") if origin.strip()]

    return {
        "API_HOST": os.getenv("API_HOST", "0.0.0.0"),
        "API_PORT": int(os.getenv("API_PORT", "5000")),
        "DEBUG": os.getenv("FLASK_DEBUG", "true").lower() in {"1", "true", "yes"},
        "CORS_ORIGINS": origins,
        "MONGO_URI": os.getenv("MONGO_URI"),
        "DB_NAME": os.getenv("DB_NAME", "callmed"),
    }
