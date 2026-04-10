from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse

from src.api.dependencies import get_tokenizer
from src.domain.nlp.services.tokenizer import Tokenizer

router = APIRouter(prefix="/nlp")


@router.post("/tokenize")
def tokenize(
    raw_text: str | list[str] = Body(...),
    language: str = Body(...),
    tokenizer: Tokenizer = Depends(get_tokenizer),
) -> JSONResponse:
    tokens = tokenizer.tokenize(raw_text, language)
    return JSONResponse(content=[t.model_dump() for t in tokens])
