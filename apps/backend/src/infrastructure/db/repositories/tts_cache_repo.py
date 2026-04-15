from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.tts import TtsSentenceCache


class TtsCacheRepository:
    async def get_cached(
        self,
        session: AsyncSession,
        language_code: str,
        text_hash: str,
    ) -> TtsSentenceCache | None:
        result = await session.execute(
            sa.select(TtsSentenceCache).where(
                TtsSentenceCache.language_code == language_code,
                TtsSentenceCache.text_hash == text_hash,
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        session: AsyncSession,
        language_code: str,
        text_hash: str,
        audio_file: str,
        duration_ms: int,
    ) -> None:
        stmt = pg_insert(TtsSentenceCache).values(
            id=uuid.uuid4(),
            language_code=language_code,
            text_hash=text_hash,
            audio_file=audio_file,
            duration_ms=duration_ms,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_tts_sentence_cache",
            set_={
                "audio_file": stmt.excluded.audio_file,
                "duration_ms": stmt.excluded.duration_ms,
            },
        )
        await session.execute(stmt)
