"""Penn Treebank bracket string parser for phrase boundary extraction (ADR-020).

Parses constituency strings produced by Stanza and returns NP/VP span tuples.
No external dependencies — uses a simple stack-based tokenizer.
"""
from __future__ import annotations

_PHRASE_LABELS = frozenset({"NP", "VP", "PP", "ADJP", "ADVP", "SBAR"})


def extract_phrases(bracket: str) -> list[tuple[int, int, str]]:
    """Return (start_word, end_word_exclusive, phrase_type) for target phrases.

    Word indices are 0-based within the sentence. Nested phrases are both
    returned (e.g., an NP inside a VP appears as separate entries).

    Returns [] on parse failure.
    """
    if not bracket or not bracket.strip():
        return []

    results: list[tuple[int, int, str]] = []
    stack: list[tuple[str, int]] = []  # (label, start_word_idx)
    word_idx = 0
    last_was_open = False

    # Tokenize bracket string into (type, value) pairs.
    tokens: list[tuple[str, str]] = []
    i = 0
    n = len(bracket)
    while i < n:
        c = bracket[i]
        if c == "(":
            tokens.append(("OPEN", "("))
            i += 1
        elif c == ")":
            tokens.append(("CLOSE", ")"))
            i += 1
        elif c in " \t\n":
            i += 1
        else:
            j = i
            while j < n and bracket[j] not in "() \t\n":
                j += 1
            tokens.append(("ATOM", bracket[i:j]))
            i = j

    try:
        for ttype, tval in tokens:
            if ttype == "OPEN":
                last_was_open = True
            elif ttype == "ATOM":
                if last_was_open:
                    # First ATOM after OPEN is always the node label.
                    stack.append((tval, word_idx))
                    last_was_open = False
                else:
                    # ATOM not after OPEN is a leaf word.
                    word_idx += 1
            elif ttype == "CLOSE":
                last_was_open = False
                if stack:
                    label, start = stack.pop()
                    if label in _PHRASE_LABELS and word_idx > start:
                        results.append((start, word_idx, label))
    except Exception:
        return []

    return results


def phrases_for_page(
    constituency: list[str | None],
    stored_tokens: list[dict],
) -> list[dict]:
    """Convert per-sentence constituency strings into a flat phrase list.

    Args:
        constituency: list indexed by sentence_idx; each entry is a Penn bracket
            string or None if parsing failed / constituency not available.
        stored_tokens: token dicts from content_pages.tokens (with "si" and "w" keys).

    Returns:
        List of {"si": int, "start": int, "end": int, "type": str, "text": str}
        sorted by (si, start).
    """
    # Build per-sentence word list for text reconstruction.
    sent_words: dict[int, list[str]] = {}
    for t in stored_tokens:
        si = t.get("si", 0)
        sent_words.setdefault(si, []).append(t.get("w", ""))

    results: list[dict] = []
    for si, bracket in enumerate(constituency):
        if not bracket:
            continue
        spans = extract_phrases(bracket)
        words = sent_words.get(si, [])
        for start, end, label in spans:
            phrase_text = " ".join(words[start:end])
            results.append({
                "si": si,
                "start": start,
                "end": end,
                "type": label,
                "text": phrase_text,
            })

    results.sort(key=lambda r: (r["si"], r["start"]))
    return results
