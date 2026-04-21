from __future__ import annotations

# (preposition, governed_case, optional_context_hint)
_RULES: dict[str, list[tuple[str, str, str | None]]] = {
    "pl": [
        ("bez", "genitive", None),
        ("dla", "genitive", None),
        ("do", "genitive", None),
        ("od", "genitive", None),
        ("przy", "locative", None),
        ("w", "locative", "miejsce"),
        ("w", "accusative", "kierunek / czas"),
        ("na", "locative", "miejsce"),
        ("na", "accusative", "kierunek"),
        ("po", "locative", "po czymś / wokół"),
        ("o", "locative", "temat"),
        ("nad", "instrumental", "nad — pozycja"),
        ("pod", "instrumental", "pod — pozycja"),
        ("przed", "instrumental", "przed — pozycja"),
        ("za", "instrumental", "za — pozycja"),
        ("między", "instrumental", "między"),
        ("z", "instrumental", "z kimś / razem"),
        ("z", "genitive", "z czegoś / skądś"),
        ("ku", "dative", None),
        ("dzięki", "dative", None),
        ("przez", "accusative", "przez — powód / przejście"),
    ],
    "ru": [
        ("без", "genitive", None),
        ("для", "genitive", None),
        ("до", "genitive", None),
        ("из", "genitive", None),
        ("от", "genitive", None),
        ("у", "genitive", None),
        ("около", "genitive", None),
        ("вместо", "genitive", None),
        ("кроме", "genitive", None),
        ("к", "dative", None),
        ("по", "dative", "по — распределение / после"),
        ("благодаря", "dative", None),
        ("в", "prepositional", "в — место"),
        ("в", "accusative", "в — направление"),
        ("на", "prepositional", "на — место"),
        ("на", "accusative", "на — направление"),
        ("о", "prepositional", None),
        ("при", "prepositional", None),
        ("с", "instrumental", "с — вместе с"),
        ("над", "instrumental", None),
        ("перед", "instrumental", None),
        ("за", "instrumental", "за — позади (место)"),
        ("за", "accusative", "за — движение"),
        ("между", "instrumental", None),
        ("через", "accusative", None),
    ],
    "de": [
        ("aus", "dative", None),
        ("bei", "dative", None),
        ("mit", "dative", None),
        ("nach", "dative", None),
        ("seit", "dative", None),
        ("von", "dative", None),
        ("zu", "dative", None),
        ("durch", "accusative", None),
        ("für", "accusative", None),
        ("gegen", "accusative", None),
        ("ohne", "accusative", None),
        ("um", "accusative", None),
        ("in", "dative", "in — Ort"),
        ("in", "accusative", "in — Richtung"),
        ("an", "dative", "an — Ort"),
        ("an", "accusative", "an — Richtung"),
        ("auf", "dative", "auf — Ort"),
        ("auf", "accusative", "auf — Richtung"),
        ("über", "dative", "über — Ort"),
        ("über", "accusative", "über — Richtung"),
        ("unter", "dative", "unter — Ort"),
        ("neben", "dative", "neben — Ort"),
        ("gegenüber", "dative", None),
    ],
    "cs": [
        ("bez", "genitive", None),
        ("do", "genitive", None),
        ("od", "genitive", None),
        ("z", "genitive", "z — odkud"),
        ("k", "dative", None),
        ("v", "locative", "v — místo"),
        ("v", "accusative", "v — směr"),
        ("na", "locative", "na — místo"),
        ("na", "accusative", "na — směr"),
        ("o", "locative", "o — téma"),
        ("s", "instrumental", "s — spolu s"),
        ("před", "instrumental", "před — pozice"),
        ("za", "instrumental", "za — pozice"),
    ],
}

# All cases per language, used for generating MC options
CASE_OPTIONS: dict[str, list[str]] = {
    "ru": ["nominative", "genitive", "dative", "accusative", "instrumental", "prepositional"],
    "pl": ["nominative", "genitive", "dative", "accusative", "instrumental", "locative", "vocative"],
    "de": ["nominative", "genitive", "dative", "accusative"],
    "cs": ["nominative", "genitive", "dative", "accusative", "instrumental", "locative", "vocative"],
    "_default": ["nominative", "genitive", "dative", "accusative"],
}

# Languages where aspect (perfective/imperfective) is grammatically central
ASPECT_LANGUAGES = frozenset({"ru", "pl", "cs", "uk", "sr", "bs", "hr", "sk", "bg"})

SUPPORTED_PREPOSITION_LANGUAGES = frozenset(_RULES.keys())


def get_rules(lang_code: str) -> list[tuple[str, str, str | None]]:
    return _RULES.get(lang_code, [])


def get_case_options(lang_code: str) -> list[str]:
    return CASE_OPTIONS.get(lang_code) or CASE_OPTIONS["_default"]
