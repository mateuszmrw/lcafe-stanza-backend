import re

import lxml.html
import lxml_html_clean
from ebooklib import ITEM_DOCUMENT, ITEM_NAVIGATION, epub


class BookParser:
    def __init__(self, import_file: str, chapter_sort_method: str):
        self.import_file = import_file
        self.chapter_sort_method = chapter_sort_method

    def get_sorted_pages(self) -> list[any]:
        book = epub.read_epub(self.import_file)

        document_items = []
        navigation_items = []

        for item in book.get_items():
            if item.get_type() == ITEM_DOCUMENT:
                document_items.append(item)
            if item.get_type() == ITEM_NAVIGATION:
                navigation_items.append(item)

        print(len(navigation_items))
        print(navigation_items)
        return document_items

    def parse(self) -> str:
        html_cleaner = lxml_html_clean.Cleaner(
            allow_tags=[""],
            remove_unknown_tags=False,
            kill_tags=["rp", "rt"],
            page_structure=False,
        )
        book_content = ""
        sorted_pages = self.get_sorted_pages()

        for item in sorted_pages:
            if item.get_type() == ITEM_DOCUMENT:
                content_str = item.get_content().decode()
                content_str = re.sub(r"<\?xml[^>]+\?>", "", content_str, count=1)
                cleanHtmlEpubPage = html_cleaner.clean_html(content_str)
                epubPage = lxml.html.fromstring(cleanHtmlEpubPage).text_content()
                book_content += epubPage

        return str(book_content)
