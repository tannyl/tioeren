"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = "postgresql://tioeren:tioeren@localhost:5432/tioeren"

    # Security
    SECRET_KEY: str = "change-this-in-production-to-a-secure-random-key"

    # Application
    DEBUG: bool = True
    TESTING: bool = False  # Set to True in test environment to disable secure cookies

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
