"""Parser for KRDICT (한국어기초사전) bulk XML export.

Source:  https://krdict.korean.go.kr/openApi/openApiInfo
Format:  LMF (Lexical Markup Framework) XML, DTD version 16
License: CC BY-SA 2.0 KR

The bulk download is a ZIP containing one or more XML files.
Each XML file follows this structure:

    <LexicalResource dtdVersion="16">
      <GlobalInformation>...</GlobalInformation>
      <Lexicon>
        <LexicalEntry id="40834">
          <feat att="partOfSpeech"     val="명사"/>
          <feat att="vocabularyLevel"  val="초급"/>
          <feat att="origin"           val="家族"/>   <!-- hanja, if any -->
          <Lemma>
            <feat att="writtenForm" val="가족"/>
          </Lemma>
          <Sense id="1">
            <feat att="definition" val="같은 집에서 함께 생활하는 사람들의 집단."/>
            <SenseExample type="문장">
              <feat att="example" val="우리 가족은 서울에 살아요."/>
            </SenseExample>
            <Equivalent lang="en">
              <feat att="translation" val="family"/>
              <feat att="definition"  val="A group of people..."/>
            </Equivalent>
          </Sense>
        </LexicalEntry>
      </Lexicon>
    </LexicalResource>

The `origin` feat is only present when the word has a hanja or foreign-language
origin; it may be empty or hold romanised text for non-hanja origins — we only
keep it when it contains CJK characters.

Vocabulary-level mapping:  초급 → beginner  |  중급 → intermediate  |  고급 → advanced
"""
from __future__ import annotations

import io
import re
import zipfile
import xml.etree.ElementTree as ET

# CJK Unified Ideographs block — used to detect hanja vs. romanised origins
_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")

_LEVEL_MAP = {
    "초급": "beginner",
    "중급": "intermediate",
    "고급": "advanced",
}

# Korean POS → normalised English label
_POS_MAP = {
    "명사": "noun",
    "대명사": "pronoun",
    "수사": "numeral",
    "동사": "verb",
    "형용사": "adjective",
    "관형사": "determiner",
    "부사": "adverb",
    "감탄사": "interjection",
    "조사": "postposition",
    "접속사": "conjunction",
    "의존명사": "dependent noun",
    "보조동사": "auxiliary verb",
    "보조형용사": "auxiliary adjective",
    "접두사": "prefix",
    "접미사": "suffix",
}


def _feat(element: ET.Element, att: str) -> str:
    """Return the value of the first <feat att=*att*> child, or ''."""
    for child in element:
        if child.tag == "feat" and child.get("att") == att:
            return (child.get("val") or "").strip()
    return ""


def _parse_xml(data: bytes) -> list[dict]:
    """Parse one KRDICT LMF XML file into row dicts."""
    try:
        root = ET.fromstring(data.decode("utf-8", errors="replace"))
    except ET.ParseError:
        return []

    # The Lexicon element may be a direct child or nested under LexicalResource
    lexicons = root.findall(".//Lexicon")
    rows: list[dict] = []

    for lexicon in lexicons:
        for entry in lexicon.findall("LexicalEntry"):
            # ── Headword ──────────────────────────────────────────────────────
            lemma_el = entry.find("Lemma")
            if lemma_el is None:
                continue
            word = _feat(lemma_el, "writtenForm").strip()
            if not word:
                continue

            # ── Entry-level metadata ──────────────────────────────────────────
            pos_raw = _feat(entry, "partOfSpeech")
            pos = _POS_MAP.get(pos_raw, pos_raw.lower() or None) or None

            level_raw = _feat(entry, "vocabularyLevel")
            level = _LEVEL_MAP.get(level_raw)

            origin = _feat(entry, "origin")
            # Keep origin only if it contains CJK (actual hanja), not romanised text
            hanja = origin if origin and _CJK_RE.search(origin) else None

            # ── Senses / definitions ──────────────────────────────────────────
            definitions: list[dict] = []
            for sense in entry.findall("Sense"):
                defn_text = _feat(sense, "definition")
                if not defn_text:
                    continue

                # Collect example sentences (any type: 구, 문장, 대화)
                examples: list[str] = []
                for ex_el in sense.findall("SenseExample"):
                    ex_text = _feat(ex_el, "example")
                    if ex_text:
                        examples.append(ex_text)

                # English equivalents (translation + optional English definition)
                en_translation: str | None = None
                en_definition: str | None = None
                for equiv in sense.findall("Equivalent"):
                    if equiv.get("lang", "").lower() in {"en", "eng", "english"}:
                        en_translation = _feat(equiv, "translation") or None
                        en_definition = _feat(equiv, "definition") or None
                        break

                definitions.append({
                    "text": defn_text,
                    "en": en_translation,
                    "en_def": en_definition or None,
                    "examples": examples,
                })

            if not definitions:
                continue

            rows.append({
                "word": word.lower(),
                "hanja": hanja,
                "pos": pos,
                "level": level,
                "definitions": definitions,
                "source_dict": "krdict",
            })

    return rows


def parse_krdict(
    content: bytes, source_lang: str, _target_lang: str
) -> list[dict]:
    """Parse a KRDICT ZIP or single XML export into row dicts for krdict_entries.

    Args:
        content:      Raw bytes of the uploaded file (ZIP or single XML).
        source_lang:  Must be "ko".
        _target_lang: Accepted but ignored.

    Returns:
        list[dict] with keys matching krdict_entries columns.
    """
    if source_lang.lower() != "ko":
        raise ValueError(
            f"KRDICT only supports source_lang='ko', got '{source_lang}'"
        )

    rows: list[dict] = []

    if zipfile.is_zipfile(io.BytesIO(content)):
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            xml_names = [n for n in zf.namelist() if n.lower().endswith(".xml")]
            if not xml_names:
                raise ValueError("No .xml files found inside the ZIP")
            for name in xml_names:
                rows.extend(_parse_xml(zf.read(name)))
    else:
        rows = _parse_xml(content)

    return rows
