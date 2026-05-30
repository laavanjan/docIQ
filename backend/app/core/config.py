"""Application configuration loaded from environment variables / `.env`.

All settings are centralised here so the rest of the codebase imports a single
`settings` object. See ``docs/CONFIGURATION.md`` for an explanation of each value.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- App ----
    app_name: str = "Document Analysis Platform"
    environment: Literal["development", "production", "test"] = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    # Comma-separated string in the environment; use `cors_origins_list` in code.
    cors_origins: str = "http://localhost:3000"

    # ---- Database ----
    database_url: str = (
        "postgresql+psycopg://docanalysis:docanalysis@localhost:5432/docanalysis"
    )

    # ---- Auth / JWT ----
    jwt_secret: str = "change-me-please-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    # Comma-separated string; use `api_keys_list` in code. Empty => X-API-Key disabled.
    api_keys: str = ""

    # ---- LLM providers ----
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"
    llm_primary: Literal["anthropic", "openai"] = "anthropic"
    llm_fallback_enabled: bool = True
    llm_max_tokens: int = 2048
    # Omitted from API calls when None (default). Some newer Claude/OpenAI models reject a
    # custom temperature, so we only send it if explicitly configured.
    llm_temperature: float | None = None

    # ---- Embeddings ----
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384

    # ---- RAG ----
    retrieval_top_k: int = 5
    chunk_size: int = 1000
    chunk_overlap: int = 150

    # ---- Document extraction ----
    upload_dir: str = "./data/uploads"
    max_upload_mb: int = 25
    tesseract_cmd: str | None = None
    poppler_path: str | None = None
    yolo_enabled: bool = True
    yolo_model_path: str = "yolov8n.pt"
    ocr_dpi: int = 200
    vision_dpi: int = 150
    # Extract embedded raster images from PDFs so the chat can surface figures from cited pages.
    extract_images: bool = True
    image_min_dimension: int = 64  # skip images smaller than this (icons/artifacts)

    # ---- Logging ----
    log_level: str = "INFO"
    log_dir: str = "./logs"
    log_json: bool = False

    # ---- Derived helpers ----
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def api_keys_list(self) -> list[str]:
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read once per process)."""
    return Settings()


settings = get_settings()
