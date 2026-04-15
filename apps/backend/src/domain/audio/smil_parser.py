"""SmilParser — parse EPUB3 SMIL audio overlay files.

Extracts (xhtml_file, fragment_id, audio_file, start_ms, end_ms) tuples
from all SMIL overlay files embedded in an EPUB.
"""

from __future__ import annotations

import logging
import posixpath
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup
from ebooklib import epub

logger = logging.getLogger(__name__)

_TIME_RE = re.compile(
    r"(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)"  # [H:]MM:SS[.mmm]
    r"|(\d+(?:\.\d+)?)s?"                  # SS[.mmm][s]
)


def _parse_time_ms(s: str) -> int:
    """Parse SMIL clock value to milliseconds."""
    s = s.strip()
    m = _TIME_RE.match(s)
    if not m:
        return 0
    if m.group(4) is not None:
        # plain seconds
        return int(float(m.group(4)) * 1000)
    hours = int(m.group(1) or 0)
    minutes = int(m.group(2))
    seconds = float(m.group(3))
    return int((hours * 3600 + minutes * 60 + seconds) * 1000)


@dataclass
class SmilFragment:
    xhtml_file: str   # EPUB root-relative path, e.g. "Text/chapter01.xhtml"
    fragment_id: str  # HTML element id, e.g. "sentence_001"
    audio_file: str   # EPUB root-relative path, e.g. "Audio/chapter01.mp3"
    audio_start_ms: int
    audio_end_ms: int


class SmilParser:
    def parse_epub(self, epub_path: str) -> list[SmilFragment]:
        """Return all SMIL fragments from the EPUB, in document order."""
        book = epub.read_epub(epub_path)
        fragments: list[SmilFragment] = []

        for smil_item in book.get_items_of_media_type("application/smil+xml"):
            smil_name = smil_item.get_name()  # e.g. "Text/chapter01_overlay.smil"
            smil_dir = posixpath.dirname(smil_name)
            content = smil_item.get_content().decode("utf-8", errors="replace")
            fragments.extend(self._parse_smil(content, smil_dir))

        logger.info("SmilParser: found %d fragments in %s", len(fragments), epub_path)
        return fragments

    def _parse_smil(self, content: str, smil_dir: str) -> list[SmilFragment]:
        soup = BeautifulSoup(content, "lxml-xml")
        fragments: list[SmilFragment] = []

        for par in soup.find_all("par"):
            text_el = par.find("text")
            audio_el = par.find("audio")
            if text_el is None or audio_el is None:
                continue

            text_src = text_el.get("src", "")
            audio_src = audio_el.get("src", "")
            clip_begin = audio_el.get("clipBegin", "0s")
            clip_end = audio_el.get("clipEnd", "0s")

            if "#" not in text_src:
                continue

            xhtml_rel, fragment_id = text_src.split("#", 1)
            xhtml_file = posixpath.normpath(posixpath.join(smil_dir, xhtml_rel))
            audio_file = posixpath.normpath(posixpath.join(smil_dir, audio_src))

            fragments.append(
                SmilFragment(
                    xhtml_file=xhtml_file,
                    fragment_id=fragment_id,
                    audio_file=audio_file,
                    audio_start_ms=_parse_time_ms(clip_begin),
                    audio_end_ms=_parse_time_ms(clip_end),
                )
            )

        return fragments

    def list_audio_files(self, epub_path: str) -> list[str]:
        """Return sorted unique EPUB-root-relative audio file paths referenced by SMIL."""
        fragments = self.parse_epub(epub_path)
        seen: set[str] = set()
        result: list[str] = []
        for f in fragments:
            if f.audio_file not in seen:
                seen.add(f.audio_file)
                result.append(f.audio_file)
        return result
