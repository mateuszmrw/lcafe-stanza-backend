import logging
import re
from typing import List

import lxml.html
import lxml_html_clean
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


class BookParser:
    def __init__(self, import_file: str, chapter_sort_method: str):
        self.import_file = import_file
        self.chapter_sort_method = chapter_sort_method

    def read_epub_file(self):
        return epub.read_epub(self.import_file)

    def get_html_cleaner(self) -> lxml_html_clean.Cleaner:
        return lxml_html_clean.Cleaner(
            allow_tags=[""],
            remove_unknown_tags=False,
            kill_tags=["rp", "rt"],
            page_structure=False,
        )

    def parse_document_item(
        self, item, spine: int, chapter_name: str
    ) -> ParsedDocumentItem:
        html_cleaner = self.get_html_cleaner()
        content_str = item.get_content().decode()
        content_str = re.sub(r"<\?xml[^>]+\?>", "", content_str, count=1)
        cleanHtmlEpubPage = html_cleaner.clean_html(content_str)
        text_content = str(lxml.html.fromstring(cleanHtmlEpubPage).text_content())
        return ParsedDocumentItem(
            text_content=text_content,
            spine=spine,
            name=item.get_name(),
            type=item.get_type(),
            chapter_name=chapter_name,
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
                # If no match, then inherit previous chapter name
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
