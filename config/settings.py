# controller/config/settings.py
import os
from typing import ClassVar
from pydantic_settings import BaseSettings
from pathlib import Path
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    DB_USER: str = os.getenv("DB_USER", "root")
    # DB_PASSWORD: str = quote_plus(os.getenv("DB_PASSWORD", "unisys@123"))
    DB_PASSWORD: str = quote_plus(os.getenv("DB_PASSWORD", ""))
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", 3306))
    DB_NAME: str = os.getenv("DB_NAME", "drm_system")

    # DATABASE_URL: ClassVar[str] = f"mysql+pymysql://{os.getenv('DB_USER', 'root')}:{quote_plus(os.getenv('DB_PASSWORD', 'unisys@123'))}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME', 'drm_system')}"
    DATABASE_URL: ClassVar[str] = f"mysql+pymysql://{os.getenv('DB_USER', 'root')}:{quote_plus(os.getenv('DB_PASSWORD', ''))}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME', 'drm_system')}"

    OUTPUT_DIR: Path = Path("output")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 9000))

    MAX_CONCURRENT_JOBS : int = int(os.getenv("MAX_CONCURRENT_JOBS", 10))
    # MAX_CONCURRENT_JOBS : int = int(os.getenv("MAX_CONCURRENT_JOBS", 0))

    MAX_JOBS_PER_WORKER : int = int(os.getenv("MAX_JOBS_PER_WORKER", 3))
    POLL_INTERVAL: int = int(os.getenv("POLL_INTERVAL", 5))

    IS_PRODUCTION: bool = bool(os.getenv("IS_PRODUCTION", False))

    # WORKERPORT: int = int(os.getenv("WORKERPORT", 9000))
    WORKERPORT: int = int(os.getenv("WORKERPORT", 10200))

    class Config:
        env_file = ".env"
        extra = "forbid"

settings = Settings()
