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
    # Razorpay test API credentials (https://dashboard.razorpay.com -> API Keys).
    # When empty, RAZOR runs in "demo" mode and the Razorpay tab shows setup
    # guidance instead of live data.
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_base_url: str = "https://api.razorpay.com/v1"
    # When true and no test keys are set, the Razorpay client serves realistic
    # mock data (same response shape) so the dashboard demo always works.
    razorpay_mock: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
