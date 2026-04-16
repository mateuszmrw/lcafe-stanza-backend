"""FragmentResolver — resolve (xhtml_file, fragment_id) → element text.

Opens the EPUB zip and looks up the HTML element with the given id,
returning its plain-text content for sentence matching.
"""

from __future__ import annotations

import logging
import zipfile

from bs4 import BeautifulSoup

from src.domain.nlp.services.book_parser import BookParser

logger = logging.getLogger(__name__)


class FragmentResolver:
    def __init__(self, epub_path: str) -> None:
        self._epub_path = epub_path
        self._cache: dict[str, dict[str, str]] = {}  # xhtml_file → {id: text}

    def resolve_text(self, xhtml_file: str, fragment_id: str) -> str | None:
        """Return the text of the element identified by fragment_id in xhtml_file."""
        if xhtml_file not in self._cache:
            self._cache[xhtml_file] = self._index_xhtml(xhtml_file)
        return self._cache[xhtml_file].get(fragment_id)

    def _index_xhtml(self, xhtml_file: str) -> dict[str, str]:
        """Parse an XHTML file and return a mapping of element id → stripped text.

        Uses BookParser.extract_element_text so SMIL fragment text and page
        text normalise identically — divergence here causes "DlaCamerona"
        style fusion that breaks substring matching in _find_sentence.
        """
        content = self._read_xhtml(xhtml_file)
        if content is None:
            return {}

        soup = BeautifulSoup(content, "html.parser")
        index: dict[str, str] = {}
        for el in soup.find_all(id=True):
            el_id = el.get("id")
            if el_id:
                for br in el.find_all("br"):
                    br.replace_with("\n")
                text = BookParser.extract_element_text(el)
                if text:
                    index[el_id] = text
        return index

    def _read_xhtml(self, xhtml_file: str) -> bytes | None:
        candidates = [
            xhtml_file,
            f"OEBPS/{xhtml_file}",
            f"OPS/{xhtml_file}",
        ]
        try:
            with zipfile.ZipFile(self._epub_path, "r") as zf:
                names_lower = {n.lower(): n for n in zf.namelist()}
                for candidate in candidates:
                    if candidate in zf.namelist():
                        return zf.read(candidate)
                    actual = names_lower.get(candidate.lower())
                    if actual:
                        return zf.read(actual)
        except Exception as exc:
            logger.warning("FragmentResolver: could not read %s: %s", xhtml_file, exc)
        return None
