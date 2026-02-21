from fastapi import APIRouter
from fastapi.responses import JSONResponse
from newspaper import Article

from src.api.schemas.content import GetWebsiteTextRequest, ImportBookRequest, ImportTextRequest
from src.domain.nlp.services.book_chunker import BookChunker
from src.domain.nlp.services.book_parser import BookParser
from src.domain.nlp.services.text_parser import TextParser

router = APIRouter()


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
    chunks = BookChunker(chapters, chunk_size=3000).chunk()
    epubPages = list(map(lambda item: item.text, chunks))
    return JSONResponse(content=epubPages)
