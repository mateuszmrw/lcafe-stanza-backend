import re
from ebooklib import epub, ITEM_DOCUMENT 
import lxml_html_clean
import lxml.html
class BookParser:
    def __init__(self, import_file: str, chapter_sort_method: str):
        self.import_file = import_file
        self.chapter_sort_method = chapter_sort_method

    def get_sorted_items(self) -> list[any]:
        book = epub.read_epub(self.import_file)
        book_items = book.get_items()

        if self.chapter_sort_method == "spine":
            sorted_items = list()   
            for item in enumerate(book.spine):
                sorted_items.append(book.get_item_with_id(item[1][0]))
        else:
            sorted_items = book_items

        return sorted_items 

    def parse(self) -> str:
        html_cleaner = lxml_html_clean.Cleaner(allow_tags=[''], remove_unknown_tags=False, kill_tags = ['rp','rt'], page_structure=False)
        book_content = ""
        sorted_items = self.get_sorted_items()

        for item in sorted_items:
            if item.get_type() == ITEM_DOCUMENT:
                content_str = item.get_content().decode()
                content_str = re.sub(r'<\?xml[^>]+\?>', '', content_str, count=1)
                epubPage = html_cleaner.clean_html(content_str)
                epubPage = lxml.html.fromstring(epubPage).text_content()
                book_content += epubPage

        return str(book_content)
