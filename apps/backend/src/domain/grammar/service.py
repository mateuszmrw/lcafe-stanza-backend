import json
import logging

from src.api.schemas.grammar import GrammarExplainResponse, TokenAnnotation, TokenInput
from src.infrastructure.llm.client import LLMClient

log = logging.getLogger(__name__)

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


def _build_user_prompt(
    tokens: list[TokenInput],
    language_code: str,
    proficiency_level: str,
    native_language_code: str,
) -> str:
    rows = "\n".join(
        f"  {t.w!r:20s} | lemma={t.l!r:20s} | pos={t.pos:10s} | feats={t.feats or '-':30s} | head={t.dep_head:2d} | rel={t.dep_rel or '-'}"
        for t in tokens
    )
    return (
        f"Sentence language: {language_code}\n"
        f"Learner proficiency: {proficiency_level}\n"
        f"Learner native language: {native_language_code}\n\n"
        f"Token table:\n{rows}\n\n"
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
    ) -> GrammarExplainResponse:
        user_prompt = _build_user_prompt(
            tokens, language_code, proficiency_level, native_language_code
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
