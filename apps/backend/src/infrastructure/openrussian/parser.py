"""Parser for the OpenRussian.org dataset exported from TogetherDB.

Source:  https://en.openrussian.org/dictionary-data
Export:  https://app.togetherdb.com/db/fwoedz5fvtwvq03v/openrussian_public

Usage
-----
1. Export the tables you need from TogetherDB (CSV button on each table tab).
   Required:   words, translations
   Optional:   words_forms, verbs, nouns

2. Collect the downloaded files into a single ZIP archive and upload via the
   admin dictionary page with source "OpenRussian" and language pair ru → en.

File naming
-----------
TogetherDB exports files as "openrussian_public - {table}.csv".
Plain names like "words.csv" are also accepted.

Table schemas (as confirmed from the live database)
----------------------------------------------------
words.csv:        id, bare, accented, derived_from_word_id, rank, disabled, usage_en, type
translations.csv: id, lang, position, word_id, tl, example_ru, example_tl, info
words_forms.csv:  word_id, form_type, form
verbs.csv:        word_id, aspect, partner
nouns.csv:        word_id, gender, partner, animate, indeclinable, sg_only, pl_only

Stress marks
------------
The `accented` column uses trailing-apostrophe notation ("она'" means stress on а).
This parser converts those to Unicode combining acute accents (U+0301) in-place.
"""
from __future__ import annotations

import csv
import io
import zipfile

# U+0301 combining acute accent — placed after the stressed vowel
_COMBINING_ACUTE = "\u0301"


def _convert_stress(word: str) -> str:
    """Replace trailing-apostrophe stress notation with combining acute accent.

    E.g. "она'" → "она́"  (a + U+0301)
    """
    return word.replace("'", _COMBINING_ACUTE)


def _read_csv(data: bytes) -> list[dict[str, str]]:
    """Parse a comma-separated CSV file into a list of dicts.

    Uses utf-8-sig to automatically strip a BOM if present (TogetherDB
    sometimes prepends one to CSV exports).
    """
    # utf-8-sig strips leading BOM (\ufeff) so the first column name is clean
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text), delimiter=",")
    return [row for row in reader]


def _find_table(zf: zipfile.ZipFile, table_name: str) -> bytes | None:
    """Return the bytes of the first ZIP entry whose name matches *table_name*.

    Matches both "words.csv" and "openrussian_public - words.csv".
    """
    for name in zf.namelist():
        base = name.split("/")[-1].lower()
        if base == f"{table_name}.csv" or base == f"openrussian_public - {table_name}.csv":
            return zf.read(name)
    return None


def parse_openrussian(
    content: bytes, source_lang: str, _target_lang: str
) -> list[dict]:
    """Parse an OpenRussian ZIP export into row dicts for openrussian_words.

    Args:
        content:     Raw bytes of the uploaded file (ZIP or single words.csv).
        source_lang: Must be "ru".
        _target_lang: Accepted but ignored; OpenRussian is ru-only.

    Returns:
        list[dict] with keys matching openrussian_words columns.
    """
    if source_lang.lower() != "ru":
        raise ValueError(
            f"OpenRussian only supports source_lang='ru', got '{source_lang}'"
        )

    # ── Load tables ────────────────────────────────────────────────────────────
    words_data: bytes | None = None
    translations_data: bytes | None = None
    forms_data: bytes | None = None
    verbs_data: bytes | None = None
    nouns_data: bytes | None = None

    if zipfile.is_zipfile(io.BytesIO(content)):
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            words_data = _find_table(zf, "words")
            translations_data = _find_table(zf, "translations")
            forms_data = _find_table(zf, "words_forms")
            verbs_data = _find_table(zf, "verbs")
            nouns_data = _find_table(zf, "nouns")
    else:
        # Single file — assume it is words.csv (no translations → glosses empty)
        words_data = content

    if words_data is None:
        raise ValueError(
            "No 'words.csv' (or 'openrussian_public - words.csv') found in the upload"
        )
    if translations_data is None:
        raise ValueError(
            "No 'translations.csv' found — required for English definitions. "
            "Export it from TogetherDB and include it in the ZIP."
        )

    # ── Parse words ────────────────────────────────────────────────────────────
    words: dict[str, dict] = {}  # word_id (str) → word dict
    for row in _read_csv(words_data):
        wid = row.get("id", "").strip()
        bare = row.get("bare", "").strip()
        if not wid or not bare:
            continue
        if row.get("disabled", "").strip().lower() in {"1", "true", "yes"}:
            continue
        rank_raw = row.get("rank", "").strip()
        accented_raw = row.get("accented", "").strip()
        words[wid] = {
            "bare": bare.lower(),
            "accented": _convert_stress(accented_raw) if accented_raw else None,
            "pos": row.get("type", "").strip().lower() or "other",
            "rank": int(rank_raw) if rank_raw and rank_raw.isdigit() else None,
            "aspect": None,
            "glosses": [],
            "forms": [],
        }

    # ── Enrich with verb aspect ────────────────────────────────────────────────
    if verbs_data:
        for row in _read_csv(verbs_data):
            wid = row.get("word_id", "").strip()
            if wid in words:
                aspect = row.get("aspect", "").strip().lower() or None
                words[wid]["aspect"] = aspect

    # ── Enrich with noun gender (stored as label in glosses metadata) ──────────
    noun_gender: dict[str, str] = {}
    if nouns_data:
        for row in _read_csv(nouns_data):
            wid = row.get("word_id", "").strip()
            gender = row.get("gender", "").strip().lower()
            if wid and gender:
                noun_gender[wid] = gender

    # ── Parse translations (English only) ─────────────────────────────────────
    if translations_data:
        for row in _read_csv(translations_data):
            if row.get("lang", "").strip().lower() != "en":
                continue
            wid = row.get("word_id", "").strip()
            if wid not in words:
                continue
            tl = row.get("tl", "").strip()
            if not tl:
                continue
            words[wid]["glosses"].append({
                "text": tl,
                "info": row.get("info", "").strip() or None,
                "example_ru": row.get("example_ru", "").strip() or None,
                "example_tl": row.get("example_tl", "").strip() or None,
            })

    # ── Parse forms ────────────────────────────────────────────────────────────
    if forms_data:
        for row in _read_csv(forms_data):
            wid = row.get("word_id", "").strip()
            if wid not in words:
                continue
            form_type = row.get("form_type", "").strip()
            form_val = row.get("form", "").strip()
            if form_type and form_val and form_val != "-":
                # form_type is e.g. "nominative singular" → split into tags list
                tags = [t.strip() for t in form_type.split() if t.strip()]
                words[wid]["forms"].append({"form": form_val, "tags": tags})

    # ── Build output rows ──────────────────────────────────────────────────────
    result: list[dict] = []
    for wid, word in words.items():
        if not word["glosses"]:
            continue  # skip words with no English translations

        # Attach noun gender as a label via metadata
        # (stored inside glosses[0]["info"] would be wrong — pass via bare metadata key)
        gender = noun_gender.get(wid)
        if gender:
            # Prepend gender to info of first gloss if no info already set
            if word["glosses"] and not word["glosses"][0].get("info"):
                word["glosses"][0]["info"] = gender

        result.append({
            "bare": word["bare"],
            "accented": word["accented"],
            "pos": word["pos"],
            "rank": word["rank"],
            "aspect": word["aspect"],
            "glosses": word["glosses"],
            "forms": word["forms"],
            "source_dict": "openrussian",
        })

    return result
