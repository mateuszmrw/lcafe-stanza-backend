"""FragmentResolver — resolve (xhtml_file, fragment_id) → element text.

Opens the EPUB zip and looks up the HTML element with the given id,
returning its plain-text content for sentence matching.
"""

from __future__ import annotations

import logging
import zipfile

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


_INVISIBLE_CHARS = str.maketrans("", "", "\u00AD\u200B\u200C\u200D\u2060\uFEFF")


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
        """Parse an XHTML file and return a mapping of element id → stripped text."""
        content = self._read_xhtml(xhtml_file)
        if content is None:
            return {}

        soup = BeautifulSoup(content, "html.parser")
        index: dict[str, str] = {}
        for el in soup.find_all(id=True):
            el_id = el.get("id")
            if el_id:
                # Match BookParser: empty separator so intra-word inline spans
                # (drop-caps, styled letter fragments) don't fuse with spaces
                # and mis-align sentence matching against the tokenized text.
                for br in el.find_all("br"):
                    br.replace_with("\n")
                text = el.get_text(strip=True).replace("\xa0", " ").translate(_INVISIBLE_CHARS)
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
