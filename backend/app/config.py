"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed runtime configuration for GoldProof backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "GoldProof API"
    APP_VERSION: str = "1.0.0"

    DATABASE_URL: str = "sqlite:///./goldproof_dev.db"

    JWT_SECRET: str = "goldproof-local-dev-secret-change-me-2026-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 720

    ED25519_PRIVATE_KEY_B64: str = ""
    DEV_KEY_DIR: str = str(Path(__file__).resolve().parent.parent / ".keys")

    APP_PUBLIC_URL: str = "http://localhost:3000"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    DEMO_MODE: bool = True

    LLM_PROVIDER: str = "local_evidence_explainer"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"

    OCR_PROVIDER: str = "auto"
    SPEECH_PROVIDER: str = "browser_web_speech"
    SPEECH_API_KEY: str = ""

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
