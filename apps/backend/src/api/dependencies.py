from functools import lru_cache

from fastapi import Body, Depends

from src.core import get_settings
from src.domain.nlp.services.tokenizer import Tokenizer
from src.infrastructure.stanza.client import (
    StanzaClient,
    StanzaConfig,
    get_stanza_client,
)


@lru_cache
def get_stanza_client_dependency():
    settings = get_settings()
    config = StanzaConfig(
        languages=settings.languages,
        model_dir=settings.model_dir,
        use_gpu=settings.use_gpu,
    )
    return get_stanza_client(config)


def get_tokenizer(
    stanza_client: StanzaClient = Depends(get_stanza_client_dependency),
    raw_text: str | list[str] = Body(...),
    language: str = Body(...),
) -> Tokenizer:
    return Tokenizer(text=raw_text, language=language, stanza_client=stanza_client)
