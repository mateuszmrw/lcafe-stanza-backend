from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from newspaper import Article

from src.api.dependencies import get_tokenizer
from src.domain import TextParser, Tokenizer
from src.domain.models.book import ImportBookRequest
from src.domain.models.text import GetWebsiteTextRequest, ImportTextRequest
from src.domain.services.book_chunker import EbookChunker
from src.domain.services.book_parser import BookParser

router = APIRouter()


@router.post("/tokenizer")
def tokenize(tokenizer: Tokenizer = Depends(get_tokenizer)) -> JSONResponse:
    tokens = tokenizer.tokenize()
    return JSONResponse(content=tokens)


@router.post("/tokenizer/import-text")
async def import_text(request: ImportTextRequest) -> JSONResponse:
    text_parser = TextParser(request.importText, request.chunkSize)
    chunks = text_parser.parse()
    return JSONResponse(content=chunks)


@router.post("/tokenizer/get-website-text")
async def get_website_text(request: GetWebsiteTextRequest) -> JSONResponse:
    article = Article(request.url)
    article.download()
    article.parse()
    return JSONResponse(content=article.text)


@router.post("/tokenizer/import-book")
def import_book(request: ImportBookRequest) -> JSONResponse:
    book_parser = BookParser(request.importFile, request.chapterSortMethod)
    chapters = book_parser.parse()
    chunks = EbookChunker(chapters, chunk_size=3000).chunk()
    epubPages = list(map(lambda item: item.text, chunks))
    return JSONResponse(content=epubPages)
