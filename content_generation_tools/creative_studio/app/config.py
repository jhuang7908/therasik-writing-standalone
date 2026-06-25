"""Creative Studio — application settings (Pydantic v2)."""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8",
                                      extra="ignore")

    # Service
    app_name: str = "Creative Studio"
    app_version: str = "0.1.0"
    debug: bool = False
    allowed_origins: list[str] = ["http://localhost:3000", "https://insynbio.com",
                                  "https://studio.insynbio.com"]

    # Auth
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24

    # Database
    database_url: str = "postgresql://creative:creative@postgres:5432/creative_db"

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # Object Storage
    s3_endpoint: Optional[str] = None          # None → AWS; set for MinIO/OSS/R2
    s3_bucket: str = "creative-studio-assets"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"

    # LLM API keys
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Image models
    default_image_tier: str = "standard"  # template_only|stock|standard|premium


@lru_cache
def get_settings() -> Settings:
    return Settings()
