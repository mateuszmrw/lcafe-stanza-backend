"""Token enrichment for reader pages.

Takes raw page text and a words_map (surface_form → word data from DB) and
returns a list of TokenWithStatus objects ready to send to the frontend.
"""
from __future__ import annotations

import re

from src.api.schemas.books import TokenWithStatus

# Matches individual word tokens (letters/digits only) — used for vocabulary lookups.
_WORD_RE = re.compile(r"\b\w+\b")
# Matches words OR individual punctuation/symbol characters (not whitespace).
# Used when building the full token list for the reader, so punctuation is preserved.
_TOKEN_RE = re.compile(r"\w+|[^\w\s]")


def collect_surface_forms(text: str) -> list[str]:
    """Return lowercased word surface forms from page text (for words_map lookup)."""
    return [m.group(0).lower() for m in _WORD_RE.finditer(text)]


def enrich_page_tokens(text: str, words_map: dict[str, dict]) -> list[TokenWithStatus]:
    """Convert raw page text into enriched token list using the vocabulary words_map.

    Paragraphs are split on double newlines; sentences on single newlines within.
    Punctuation tokens are annotated with status='ignored'.
    """
    tokens: list[TokenWithStatus] = []
    paragraphs = re.split(r"\n\n+", text)
    global_si = 0

    for pi, paragraph in enumerate(paragraphs):
        sentences = [s for s in re.split(r"\r?\n", paragraph) if s.strip()]
        if not sentences:
            sentences = [paragraph]

        for sentence in sentences:
            for m in _TOKEN_RE.finditer(sentence):
                surface = m.group(0)
                is_punct = not (surface[0].isalnum() or surface[0] == "_")

                if is_punct:
                    tokens.append(TokenWithStatus(
                        w=surface, l="", pos="PUNCT", r="",
                        pi=pi, si=global_si, g="", f="",
                        dep_head=0, dep_rel="", status="ignored",
                    ))
                else:
                    key = surface.lower()
                    word_data = words_map.get(key, {})
                    tokens.append(TokenWithStatus(
                        id=word_data.get("id"),
                        w=surface,
                        l=word_data.get("lemma", ""),
                        pos=word_data.get("pos", ""),
                        r=word_data.get("reading", ""),
                        pi=pi,
                        si=global_si,
                        g=word_data.get("gender", ""),
                        f=word_data.get("feats", ""),
                        dep_head=word_data.get("dep_head", 0),
                        dep_rel=word_data.get("dep_rel", ""),
                        hint=word_data.get("hint"),
                        status=word_data.get("status", "new"),
                    ))
            global_si += 1

    return tokens
