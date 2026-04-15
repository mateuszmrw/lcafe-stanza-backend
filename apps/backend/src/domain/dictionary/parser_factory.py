"""Parser factory for dictionary file imports.

Each parser is a callable:
    parse(content: bytes, source_lang: str, target_lang: str) -> list[dict]

The returned dicts must have the keys expected by DictionaryEntryRepository.bulk_insert:
    word, source_lang, target_lang, pos, glosses, forms, etymology, labels, source_dict
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable

from src.infrastructure.cc_cedict.parser import parse_cc_cedict
from src.infrastructure.dict_cc.parser import parse_dict_cc
from src.infrastructure.krdict.parser import parse_krdict
from src.infrastructure.openrussian.parser import parse_openrussian

# Register/style tags extracted from kaikki.org sense.tags and gloss prefixes
_REGISTER_TAGS = frozenset({
    "informal", "formal", "archaic", "colloquial", "slang", "vulgar",
    "offensive", "regional", "dialectal", "rare", "obsolete", "poetic",
    "literary", "technical", "dated", "historical", "derogatory",
    "figurative", "euphemistic",
})

_LABEL_PREFIX_RE = re.compile(r"^\(([^)]+)\)\s+")

ParserFn = Callable[[bytes, str, str], list[dict]]


def _parse_wiktionary(content: bytes, source_lang: str, target_lang: str) -> list[dict]:
    """Parse a kaikki.org JSONL export into DictionaryEntry row dicts."""
    rows: list[dict] = []

    for line in content.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        word = obj.get("word", "").strip()
        if not word:
            continue

        pos = obj.get("pos", "")
        glosses: list[str] = []
        all_labels: set[str] = set()

        for sense in obj.get("senses", []):
            for tag in sense.get("tags", []):
                t = tag.lower()
                if t in _REGISTER_TAGS:
                    all_labels.add(t)
            for sense_gloss in sense.get("glosses", []):
                m = _LABEL_PREFIX_RE.match(sense_gloss)
                if m:
                    for part in m.group(1).split(","):
                        t = part.strip().lower()
                        if t in _REGISTER_TAGS:
                            all_labels.add(t)
                    glosses.append(sense_gloss[m.end():])
                else:
                    glosses.append(sense_gloss)

        forms: list[dict] = [
            {"form": f.get("form", ""), "tags": f.get("tags", [])}
            for f in obj.get("forms", [])
            if f.get("form") and f.get("form") not in ("-", "—", "–")
        ]
        etymology = obj.get("etymology_text") or obj.get("etymology") or None

        rows.append({
            "word": word.lower(),
            "source_lang": source_lang,
            "target_lang": target_lang,
            "pos": pos,
            "glosses": glosses,
            "forms": forms,
            "etymology": etymology,
            "labels": sorted(all_labels),
            "source_dict": "wiktionary",
        })

    return rows


# Registry: slug → parser function
# Add new dictionary sources here alongside their adapters in the lookup route.
_PARSERS: dict[str, ParserFn] = {
    "wiktionary": _parse_wiktionary,
    "openrussian": parse_openrussian,
    "cc-cedict": parse_cc_cedict,
    "dict.cc": parse_dict_cc,
    "krdict": parse_krdict,
}


def get_parser(source_slug: str) -> ParserFn | None:
    return _PARSERS.get(source_slug)


def supported_slugs() -> list[str]:
    return list(_PARSERS.keys())
