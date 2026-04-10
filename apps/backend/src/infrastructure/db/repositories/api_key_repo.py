from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.infrastructure.db.models.user_api_keys import UserApiKey


class ApiKeyRepository:
    async def upsert(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        provider_id: uuid.UUID,
        plaintext_key: str,
    ) -> None:
        """Encrypt and store the API key using pgp_sym_encrypt."""
        passphrase = get_settings().db_encryption_key
        await session.execute(
            sa.text(
                """
                INSERT INTO user_api_keys (user_id, provider_id, api_key_encrypted)
                VALUES (:user_id, :provider_id, pgp_sym_encrypt(:key, :passphrase))
                ON CONFLICT (user_id, provider_id)
                DO UPDATE SET
                    api_key_encrypted = pgp_sym_encrypt(:key, :passphrase),
                    updated_at = now()
                """
            ).bindparams(
                user_id=user_id,
                provider_id=provider_id,
                key=plaintext_key,
                passphrase=passphrase,
            )
        )

    async def get_decrypted(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        provider_id: uuid.UUID,
    ) -> str | None:
        """Decrypt and return the stored API key, or None if not found."""
        passphrase = get_settings().db_encryption_key
        result = await session.execute(
            sa.text(
                """
                SELECT pgp_sym_decrypt(api_key_encrypted, :passphrase) AS api_key
                FROM user_api_keys
                WHERE user_id = :user_id AND provider_id = :provider_id
                """
            ).bindparams(
                passphrase=passphrase,
                user_id=user_id,
                provider_id=provider_id,
            )
        )
        row = result.one_or_none()
        return row.api_key if row else None

    async def delete(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        provider_id: uuid.UUID,
    ) -> None:
        await session.execute(
            sa.delete(UserApiKey).where(
                UserApiKey.user_id == user_id,
                UserApiKey.provider_id == provider_id,
            )
        )
