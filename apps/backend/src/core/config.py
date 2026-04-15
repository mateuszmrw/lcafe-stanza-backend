from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
