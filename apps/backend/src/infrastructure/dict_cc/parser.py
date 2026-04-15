"""Parser for dict.cc bulk download TSV files.

Source: https://www.dict.cc/ (requires free registration for bulk download)

File format
-----------
- Lines starting with # are comments (license, attribution, column headers).
- Data lines are tab-separated with 2–4 columns:
    source_word  \\t  target_word  [\\t subject_area]  [\\t word_type]
- POS tags appear in curly braces: {n}, {v}, {adj}, {adv}, {prep}, {conj}, {pron}
  They may be inline within the word columns or in a dedicated 3rd/4th column.
- Subject area / register tags appear in square brackets: [med.], [Am.], [coll.]
  They may also be inline within the word columns.

Filename convention
-------------------
dict.cc exports are typically named "<source>-<target>.txt",
e.g. "de-en.txt", "ru-en.txt", "fr-en.txt".
This parser ignores the filename — language pair is passed explicitly.
"""
from __future__ import annotations

import re

# POS tag map: dict.cc curly-brace notation → normalised label
_POS_MAP: dict[str, str] = {
    "n": "noun",
    "v": "verb",
    "adj": "adjective",
    "adv": "adverb",
    "prep": "preposition",
    "conj": "conjunction",
    "pron": "pronoun",
    "interj": "interjection",
    "num": "numeral",
    "art": "article",
    "prefix": "prefix",
    "suffix": "suffix",
    "abbr": "abbreviation",
}

# Matches {tag} — POS markers
_CURLY_RE = re.compile(r"\{([^}]+)\}")
# Matches [tag] — subject area / register markers (kept as notes)
_BRACKET_RE = re.compile(r"\[([^\]]+)\]")


def _extract_tags(text: str) -> tuple[str, str | None, str | None]:
    """Return (cleaned_text, pos, notes) for a field value.

    Removes all {..} and [..] markers, returns the first recognised POS and
    a joined notes string from all [..] markers found in *text*.
    """
    pos: str | None = None
    note_parts: list[str] = []

    for m in _CURLY_RE.finditer(text):
        tag = m.group(1).strip().lower()
        if pos is None and tag in _POS_MAP:
            pos = _POS_MAP[tag]

    for m in _BRACKET_RE.finditer(text):
        note_parts.append(m.group(1).strip())

    cleaned = _CURLY_RE.sub("", text)
    cleaned = _BRACKET_RE.sub("", cleaned)
    cleaned = cleaned.strip().strip(",;").strip()

    notes = ", ".join(note_parts) if note_parts else None
    return cleaned, pos, notes


def parse_dict_cc(
    content: bytes, source_lang: str, target_lang: str
) -> list[dict]:
    """Parse a dict.cc TSV export into row dicts for dict_cc_entries.

    Args:
        content:     Raw bytes of the uploaded file (plain text or ZIP).
        source_lang: Source language code (e.g. "de", "ru").
        target_lang: Target language code (e.g. "en").

    Returns:
        list[dict] with keys: source_word, source_lang, target_word,
        target_lang, pos, notes, source_dict.
    """
    # dict.cc files can be wrapped in a ZIP
    import io
    import zipfile

    if zipfile.is_zipfile(io.BytesIO(content)):
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            # Pick the first .txt / .tsv entry
            for name in zf.namelist():
                if name.lower().endswith((".txt", ".tsv", ".tab")):
                    content = zf.read(name)
                    break
            else:
                raise ValueError("No .txt/.tsv file found inside the ZIP")

    # dict.cc exports are typically UTF-8 with a BOM, or Latin-1
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1", errors="replace")

    src = source_lang.lower()
    tgt = target_lang.lower()
    result: list[dict] = []

    for line in text.splitlines():
        # Skip blank lines and comment lines
        if not line.strip() or line.startswith("#"):
            continue

        cols = line.split("\t")
        if len(cols) < 2:
            continue

        raw_src = cols[0]
        raw_tgt = cols[1]
        # Any extra columns may contain additional POS/subject tags
        extra = " ".join(cols[2:]) if len(cols) > 2 else ""

        src_word, pos_src, notes_src = _extract_tags(raw_src)
        tgt_word, pos_tgt, notes_tgt = _extract_tags(raw_tgt)
        _, pos_extra, notes_extra = _extract_tags(extra)

        if not src_word or not tgt_word:
            continue

        # Prefer POS from extra column, then source, then target
        pos = pos_extra or pos_src or pos_tgt

        # Merge notes
        all_notes = [n for n in (notes_src, notes_tgt, notes_extra) if n]
        notes = "; ".join(all_notes) or None

        result.append({
            "source_word": src_word.lower(),
            "source_lang": src,
            "target_word": tgt_word,
            "target_lang": tgt,
            "pos": pos,
            "notes": notes,
            "source_dict": "dict.cc",
        })

    return result
