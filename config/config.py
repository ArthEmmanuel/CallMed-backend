import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CORS_ORIGINS = "http://localhost:5500,http://127.0.0.1:5500"


def load_config():
    load_dotenv(BASE_DIR / ".env")

    origins = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
        if origin.strip()
    ]
    try:
        port = int(os.getenv("API_PORT", "5000"))
        token_max_age = int(os.getenv("TOKEN_MAX_AGE_SECONDS", "3600"))
    except ValueError as error:
        raise RuntimeError("API_PORT e TOKEN_MAX_AGE_SECONDS devem ser inteiros") from error

    if not 1 <= port <= 65535:
        raise RuntimeError("API_PORT deve estar entre 1 e 65535")
    if not 60 <= token_max_age <= 604800:
        raise RuntimeError(
            "TOKEN_MAX_AGE_SECONDS deve estar entre 60 e 604800"
        )

    return {
        "API_HOST": os.getenv("API_HOST", "127.0.0.1"),
        "API_PORT": port,
        "DEBUG": os.getenv("FLASK_DEBUG", "false").lower() in {"1", "true", "yes"},
        "CORS_ORIGINS": origins,
        "SECRET_KEY": os.getenv("SECRET_KEY"),
        "TOKEN_MAX_AGE_SECONDS": token_max_age,
        "DATABASE_PROJECT_PATH": os.getenv("DATABASE_PROJECT_PATH"),
        "MONGO_URI": os.getenv("MONGO_URI"),
        "DB_NAME": os.getenv("DB_NAME", "callmed"),
    }
