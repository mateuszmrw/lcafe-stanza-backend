from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.infrastructure.db.models.system_api_keys import SystemApiKey


class SystemApiKeyRepository:
    async def upsert(
        self,
        session: AsyncSession,
        provider_id: uuid.UUID,
        plaintext_key: str,
        model: str | None = None,
    ) -> None:
        passphrase = get_settings().db_encryption_key
        await session.execute(
            sa.text(
                """
                INSERT INTO system_api_keys (provider_id, api_key_encrypted, model)
                VALUES (:provider_id, pgp_sym_encrypt(:key, :passphrase), :model)
                ON CONFLICT (provider_id)
                DO UPDATE SET
                    api_key_encrypted = pgp_sym_encrypt(:key, :passphrase),
                    model = COALESCE(:model, system_api_keys.model),
                    updated_at = now()
                """
            ).bindparams(
                provider_id=provider_id,
                key=plaintext_key,
                passphrase=passphrase,
                model=model,
            )
        )

    async def update_model(
        self,
        session: AsyncSession,
        provider_id: uuid.UUID,
        model: str,
    ) -> bool:
        """Update only the model on an existing row. Returns False if no row exists."""
        result = await session.execute(
            sa.text(
                """
                UPDATE system_api_keys
                SET model = :model, updated_at = now()
                WHERE provider_id = :provider_id
                """
            ).bindparams(provider_id=provider_id, model=model)
        )
        return result.rowcount > 0  # type: ignore[union-attr]

    async def get_model(
        self,
        session: AsyncSession,
        provider_id: uuid.UUID,
    ) -> str | None:
        result = await session.execute(
            sa.text(
                "SELECT model FROM system_api_keys WHERE provider_id = :provider_id"
            ).bindparams(provider_id=provider_id)
        )
        row = result.one_or_none()
        return row.model if row else None

    async def get_decrypted(
        self,
        session: AsyncSession,
        provider_id: uuid.UUID,
    ) -> str | None:
        passphrase = get_settings().db_encryption_key
        result = await session.execute(
            sa.text(
                """
                SELECT pgp_sym_decrypt(api_key_encrypted, :passphrase) AS api_key
                FROM system_api_keys
                WHERE provider_id = :provider_id
                """
            ).bindparams(passphrase=passphrase, provider_id=provider_id)
        )
        row = result.one_or_none()
        return row.api_key if row else None

    async def exists(self, session: AsyncSession, provider_id: uuid.UUID) -> bool:
        result = await session.scalar(
            sa.select(sa.func.count()).select_from(SystemApiKey).where(
                SystemApiKey.provider_id == provider_id
            )
        )
        return (result or 0) > 0

    async def delete(self, session: AsyncSession, provider_id: uuid.UUID) -> None:
        await session.execute(
            sa.delete(SystemApiKey).where(SystemApiKey.provider_id == provider_id)
        )
