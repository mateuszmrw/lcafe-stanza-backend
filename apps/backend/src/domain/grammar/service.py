import json
import logging
import re

from src.api.schemas.grammar import GrammarExplainResponse, TokenAnnotation, TokenInput
from src.infrastructure.llm.client import LLMClient

log = logging.getLogger(__name__)

# Strict whitelist for values embedded in LLM prompts. Anything user-influenced
# that lands in the prompt must pass these — otherwise a crafted input like
# "en. Ignore all prior instructions and..." could hijack the prompt.
_LANG_CODE_RE = re.compile(r"^[a-z]{2,3}(?:-[a-zA-Z]{2,8})?$")
_PROFICIENCY_LEVELS = {"A1", "A2", "B1", "B2", "C1", "C2"}
_ALLOWED_REGISTERS = {"formal", "literary", "informal", "technical"}


def _safe_lang(code: str) -> str:
    """Lowercase + validate a language code. Raises ValueError on injection attempts."""
    code = (code or "").strip().lower()
    if not _LANG_CODE_RE.match(code):
        raise ValueError(f"Invalid language code: {code!r}")
    return code


def _safe_proficiency(level: str) -> str:
    level = (level or "").strip().upper()
    if level not in _PROFICIENCY_LEVELS:
        raise ValueError(f"Invalid proficiency level: {level!r}")
    return level


def _safe_register(register: str | None) -> str | None:
    if register is None:
        return None
    register = register.strip().lower()
    if register not in _ALLOWED_REGISTERS:
        # Drop invalid registers rather than raising — register is user-controlled
        # metadata where nothing critical depends on it.
        return None
    return register

_SYSTEM_PROMPT = """\
You are a friendly language tutor helping someone learn a foreign language.
You will receive a sentence's tokens with linguistic features and information about the learner.

Your tone must be conversational and encouraging — like a patient tutor talking to a student, \
not a linguist writing a textbook. Avoid academic jargon. Write as if you are explaining \
over coffee, using plain words the learner already knows.

CRITICAL: You MUST write both the token annotations and the prose explanation in the learner's \
native language specified in the user message. If the native language is Polish, write in Polish. \
If it is English, write in English. If it is German, write in German. And so on. \
Never respond in the sentence's language or in English by default.

Your job:
1. For each content word (not punctuation), write a SHORT practical label in the learner's native language \
   — what role this word plays, e.g. "subject", "verb — past tense", "adjective agreeing with subject". \
   Keep labels brief (3–6 words max).
2. Write a prose explanation in the learner's native language. It must:
   - Tell the learner what is happening in plain terms: who does what.
   - Point out 1–3 grammar patterns that are worth noticing, explained simply and practically. \
     Focus on patterns the learner will reuse, not on exhaustive analysis.
   - When a pattern works differently from the learner's native language, say so in one plain sentence \
     (e.g. "In Russian you don't need an article here, unlike in English").
   - Never translate the original words — keep them in their original form and script.
   - Match the depth to proficiency: A1–A2 = one simple takeaway; B1–B2 = 2–3 useful patterns; \
     C1–C2 = subtle choices, register, style.
   - Use one concrete example to reinforce.
   - Use SHORT paragraphs. Aim for 3–5 sentences total, never more than 6.

Respond ONLY with a valid JSON object — no markdown, no extra keys:
{
  "token_annotations": [
    {"w": "<exact surface form>", "annotation": "<short label in learner's native language>"}
  ],
  "prose_explanation": "<plain, conversational explanation in learner's native language>"
}"""


_INTERESTING_FEATURES: dict[str, list[str]] = {
    "ru": ["Case", "Aspect", "Animacy", "Voice", "Mood"],
    "pl": ["Case", "Aspect", "Animacy", "Gender"],
    "ko": ["Tense", "Mood", "Polite"],
    "zh": ["Aspect"],
    "zh-hans": ["Aspect"],
}


def _build_dep_summary(tokens: list[TokenInput]) -> str:
    head_map = {i + 1: t for i, t in enumerate(tokens)}  # 1-based
    lines: list[str] = []
    for t in tokens:
        if t.dep_rel == "ROOT":
            lines.append(f'"{t.w}" is the main verb (ROOT)')
        elif t.dep_head and t.dep_rel:
            head = head_map.get(t.dep_head)
            if head:
                lines.append(f'"{t.w}" → {t.dep_rel} of "{head.w}"')
    return "\n".join(lines) if lines else "—"


def _select_focus_features(tokens: list[TokenInput], language_code: str) -> list[str]:
    candidates = _INTERESTING_FEATURES.get(language_code, ["Case", "Tense"])
    found: list[str] = []
    for feat in candidates:
        if any(feat in (t.feats or "") for t in tokens):
            found.append(feat)
        if len(found) == 2:
            break
    return found or candidates[:2]


def _build_user_prompt(
    tokens: list[TokenInput],
    language_code: str,
    proficiency_level: str,
    native_language_code: str,
    register: str | None = None,
) -> str:
    morph_rows = "\n".join(
        f"  {t.w!r:20s} | lemma={t.l!r:20s} | pos={t.pos:10s} | xpos={t.x or '—':15s} | gender={t.g or '—':6s} | feats={t.feats or '—':35s} | head={t.dep_head:2d} | rel={t.dep_rel or '—'}"
        for t in tokens
    )
    dep_summary = _build_dep_summary(tokens)
    focus = ", ".join(_select_focus_features(tokens, language_code)) or "general structure"
    register_line = f"Document register: {register}" if register else "Document register: unspecified"

    return (
        f"Sentence language: {language_code}\n"
        f"Learner proficiency: {proficiency_level}\n"
        f"Learner native language: {native_language_code}\n"
        f"{register_line}\n\n"
        f"MORPHOLOGICAL ANALYSIS:\n{morph_rows}\n\n"
        f"DEPENDENCY STRUCTURE:\n{dep_summary}\n\n"
        f"FOCUS ON: {focus}\n\n"
        f"Do not contradict the Stanza analysis above.\n"
        f"Write the entire JSON response (annotations and prose_explanation) in {native_language_code}."
    )


class GrammarExplanationService:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def explain(
        self,
        tokens: list[TokenInput],
        language_code: str,
        proficiency_level: str,
        native_language_code: str,
        register: str | None = None,
    ) -> GrammarExplainResponse:
        # Sanitize any user-controlled values that end up in the prompt.
        # Prevents prompt injection via e.g. native_language_code = "en. Ignore prior..."
        language_code = _safe_lang(language_code)
        native_language_code = _safe_lang(native_language_code)
        proficiency_level = _safe_proficiency(proficiency_level)
        register = _safe_register(register)

        user_prompt = _build_user_prompt(
            tokens, language_code, proficiency_level, native_language_code, register
        )
        raw = await self._llm.complete(_SYSTEM_PROMPT, user_prompt)

        try:
            data = json.loads(raw)
            return GrammarExplainResponse(
                token_annotations=[
                    TokenAnnotation(**a) for a in data["token_annotations"]
                ],
                prose_explanation=data["prose_explanation"],
            )
        except Exception as exc:
            log.warning("Failed to parse LLM grammar response: %s | raw=%r", exc, raw)
            raise ValueError("LLM returned an unparseable response") from exc
