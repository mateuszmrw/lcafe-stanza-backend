from fastapi import Depends, Body
from src.core import get_settings
from src.domain.services.tokenizer import Tokenizer
from src.infrastructure.external.stanza_client import StanzaClient, StanzaConfig, get_stanza_client

def get_stanza_client_dependency():
    settings = get_settings()
    return get_stanza_client(StanzaConfig(languages=settings.languages, model_dir=settings.model_dir))

def get_tokenizer(stanza_client: StanzaClient = Depends(get_stanza_client_dependency), raw_text: str | list[str] = Body(...), language: str = Body(...)) -> Tokenizer:
    return Tokenizer(text=raw_text, language=language, stanza_client=stanza_client) 