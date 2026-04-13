import logging

from pypdf import PdfReader

from .book_parser import ParsedDocumentItem

logger = logging.getLogger(__name__)


class PdfParser:
    def __init__(self, import_file: str):
        self.import_file = import_file

    def parse(self) -> list[ParsedDocumentItem]:
        reader = PdfReader(self.import_file)
        items: list[ParsedDocumentItem] = []

        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            text = text.strip()
            if not text:
                continue

            items.append(
                ParsedDocumentItem(
                    text_content=text,
                    chapter_name=f"Page {i + 1}",
                    spine=i,
                    name=f"page_{i + 1}",
                    type=0,
                )
            )

        logger.info("PDF parsed: %d non-empty pages from %s", len(items), self.import_file)
        return items
