"""Vocabulary noise filter — shared between the tokenize worker and the dev clean script."""

_HEX_CHARS = frozenset("0123456789abcdef")
_LATIN_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")


def _is_hex_hash(w: str) -> bool:
    lw = w.lower()
    if len(lw) < 6 or not all(c in _HEX_CHARS for c in lw):
        return False
    # Require enough digits — real hashes have them; words like "decade"/"facade" don't
    return sum(c.isdigit() for c in lw) >= max(2, len(lw) // 3)


def _is_latin_only(w: str) -> bool:
    alpha = [c for c in w if c.isalpha()]
    return bool(alpha) and all(c in _LATIN_CHARS for c in alpha)


def is_trash(word: str, pos: str = "") -> tuple[bool, str]:
    """Return (True, reason) if the word should be excluded from vocabulary.

    Catches URLs, punctuation-only tokens, hex hashes, alphanumeric junk, etc.
    Safe to call with any POS tag; POS is only used for the latin/X-tag check.
    """
    w = word.strip()

    if not w:
        return True, "empty"

    if "://" in w or w.startswith("www."):
        return True, "URL"

    if "." in w:
        return True, "contains ."

    if "/" in w:
        return True, "contains /"

    if "=" in w:
        return True, "contains ="

    if " " in w:
        return True, "multi-word phrase"

    if not any(c.isalpha() for c in w):
        return True, "no alphabetic chars"

    if _is_hex_hash(w):
        return True, "hex hash"

    digits_and_alpha = all(c.isdigit() or c.isalpha() for c in w)
    has_digit = any(c.isdigit() for c in w)
    has_alpha = any(c.isalpha() for c in w)
    if digits_and_alpha and has_digit and has_alpha and len(w) <= 12 and _is_latin_only(w):
        return True, "alphanumeric junk"

    stripped = w.lstrip("0123456789-\u2013\u2014")
    if not stripped:
        return True, "numeric"

    if len(w) > 60:
        return True, f"too long ({len(w)} chars)"

    if pos == "X" and _is_latin_only(w):
        return True, "latin word with POS=X (metadata)"

    return False, ""
