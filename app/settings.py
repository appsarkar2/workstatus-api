# backend/app/settings.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Centralized configuration loaded from environment variables."""

    # MongoDB
    mongo_uri: str
    mongo_db_name: str = "workstatus_v1"

    # Auth
    jwt_secret: str
    jwt_expire_minutes: int = 1440

    # App metadata
    app_version: str = "3.1.0"
    environment: str = "production"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()