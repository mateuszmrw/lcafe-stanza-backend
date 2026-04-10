from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from functools import lru_cache

import jwt
import sqlalchemy as sa
from arq import ArqRedis, create_pool
from arq.connections import RedisSettings
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import get_settings
from src.domain.auth.services.jwt import decode_token
from src.domain.nlp.models.token import Token
from src.domain.nlp.services.tokenizer import Tokenizer
from src.domain.ports.nlp_port import NlpPort
from src.infrastructure.db import AsyncSessionFactory
from src.infrastructure.db.models.languages import LanguageNlpConfig
from src.infrastructure.db.models.providers import Provider
from src.infrastructure.db.models.users import User
from src.infrastructure.stanza.adapter import StanzaNlpAdapter
from src.infrastructure.stanza.client import (
    StanzaClient,
    StanzaConfig,
    get_stanza_client,
)

_bearer_scheme = HTTPBearer(auto_error=False)
_arq_pool: ArqRedis | None = None
_redis_conn: Redis | None = None


@lru_cache()
def get_stanza_client_dependency() -> StanzaClient:
    settings = get_settings()
    config = StanzaConfig(
        languages=settings.languages,
        model_dir=settings.model_dir,
        use_gpu=settings.use_gpu,
    )
    return get_stanza_client(config)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        yield session


async def get_arq_pool() -> ArqRedis:
    global _arq_pool
    if _arq_pool is None:
        settings = get_settings()
        _arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    return _arq_pool


async def get_redis() -> Redis:
    global _redis_conn
    if _redis_conn is None:
        settings = get_settings()
        _redis_conn = Redis.from_url(settings.redis_url)
    return _redis_conn


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = await session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def get_nlp_adapter(
    language_id: int,
    session: AsyncSession = Depends(get_db),
    stanza_client: StanzaClient = Depends(get_stanza_client_dependency),
) -> NlpPort:
    result = await session.execute(
        sa.select(LanguageNlpConfig, Provider)
        .join(Provider, LanguageNlpConfig.provider_id == Provider.id)
        .where(LanguageNlpConfig.language_id == language_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"NLP config not found for language_id={language_id}",
        )

    nlp_config, provider = row

    if provider.slug == "stanza":
        stanza_lang: str = nlp_config.config.get("stanza_language_name", "english")
        return StanzaNlpAdapter(stanza_client, stanza_lang)

    raise HTTPException(
        status_code=400, detail=f"Provider '{provider.slug}' is not supported"
    )


class _StanzaNlpBridge(NlpPort):
    """Temporary bridge from StanzaClient to NlpPort for legacy NLP routes."""

    def __init__(self, client: StanzaClient) -> None:
        self._client = client

    def tokenize(self, text: str | list[str], language: str) -> list[Token]:
        pipeline = self._client.get_pipeline(language)
        texts = [text] if isinstance(text, str) else text
        tokens: list[Token] = []
        for t in texts:
            doc = pipeline(t)
            for i, sentence in enumerate(doc.sentences):
                for word in sentence.words:
                    tokens.append(
                        Token(
                            w=word.text,
                            r="",
                            l=word.lemma or "",
                            lr="",
                            pos=word.upos or "",
                            si=i,
                            g=_extract_gender(word.feats),
                        )
                    )
        return tokens


def _extract_gender(feats: str | None) -> str:
    if not feats:
        return ""
    for feat in feats.split("|"):
        if feat.startswith("Gender="):
            return feat.split("=")[1]
    return ""


def get_tokenizer(
    stanza_client: StanzaClient = Depends(get_stanza_client_dependency),
) -> Tokenizer:
    return Tokenizer(nlp_port=_StanzaNlpBridge(stanza_client))
