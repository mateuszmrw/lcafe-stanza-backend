from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_pre_ping=True,
        # Sized for a single FastAPI worker + ARQ worker pool sharing this engine.
        # Raise pool_size if you run with more uvicorn workers or bigger worker concurrency.
        pool_size=20,
        max_overflow=10,
        pool_recycle=3600,
    )


engine = _make_engine()

AsyncSessionFactory = async_sessionmaker(
    engine,
    expire_on_commit=False,
)
