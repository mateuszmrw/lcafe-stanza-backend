from fastapi import APIRouter
from fastapi.responses import JSONResponse
from newspaper import Article

from src.api.schemas.content import (
    GetWebsiteTextRequest,
    ImportBookRequest,
    ImportTextRequest,
)
from src.domain.nlp.services import BookChunker, BookParser, TextParser

router = APIRouter(prefix="/import")


@router.post("/text")
async def import_text(request: ImportTextRequest) -> JSONResponse:
    text_parser = TextParser(request.importText, request.chunkSize)
    chunks = text_parser.parse()
    return JSONResponse(content=chunks)


@router.post("/website")
async def import_website(request: GetWebsiteTextRequest) -> JSONResponse:
    article = Article(request.url)
    article.download()
    article.parse()
    return JSONResponse(content=article.text)


@router.post("/book")
def import_book(request: ImportBookRequest) -> JSONResponse:
    book_parser = BookParser(request.importFile, request.chapterSortMethod)
    chapters = book_parser.parse()
    chunks = BookChunker(chapters, chunk_size=3000).chunk()
    epubPages = list(map(lambda item: item.text, chunks))
    return JSONResponse(content=epubPages)
