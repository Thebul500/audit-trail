"""Application configuration from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    database_url: str = "sqlite+aiosqlite:///./audit_trail.db"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30
    debug: bool = False

    model_config = {"env_prefix": "AUDIT_TRAIL_"}


settings = Settings()
