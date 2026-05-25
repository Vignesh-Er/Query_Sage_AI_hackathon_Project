import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    QUERYSAGE_DB_PATH: str = str(Path.home() / ".querysage" / "querysage.db")
    QUERYSAGE_AI_PROVIDER: str = "anthropic"  # 'anthropic' or 'ollama'
    QUERYSAGE_ANTHROPIC_API_KEY: str = ""
    QUERYSAGE_ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    QUERYSAGE_OLLAMA_HOST: str = "http://localhost:11434"
    QUERYSAGE_OLLAMA_MODEL: str = "llama3"
    QUERYSAGE_HOST: str = "127.0.0.1"
    QUERYSAGE_PORT: int = 8421
    QUERYSAGE_PLAYWRIGHT_TIMEOUT: int = 30000
    QUERYSAGE_OTLP_ENDPOINT: str = "http://localhost:4317"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure ~/.querysage directory exists
os.makedirs(os.path.dirname(os.path.abspath(os.path.expanduser(settings.QUERYSAGE_DB_PATH))), exist_ok=True)
