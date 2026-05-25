"""Configuration management for SinoQuantis."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and optional .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    tushare_token: str | None = None
    deepseek_api_key: str | None = None
    sinoquantis_db_path: Path = Path("data/quant.duckdb")
    sinoquantis_data_dir: Path = Path("data")
    sinoquantis_deepseek_model: str = "deepseek-chat"


def get_settings() -> Settings:
    """Return application settings."""
    return Settings()
