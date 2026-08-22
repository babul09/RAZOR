"""
RAZOR — Application Configuration
Loads settings from environment variables / .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://razor:razor@localhost:5432/razor_db"
    redis_url: str = "redis://localhost:6379/0"
    gemini_api_key: str = ""
    secret_key: str = "dev-secret-change-in-production"
    environment: str = "development"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
