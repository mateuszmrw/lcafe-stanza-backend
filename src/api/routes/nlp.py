from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.api.dependencies import get_tokenizer
from src.domain.nlp.services.tokenizer import Tokenizer

router = APIRouter()


@router.post("/tokenizer")
def tokenize(tokenizer: Tokenizer = Depends(get_tokenizer)) -> JSONResponse:
    tokens = tokenizer.tokenize()
    return JSONResponse(content=tokens)
