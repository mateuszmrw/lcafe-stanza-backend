"""
Alembic migration tests.

These tests run alembic upgrade/downgrade against slovo_test DB.
They require PostgreSQL to be running (docker compose up).
Marked with @pytest.mark.migration so they can be skipped in fast runs:
  uv run pytest -m "not migration"
"""
import os
import subprocess

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

# alembic env.py reads get_settings().database_url so these env vars
# propagate to the alembic subprocess automatically
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_URL = (
    f"postgresql+asyncpg://{os.environ.get('db_username', 'user')}"
    f":{os.environ.get('db_password', 'password')}"
    f"@{os.environ.get('db_host', 'localhost')}"
    f":{os.environ.get('db_port', '5432')}"
    f"/{os.environ.get('db_database', 'slovo_test')}"
)


def _run_alembic(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["uv", "run", "alembic", *args],
        cwd=_BACKEND_DIR,
        capture_output=True,
        text=True,
        env={**os.environ},
    )


async def _get_table_names() -> list[str]:
    engine = create_async_engine(_DB_URL, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public' AND tablename != 'alembic_version'"
                )
            )
            return [row[0] for row in result]
    finally:
        await engine.dispose()


async def _drop_all(engine):
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "DO $$ DECLARE r RECORD; "
                "BEGIN FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname='public') "
                "LOOP EXECUTE 'DROP TABLE IF EXISTS \"' || r.tablename || '\" CASCADE'; "
                "END LOOP; END $$;"
            )
        )


@pytest.mark.migration
class TestAlembicMigrations:
    """Test that Alembic migrations run cleanly on a blank database."""

    @pytest.mark.asyncio
    async def test_migrations_up_creates_tables(self, test_db_engine):
        """Test alembic upgrade head creates all expected tables."""
        # Start clean
        await _drop_all(test_db_engine)

        result = _run_alembic("upgrade", "head")
        assert result.returncode == 0, f"Alembic upgrade failed:\n{result.stderr}"

        tables = await _get_table_names()
        expected = [
            "providers", "languages", "language_nlp_config",
            "users", "user_api_keys",
            "content_items", "books", "content_pages",
            "words",
        ]
        for tbl in expected:
            assert tbl in tables, f"Table '{tbl}' missing after upgrade head"

    @pytest.mark.asyncio
    async def test_migrations_down_removes_tables(self, test_db_engine):
        """Test alembic downgrade base removes all app tables."""
        # Ensure we're at head first
        _run_alembic("upgrade", "head")

        result = _run_alembic("downgrade", "base")
        assert result.returncode == 0, f"Alembic downgrade failed:\n{result.stderr}"

        tables = await _get_table_names()
        assert tables == [], f"Tables remain after downgrade base: {tables}"

    @pytest.mark.asyncio
    async def test_migrations_up_down_up_cycle(self, test_db_engine):
        """Test full up/down/up cycle runs cleanly."""
        await _drop_all(test_db_engine)

        r1 = _run_alembic("upgrade", "head")
        assert r1.returncode == 0, f"First upgrade failed:\n{r1.stderr}"

        r2 = _run_alembic("downgrade", "base")
        assert r2.returncode == 0, f"Downgrade failed:\n{r2.stderr}"

        r3 = _run_alembic("upgrade", "head")
        assert r3.returncode == 0, f"Second upgrade failed:\n{r3.stderr}"

        tables = await _get_table_names()
        expected = ["providers", "languages", "users", "content_items", "words"]
        for tbl in expected:
            assert tbl in tables, f"Table '{tbl}' missing after up/down/up cycle"
