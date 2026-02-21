from pydantic import BaseModel


class ImportBookRequest(BaseModel):
    chunkSize: int
    importFile: str
    chapterSortMethod: str


class ImportBookResponse(BaseModel):
    chunks: list[str]


class ParsedNavigationItem(BaseModel):
    chapter_name: str
    order: int
    chapter_url: str
