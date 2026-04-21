"""Tests for the constituency phrase extractor (ADR-020)."""
import pytest

from src.domain.nlp.constituency import extract_phrases, phrases_for_page


class TestExtractPhrases:
    def test_simple_np(self):
        bracket = "(ROOT (S (NP (DT the) (NN dog)) (VP (VBD ran))))"
        spans = extract_phrases(bracket)
        np_spans = [(s, e, t) for s, e, t in spans if t == "NP"]
        vp_spans = [(s, e, t) for s, e, t in spans if t == "VP"]
        assert (0, 2, "NP") in np_spans
        assert (2, 3, "VP") in vp_spans

    def test_nested_np_inside_vp(self):
        bracket = "(ROOT (S (VP (VBD ate) (NP (DT the) (NN cake)))))"
        spans = extract_phrases(bracket)
        # Both the outer VP and the inner NP should be returned
        types = {(s, e, t) for s, e, t in spans}
        assert any(t == "VP" for _, _, t in types)
        assert any(t == "NP" for _, _, t in types)

    def test_returns_empty_on_none(self):
        assert extract_phrases("") == []
        assert extract_phrases(None) == []  # type: ignore[arg-type]

    def test_returns_empty_on_malformed(self):
        assert extract_phrases("(((") == []

    def test_word_indices_are_zero_based(self):
        # (NP the quick fox) → words 0,1,2 → span (0, 3, "NP")
        bracket = "(ROOT (NP (DT the) (JJ quick) (NN fox)))"
        spans = extract_phrases(bracket)
        np = next(s for s in spans if s[2] == "NP")
        assert np == (0, 3, "NP")

    def test_punctuation_counts_as_word(self):
        bracket = "(ROOT (S (NP (NNP Ivan)) (. .)))"
        spans = extract_phrases(bracket)
        # NP contains word 0 only
        np = next((s for s in spans if s[2] == "NP"), None)
        assert np is not None
        assert np[0] == 0
        assert np[1] == 1


class TestPhrasesForPage:
    def test_basic(self):
        constituency = ["(ROOT (S (NP (DT the) (NN dog)) (VP (VBD ran))))"]
        tokens = [
            {"si": 0, "w": "the"},
            {"si": 0, "w": "dog"},
            {"si": 0, "w": "ran"},
        ]
        result = phrases_for_page(constituency, tokens)
        np = next(r for r in result if r["type"] == "NP")
        assert np["text"] == "the dog"
        assert np["si"] == 0
        assert np["start"] == 0
        assert np["end"] == 2

    def test_none_sentence_skipped(self):
        constituency = [None, "(ROOT (NP (NN cat)))"]
        tokens = [
            {"si": 1, "w": "cat"},
        ]
        result = phrases_for_page(constituency, tokens)
        assert len(result) == 1
        assert result[0]["si"] == 1

    def test_empty_constituency(self):
        assert phrases_for_page([], []) == []

    def test_sorted_by_si_then_start(self):
        bracket = "(ROOT (S (NP (DT a) (NN b)) (VP (VB c))))"
        tokens = [
            {"si": 0, "w": "a"},
            {"si": 0, "w": "b"},
            {"si": 0, "w": "c"},
        ]
        result = phrases_for_page([bracket], tokens)
        starts = [r["start"] for r in result]
        assert starts == sorted(starts)


class TestFeatsHelpers:
    """Isolated tests for the feats normalization helpers in word_repo."""

    def test_normalize_string(self):
        from src.infrastructure.db.repositories.word_repo import _normalize_feats
        assert _normalize_feats("Case=Nom|Gender=Masc") == {"Case": "Nom", "Gender": "Masc"}

    def test_normalize_empty_string(self):
        from src.infrastructure.db.repositories.word_repo import _normalize_feats
        assert _normalize_feats("") is None

    def test_normalize_dict_passthrough(self):
        from src.infrastructure.db.repositories.word_repo import _normalize_feats
        d = {"Case": "Nom"}
        assert _normalize_feats(d) is d

    def test_normalize_none(self):
        from src.infrastructure.db.repositories.word_repo import _normalize_feats
        assert _normalize_feats(None) is None

    def test_feats_to_str(self):
        from src.infrastructure.db.repositories.word_repo import _feats_to_str
        result = _feats_to_str({"Case": "Nom", "Gender": "Masc"})
        parts = set(result.split("|"))
        assert parts == {"Case=Nom", "Gender=Masc"}

    def test_feats_to_str_none(self):
        from src.infrastructure.db.repositories.word_repo import _feats_to_str
        assert _feats_to_str(None) == ""
        assert _feats_to_str({}) == ""
