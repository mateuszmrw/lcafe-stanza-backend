import logging
from typing import List

from src.domain.models.text import ChunkedText
from src.domain.services.book_parser import ParsedDocumentItem
from src.domain.services.text_parser import TextParser

logger = logging.getLogger(__name__)


class EbookChunker:
    def __init__(self, chapters: List[ParsedDocumentItem], chunk_size: int = 3000):
        self.chapters = chapters
        self.chunk_size = chunk_size

    def chunk(self) -> List[ChunkedText]:
        result: List[ChunkedText] = []
        total_page = 1
        chapter_number = 0
        prev_chapter_name = ""
        chapter_page_number = 0
        for chapter in self.chapters:
            chunks = TextParser(chapter.text_content, self.chunk_size).parse()
            if not chunks or len(chunks) == 0:
                continue
            if chapter.chapter_name != prev_chapter_name:
                prev_chapter_name = chapter.chapter_name
                chapter_page_number = 1
                chapter_number += 1
                logger.info(
                    f"chapter: {chapter.chapter_name}, page_count: {len(chunks)}, chapter_number: {chapter_number}"
                )
            for chunk_text in chunks:
                result.append(
                    ChunkedText(
                        text=chunk_text,
                        page_number=total_page,
                        chapter_number=chapter_number,
                        chapter_page_number=chapter_page_number,
                    )
                )
                chapter_page_number += 1
                total_page += 1
        return result
