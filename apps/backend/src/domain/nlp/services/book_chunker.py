import logging
from typing import List

from src.domain.nlp.models import ChunkedText

from .book_parser import ParsedDocumentItem
from .text_parser import TextParser

logger = logging.getLogger(__name__)


class BookChunker:
    def __init__(self, chapters: List[ParsedDocumentItem], chunk_size: int = 3000):
        self.chapters = chapters
        self.chunk_size = chunk_size

    def chunk(self) -> List[ChunkedText]:
        """Flatten chapters into pages. Each parsed document item is its own
        chapter — we do NOT merge consecutive items sharing the same name,
        because books often have repeated "Untitled Chapter" labels for
        structurally distinct chapters.
        """
        result: List[ChunkedText] = []
        total_page = 1
        chapter_number = 0
        for chapter in self.chapters:
            chunks = TextParser(chapter.text_content, self.chunk_size).parse()
            if not chunks:
                continue
            chapter_number += 1
            logger.info(
                "chapter: %s, page_count: %d, chapter_number: %d",
                chapter.chapter_name, len(chunks), chapter_number,
            )
            for chapter_page_number, chunk_text in enumerate(chunks, start=1):
                result.append(
                    ChunkedText(
                        text=chunk_text,
                        page_number=total_page,
                        chapter_number=chapter_number,
                        chapter_page_number=chapter_page_number,
                        chapter_name=chapter.chapter_name or None,
                        xhtml_file=chapter.xhtml_file,
                    )
                )
                total_page += 1
        return result
