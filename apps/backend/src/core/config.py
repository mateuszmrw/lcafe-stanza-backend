from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_MIN_SECRET_LEN = 32


class Settings(BaseSettings):
    project_name: str = "Slovo Backend"
    debug: bool = False
    load_stanza: bool = True  # set false on the API container; worker always keeps true
    languages: list[str] = []  # extra Stanza models to pre-load beyond the 5 defaults
    coref_enabled_languages: list[str] = Field(default_factory=list)

    @field_validator("coref_enabled_languages", mode="before")
    @classmethod
    def _parse_coref_langs(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [lang.strip() for lang in v.split(",") if lang.strip()]
        return v or []
    use_gpu: bool = False
    model_dir: str = "stanza_resources"
    jwt_secret: str
    # JWT algorithm is hardcoded to HS256 — no practical reason to make it configurable.
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 31
    db_encryption_key: str
    storage_root: str = "/app/storage"
    redis_url: str = "redis://redis:6379"

    # Per-feature upload size caps — protect against OOM from oversized uploads.
    # Each is overridable via its own env var so operators can tune them per
    # deployment without cross-feature trade-offs. Endpoints without a
    # dedicated cap fall back to `max_upload_bytes`.
    max_upload_bytes: int = 100 * 1024 * 1024              # 100 MB — generic fallback (SRT subtitles, frequency CSVs)
    max_book_upload_bytes: int = 500 * 1024 * 1024         # 500 MB — EPUB/PDF uploads
    max_dictionary_upload_bytes: int = 2 * 1024 * 1024 * 1024  # 2 GB — Wiktionary / dictionary dumps
    # Raise to 300+ when coref is enabled on CPU (XLM-RoBERTa inference is slow).
    tokenize_page_timeout_seconds: int = 60

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_database: str = "db"
    db_username: str = "user"
    db_password: str = "password"

    deepl_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-5.4-mini"

    # TTS — any server that implements the OpenAI POST /v1/audio/speech API
    openai_tts_url: Optional[str] = None
    openai_tts_api_key: Optional[str] = None
    openai_tts_model: str = "qwen3-tts"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_username}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_database}"
        )

    # Env vars are UPPERCASE by convention (Docker Compose, k8s, shell exports).
    # Field names are lowercase Python-style; pydantic-settings uppercases them
    # before matching env vars when case_sensitive is False.
    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=".env",
        extra="ignore",
    )

    @model_validator(mode="after")
    def _validate_secrets(self) -> "Settings":
        """Fail fast at startup if required secrets are missing or too short.

        A short jwt_secret makes HS256 tokens brute-forceable. A short
        db_encryption_key weakens pgp_sym_encrypt for stored API keys.
        """
        if len(self.jwt_secret) < _MIN_SECRET_LEN:
            raise ValueError(
                f"jwt_secret must be at least {_MIN_SECRET_LEN} characters. "
                f"Generate one with: openssl rand -base64 32"
            )
        if len(self.db_encryption_key) < _MIN_SECRET_LEN:
            raise ValueError(
                f"db_encryption_key must be at least {_MIN_SECRET_LEN} characters. "
                f"Generate one with: openssl rand -base64 32"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
