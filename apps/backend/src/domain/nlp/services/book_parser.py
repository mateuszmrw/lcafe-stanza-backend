import io
import logging
import re
import zipfile
from typing import List
from urllib.parse import unquote

from bs4 import BeautifulSoup
from ebooklib import ITEM_COVER, ITEM_DOCUMENT, ITEM_IMAGE, ITEM_NAVIGATION, epub
from pydantic import BaseModel

from src.domain.nlp.models import ParsedNavigationItem

# Collapse runs of horizontal whitespace (spaces, tabs, ZW whitespace) but
# preserve \n so <br>-induced line breaks survive for sentence segmentation.
_HSPACE_RE = re.compile(r"[^\S\n]+")
# Trim horizontal whitespace around newlines and collapse repeated newlines.
_VSPACE_RE = re.compile(r"[ \t]*\n[ \t]*")
_MULTINL_RE = re.compile(r"\n{2,}")

# Generic placeholder chapter names that carry no information for the reader
# sidebar (our own fallback plus common publisher placeholders in several
# languages). When we see one of these, we derive a preview from the content.
_GENERIC_CHAPTER_RE = re.compile(
    r"^\s*(unknown chapter|untitled|no name|bez nazwy|без названия|без назви|sin t[ií]tulo|sans titre|ohne titel|senza titolo)\b",
    re.IGNORECASE,
)
# Split point for first-sentence preview (handles Polish/European punctuation).
_SENTENCE_END_RE = re.compile(r"[.!?…]")
_PREVIEW_MAX_LEN = 50

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
    # Tags removed entirely (content discarded). `sup`/`sub` drop footnote
    # reference markers (¹, ², etc.) that would otherwise fuse to the preceding
    # word and confuse tokenization. Rare scientific notation (H₂O, x²) is a
    # known trade-off — language-learning content almost never uses it.
    # `img`/`svg`/`picture` are stripped so inline base64 data URIs (used by
    # some publishers for DRM watermarks or inline artwork) don't leak into
    # the extracted text. Actual cover images are handled separately via
    # `extract_cover_image()`.
    _KILL_TAGS = {
        "script", "style", "head", "rp", "rt", "nav", "aside", "sup", "sub",
        "img", "svg", "picture",
    }

    # Invisible characters that break tokenization if embedded mid-word:
    # soft hyphen, zero-width space/joiners, BOM, word joiner. EPUB publishers
    # use these for hyphenation hints, bidi control, or DRM watermarking.
    _INVISIBLE_CHARS = str.maketrans("", "", "\u00AD\u200B\u200C\u200D\u2060\uFEFF")

    # Filename substrings that mark cover/title pages. Covers typically wrap a
    # single <img> but sometimes carry a visible base64 DRM watermark, so we
    # skip them from tokenization entirely. Cover image display is a separate
    # feature (see .claude/specs/20260416-cover-image-display-spec.md).
    _COVER_NAME_HINTS = ("cover", "titlepage", "title-page", "title_page")

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

        # Look for an explicit heading BEFORE we mutate paragraph elements
        # below. This is the most reliable signal for the chapter title when
        # the TOC entry is a placeholder like "Bez nazwy-1".
        heading_text = self._extract_first_heading(soup)

        # Collect leaf block elements (those with no nested block descendants)
        # to avoid duplicating text from parent containers.
        blocks: list[str] = []
        for el in soup.find_all(self._BLOCK_TAGS):
            if el.find(self._BLOCK_TAGS):
                continue  # parent container — its children will be visited instead
            for br in el.find_all("br"):
                br.replace_with("\n")
            text = self._extract_text(el)
            if text:
                blocks.append(text)

        # Fallback: no block elements found (e.g. plain text or unusual markup).
        if not blocks:
            for br in soup.find_all("br"):
                br.replace_with("\n")
            raw = self._extract_text(soup)
            blocks = [line.strip() for line in raw.splitlines() if line.strip()]

        text_content = "\n\n".join(blocks)
        effective_name = self._derive_chapter_name(chapter_name, heading_text, text_content)
        return ParsedDocumentItem(
            text_content=text_content,
            spine=spine,
            name=item.get_name(),
            type=item.get_type(),
            chapter_name=effective_name,
            xhtml_file=item.get_name(),
        )

    def _derive_chapter_name(
        self, original: str, heading: str, text_content: str
    ) -> str:
        """Replace placeholder chapter names with the best available signal.

        Preference order when the TOC entry is a placeholder ("Bez nazwy-1",
        "Unknown Chapter", "Untitled", …):
          1. The document's first heading tag (<h1>…<h6>). This is the
             publisher's intended title even when it's not wired into the TOC.
          2. A truncated first-sentence preview of the body text. Useful for
             diary-style books where date headers ("CZWARTEK, 18 MAJA") sit at
             the top of each entry as styled paragraphs rather than headings.
        Legitimate chapter names are preserved verbatim.
        """
        if not original or _GENERIC_CHAPTER_RE.match(original):
            if heading:
                return self._truncate(heading)
            preview = self._first_sentence_preview(text_content)
            if preview:
                return preview
        return original

    def _extract_first_heading(self, soup) -> str:
        """Return the text of the first <h1>–<h6> in document order, if any."""
        for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            for br in el.find_all("br"):
                br.replace_with(" ")
            text = self._extract_text(el)
            if text:
                return text
        return ""

    @classmethod
    def _first_sentence_preview(cls, text: str) -> str:
        """Extract up to the first sentence (or _PREVIEW_MAX_LEN chars)."""
        # First non-empty line as a starting point — the body's opening paragraph.
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if line:
                break
        else:
            return ""

        match = _SENTENCE_END_RE.search(line)
        candidate = line[: match.start()].strip() if match else line
        return cls._truncate(candidate)

    @staticmethod
    def _truncate(text: str) -> str:
        """Clip to _PREVIEW_MAX_LEN chars at a word boundary, with ellipsis."""
        if len(text) <= _PREVIEW_MAX_LEN:
            return text
        truncated = text[:_PREVIEW_MAX_LEN].rsplit(" ", 1)[0]
        return (truncated or text[:_PREVIEW_MAX_LEN]).rstrip() + "…"

    def _extract_text(self, el) -> str:
        """Instance helper — delegates to the classmethod for backward compat."""
        return self.extract_element_text(el)

    @classmethod
    def extract_element_text(cls, el) -> str:
        """Extract plain text preserving natural whitespace.

        Uses BeautifulSoup's default ``get_text()`` (no separator, no strip) so
        the original inter-tag whitespace survives. This is the only way to
        handle both cases correctly:

          * drop-caps ``<span>J</span>akie`` — HTML has no whitespace between
            the tags, so the output is ``Jakie`` (concatenated).
          * prose ``że <i>wydziedziczam</i> Hansa`` — HTML has spaces in the
            text nodes, so the output is ``że wydziedziczam Hansa`` (spaced).

        Using ``strip=True`` would collapse the latter to ``żewydziedziczamHansa``.
        Using ``separator=" "`` would break the former to ``J akie``.

        Shared with ``FragmentResolver`` so SMIL fragment text and page text
        normalise identically — divergence here breaks audio alignment.
        """
        raw = el.get_text()
        raw = raw.replace("\xa0", " ").translate(cls._INVISIBLE_CHARS)
        # Collapse horizontal whitespace runs to a single space, then tidy
        # newlines (preserved from <br> → "\n" replacement above).
        raw = _HSPACE_RE.sub(" ", raw)
        raw = _VSPACE_RE.sub("\n", raw)
        raw = _MULTINL_RE.sub("\n", raw)
        return cls._strip_drm_watermarks(raw).strip()

    # Detects DRM / publisher watermark tokens embedded as visible text —
    # typical Polish EPUBs from Legimi / Virtualo carry a line like
    # ``= = = Lx4oECUXLxxvXGVdaVpuBDlLbl48XjoObFtpXmxeP11tWGhQYVhuXw = =``
    # at the top/bottom of the book. These aren't `<img>` tags so the
    # `_KILL_TAGS` strip does not remove them — we have to scrub them from
    # the extracted text directly.
    @classmethod
    def _is_likely_drm_token(cls, token: str) -> bool:
        """Heuristic: long token in the base64 alphabet with mixed case + digits.

        Natural-language words rarely mix case internally or embed digits,
        so this pattern is a high-precision signal for watermark tokens.
        """
        if len(token) < 24:
            return False
        if not all(c.isalnum() or c in "+/" for c in token):
            return False
        has_upper = any(c.isupper() for c in token)
        has_lower = any(c.islower() for c in token)
        has_digit = any(c.isdigit() for c in token)
        return has_upper and has_lower and has_digit

    @classmethod
    def _strip_drm_watermarks(cls, text: str) -> str:
        """Remove DRM watermark tokens and their ``=`` padding from ``text``.

        Preserves line breaks and unrelated text — if only the watermark is
        present, the line collapses to an empty string and is dropped.
        """
        kept_lines: list[str] = []
        for line in text.splitlines():
            kept_tokens: list[str] = []
            for token in line.split():
                core = token.strip("=")
                if not core:
                    # Pure "=" padding (often separated by spaces) — drop.
                    continue
                if cls._is_likely_drm_token(core):
                    continue
                kept_tokens.append(token)
            joined = " ".join(kept_tokens).strip()
            if joined:
                kept_lines.append(joined)
        return "\n".join(kept_lines)

    def _is_cover_item(self, item) -> bool:
        """Detect cover/title-page spine items that should be skipped.

        Matches on filename substring (most publishers name cover files
        ``cover.xhtml``, ``titlepage.xhtml``, etc.) and on EPUB3 manifest
        ``properties="cover-image"``. Conservative by design — only triggers
        on unambiguous cover indicators, never on content pages.
        """
        name = (item.get_name() or "").lower()
        if any(hint in name for hint in self._COVER_NAME_HINTS):
            return True
        props = getattr(item, "properties", None) or []
        if any("cover" in str(p).lower() for p in props):
            return True
        return False

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
                if self._is_cover_item(item):
                    logger.info("Skipping cover/title page from tokenization: %s", item.get_name())
                    continue

                if item.get_name() in nav_lookup:
                    current_chapter_name = nav_lookup[item.get_name()]

                parsed_item = self.parse_document_item(
                    item, spine_index, current_chapter_name
                )
                # DRM-only pages (just a watermark token) collapse to empty
                # after stripping — don't create a chapter/page for them.
                if not parsed_item.text_content.strip():
                    logger.info(
                        "Skipping empty/watermark-only document: %s",
                        item.get_name(),
                    )
                    continue
                parsed_document_items.append(parsed_item)

        return parsed_document_items

    def parse(self) -> list[ParsedDocumentItem]:
        book = self.read_epub_file()
        return self.get_sorted_pages(book)

    def detect_smil_overlays(self) -> bool:
        """Return True if this EPUB contains SMIL audio overlay files."""
        book = self.read_epub_file()
        return any(True for _ in book.get_items_of_media_type("application/smil+xml"))

    # Map EPUB image media types to the file extension we use on disk.
    _COVER_EXT_BY_MEDIA_TYPE = {
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/gif": "gif",
    }

    def extract_cover_image(self) -> tuple[str, bytes] | None:
        """Locate the book's cover image and return ``(media_type, bytes)``.

        Resolution order follows the EPUB specs, falling back to the HTML
        cover page as a last resort:

          1. EPUB3 — manifest item with ``properties="cover-image"`` (ebooklib
             surfaces these as ``ITEM_COVER`` with an ``image/*`` media type).
          2. EPUB2 — OPF metadata ``<meta name="cover" content="{id}"/>``,
             resolved to a manifest item by id.
          3. Fallback — first ``<img>`` referenced by the cover HTML page.

        Returns ``None`` when no cover can be located (no extraction error is
        fatal — books without covers still import successfully).
        """
        try:
            book = self.read_epub_file()
        except Exception:
            logger.exception("Failed to open EPUB for cover extraction")
            return None

        # 1. EPUB3 cover-image property.
        for item in book.get_items_of_type(ITEM_COVER):
            media_type = (getattr(item, "media_type", "") or "").lower()
            if media_type.startswith("image/"):
                content = item.get_content()
                if content:
                    return (media_type, content)

        # 2. EPUB2 OPF <meta name="cover" content="{id}"/>.
        try:
            meta_entries = book.get_metadata("OPF", "cover") or []
        except Exception:
            meta_entries = []
        for entry in meta_entries:
            # Each entry is a (value, attrs) tuple; attrs holds the referenced id.
            attrs = entry[1] if len(entry) > 1 and isinstance(entry[1], dict) else {}
            cover_id = attrs.get("content")
            if not cover_id:
                continue
            item = book.get_item_with_id(cover_id)
            if item is None:
                continue
            media_type = (getattr(item, "media_type", "") or "").lower()
            if media_type.startswith("image/"):
                content = item.get_content()
                if content:
                    return (media_type, content)

        # 3. Fallback — first <img> on the cover HTML page.
        for item in book.get_items_of_type(ITEM_DOCUMENT):
            if not self._is_cover_item(item):
                continue
            try:
                html = item.get_content().decode("utf-8", errors="replace")
            except Exception:
                continue
            soup = BeautifulSoup(html, "html.parser")
            src: str | None = None
            img = soup.find("img")
            if img is not None:
                raw_src = img.get("src")  # type: ignore[attr-defined]
                src = raw_src if isinstance(raw_src, str) else None
            if src is None:
                # EPUB3 cover pages often use SVG <image xlink:href="…"/>.
                svg_image = soup.find("image")
                if svg_image is not None:
                    raw_src = svg_image.get("xlink:href") or svg_image.get("href")  # type: ignore[attr-defined]
                    src = raw_src if isinstance(raw_src, str) else None
            if not src or src.startswith("data:"):
                continue
            # Strip any fragment/query and normalise the basename.
            src_clean = unquote(src).split("#")[0].split("?")[0]
            basename = src_clean.rsplit("/", 1)[-1].lower()
            if not basename:
                continue
            for img_item in book.get_items_of_type(ITEM_IMAGE):
                name = (img_item.get_name() or "").lower()
                if name.endswith(basename) or name.rsplit("/", 1)[-1] == basename:
                    media_type = (getattr(img_item, "media_type", "") or "").lower()
                    if media_type.startswith("image/"):
                        content = img_item.get_content()
                        if content:
                            return (media_type, content)
            break  # only inspect the first cover page

        return None

    @classmethod
    def cover_extension_for(cls, media_type: str) -> str:
        """Pick the on-disk file extension for a given cover media type."""
        return cls._COVER_EXT_BY_MEDIA_TYPE.get(media_type.lower(), "jpg")
