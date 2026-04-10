from pydantic import BaseModel


class ParsedNavigationItem(BaseModel):
    chapter_name: str
    order: int
    chapter_url: str


class ChunkedText(BaseModel):
    text: str
    page_number: int
    chapter_number: int
    chapter_page_number: int
    chapter_name: str | None = None
