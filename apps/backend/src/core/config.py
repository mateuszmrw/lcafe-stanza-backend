from functools import lru_cache
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_MIN_SECRET_LEN = 32


class Settings(BaseSettings):
    project_name: str = "Slovo Backend"
    debug: bool = False
    languages: list[str] = []  # extra Stanza models to pre-load beyond the 5 defaults
    use_gpu: bool = False
    model_dir: str = "stanza_resources"
    jwt_secret: str
    # JWT algorithm is hardcoded to HS256 — no practical reason to make it configurable.
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 31
    db_encryption_key: str
    storage_root: str = "/app/storage"
    redis_url: str = "redis://redis:6379"

    # File upload limit — protects against OOM from large uploads
    max_upload_bytes: int = 500 * 1024 * 1024  # 500 MB

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_database: str = "db"
    db_username: str = "user"
    db_password: str = "password"

    deepl_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-5.4-mini"
    claude_api_key: Optional[str] = None
    claude_model: str = "claude-sonnet-4-6"
    admin_email: Optional[str] = None
    admin_password: Optional[str] = None

    # TTS
    qwen_tts_url: Optional[str] = None
    qwen_tts_api_key: Optional[str] = None

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
                f"Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        if len(self.db_encryption_key) < _MIN_SECRET_LEN:
            raise ValueError(
                f"db_encryption_key must be at least {_MIN_SECRET_LEN} characters. "
                f"Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
