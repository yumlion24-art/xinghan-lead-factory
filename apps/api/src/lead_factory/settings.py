from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_config_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "config"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LF_",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Xinghan Lead Factory"
    environment: str = "development"
    database_url: str = "sqlite+pysqlite:///./data/lead_factory.db"
    config_dir: Path = Field(default_factory=_default_config_dir)
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    web_origin: str = "http://127.0.0.1:3000"
    log_level: str = "INFO"
    log_dir: Path = Path("./logs")
    ai_provider: str = "disabled"
    ai_model: str = "gpt-5-mini"
    ai_api_key: str | None = None
