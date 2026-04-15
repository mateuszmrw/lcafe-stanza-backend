import io
import logging
import zipfile
from typing import List

from bs4 import BeautifulSoup
from ebooklib import ITEM_DOCUMENT, ITEM_NAVIGATION, epub
from pydantic import BaseModel

from src.domain.nlp.models import ParsedNavigationItem

logger = logging.getLogger()


class ParsedDocumentItem(BaseModel):
    text_content: str
    chapter_name: str
    spine: int
    name: str
    type: int
    xhtml_file: str | None = None


class BookParser:
    def __init__(self, import_file: str, chapter_sort_method: str):
        self.import_file = import_file
        self.chapter_sort_method = chapter_sort_method

    # Block-level tags — each becomes its own paragraph (separated by \n\n).
    _BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "section"}
    # Tags removed entirely (content discarded).
    _KILL_TAGS = {"script", "style", "head", "rp", "rt", "nav", "aside"}

    def read_epub_file(self):
        # Some EPUBs (common on macOS) store META-INF/container.xml with non-standard
        # casing (e.g. "meta-inf/container.xml"). ebooklib does a case-sensitive lookup
        # on Linux, so we normalise the ZIP entries before handing off to ebooklib.
        _EPUB_RENAMES = {
            "meta-inf/container.xml": "META-INF/container.xml",
        }
        with open(self.import_file, "rb") as fh:
            raw = fh.read()

        try:
            src_zf_check = zipfile.ZipFile(io.BytesIO(raw))
        except zipfile.BadZipFile as exc:
            raise ValueError(f"File is not a valid ZIP/EPUB archive: {exc}") from exc

        with src_zf_check as src_zf:
            all_names = [info.filename for info in src_zf.infolist()]
            logger.info("EPUB ZIP entries: %s", all_names)
            names_lower = {info.filename.lower(): info.filename for info in src_zf.infolist()}
            needs_fix = any(
                actual != canonical
                for lower, canonical in _EPUB_RENAMES.items()
                if (actual := names_lower.get(lower)) is not None
            )
            if not needs_fix:
                return epub.read_epub(self.import_file)

            logger.info("Normalising EPUB ZIP entry casing for: %s", self.import_file)
            # Rewrite the ZIP with corrected entry names into a buffer.
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as dst_zf:
                for info in src_zf.infolist():
                    data = src_zf.read(info.filename)
                    canonical = _EPUB_RENAMES.get(info.filename.lower(), info.filename)
                    dst_zf.writestr(canonical, data)
            buf.seek(0)

        return epub.read_epub(io.BytesIO(buf.read()))

    def parse_document_item(self, item, spine: int, chapter_name: str) -> ParsedDocumentItem:
        content = item.get_content().decode("utf-8", errors="replace")
        soup = BeautifulSoup(content, "html.parser")

        for tag in soup(list(self._KILL_TAGS)):
            tag.decompose()

        # Collect leaf block elements (those with no nested block descendants)
        # to avoid duplicating text from parent containers.
        blocks: list[str] = []
        for el in soup.find_all(self._BLOCK_TAGS):
            if el.find(self._BLOCK_TAGS):
                continue  # parent container — its children will be visited instead
            text = el.get_text(" ", strip=True).replace("\xa0", " ")
            if text:
                blocks.append(text)

        # Fallback: no block elements found (e.g. plain text or unusual markup).
        if not blocks:
            raw = soup.get_text(" ", strip=True).replace("\xa0", " ")
            blocks = [line.strip() for line in raw.splitlines() if line.strip()]

        text_content = "\n\n".join(blocks)
        return ParsedDocumentItem(
            text_content=text_content,
            spine=spine,
            name=item.get_name(),
            type=item.get_type(),
            chapter_name=chapter_name,
            xhtml_file=item.get_name(),
        )

    def parse_navigation_items(self, item) -> List[ParsedNavigationItem]:
        parsed_navigation_items = []
        navigation_content = item.get_content().decode()

        soup = BeautifulSoup(navigation_content, "lxml-xml")

        for nav_point in soup.find_all("navPoint"):
            chapter_name = nav_point.get_text(strip=True)
            order = int(nav_point.get("playOrder"))
            chapter_url = nav_point.find("content").get("src")
            navigation_item = ParsedNavigationItem(
                chapter_name=chapter_name, order=order, chapter_url=chapter_url
            )
            parsed_navigation_items.append(navigation_item)

        return parsed_navigation_items

    def get_sorted_pages(self, book) -> List[ParsedDocumentItem]:
        parsed_document_items = []
        parsed_navigation_items = []
        for navitagion_items in book.get_items_of_type(ITEM_NAVIGATION):
            parsed_navigation_items = self.parse_navigation_items(navitagion_items)

        nav_lookup: dict[str, str] = {}
        for nav_item in parsed_navigation_items:
            nav_lookup[nav_item.chapter_url] = nav_item.chapter_name

        current_chapter_name = "Unknown Chapter"

        for spine_index, (item_id, _) in enumerate(book.spine):
            item = book.get_item_with_id(item_id)
            if item.get_type() == ITEM_DOCUMENT:
                if item.get_name() in nav_lookup:
                    current_chapter_name = nav_lookup[item.get_name()]

                parsed_item = self.parse_document_item(
                    item, spine_index, current_chapter_name
                )
                parsed_document_items.append(parsed_item)

        return parsed_document_items

    def parse(self) -> list[ParsedDocumentItem]:
        book = self.read_epub_file()
        return self.get_sorted_pages(book)

    def detect_smil_overlays(self) -> bool:
        """Return True if this EPUB contains SMIL audio overlay files."""
        book = self.read_epub_file()
        return any(True for _ in book.get_items_of_media_type("application/smil+xml"))
