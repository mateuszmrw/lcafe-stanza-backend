import os
from typing import AsyncGenerator

# Set required env vars BEFORE importing any src modules (engine.py calls get_settings at import time)
os.environ.setdefault("jwt_secret", "test-secret-key-for-testing-only-32ch")
os.environ.setdefault("db_encryption_key", "test-encryption-key-32chars!!!!!!")
os.environ.setdefault("db_database", "slovo_test")
os.environ.setdefault("db_host", "localhost")
os.environ.setdefault("db_port", "5432")
os.environ.setdefault("db_username", "user")
os.environ.setdefault("db_password", "password")

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import get_settings
from src.infrastructure.db.engine import Base

# Clear lru_cache so next call to get_settings() uses the env vars we just set
get_settings.cache_clear()

_TEST_DB_URL = (
    f"postgresql+asyncpg://{os.environ['db_username']}:{os.environ['db_password']}"
    f"@{os.environ['db_host']}:{os.environ['db_port']}/{os.environ['db_database']}"
)

# NullPool avoids asyncpg connections binding to a specific event loop
_engine = create_async_engine(_TEST_DB_URL, echo=False, poolclass=NullPool)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)

# Tables to truncate, ordered to respect FK constraints (children first)
_TRUNCATE_TABLES = [
    "content_pages",
    "words",
    "books",
    "content_items",
    "user_api_keys",
    "language_nlp_config",
    "users",
    "languages",
    "providers",
]


@pytest_asyncio.fixture(scope="session")
async def test_db_engine():
    """Create all tables once per session, drop them at the end."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield _engine

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await _engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_db(test_db_engine):
    """Truncate all tables before each test for isolation.
    Handles missing tables gracefully (migration tests drop tables)."""
    async with test_db_engine.connect() as conn:
        try:
            await conn.execute(
                text(f"TRUNCATE TABLE {', '.join(_TRUNCATE_TABLES)} RESTART IDENTITY CASCADE")
            )
            await conn.commit()
        except Exception:
            await conn.rollback()
            # Tables may not exist (e.g. after migration downgrade tests) — that's OK
    yield


@pytest_asyncio.fixture
async def test_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a fresh AsyncSession for each test."""
    async with _session_factory() as session:
        yield session
        await session.close()
