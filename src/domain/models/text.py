from pydantic import BaseModel


class ChunkedText(BaseModel):
    text: str
    page_number: int
    chapter_number: int
    chapter_page_number: int


class ImportTextRequest(BaseModel):
    chunkSize: int
    importText: str


class GetWebsiteTextRequest(BaseModel):
    url: str
