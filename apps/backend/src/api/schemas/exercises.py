"""Pydantic schemas for exercises API."""
from pydantic import BaseModel


class ExerciseCheckResponse(BaseModel):
    """Response to GET /exercises/check."""

    should_show: bool
    candidate_count: int


class ClozExercise(BaseModel):
    """Cloze exercise type."""

    id: str
    type: str = "cloze"
    word_id: str
    lemma: str
    sentence_tokens: list[str]
    blank_index: int
    correct_form: str


class MeaningRecallExercise(BaseModel):
    """Meaning recall (multiple choice) exercise."""

    id: str
    type: str = "meaning_recall"
    word_id: str
    lemma: str
    sentence: str
    highlighted_word: str
    options: list[str]
    correct_index: int


class GrammarMicroDrillExercise(BaseModel):
    """Grammar micro-drill exercise."""

    id: str
    type: str = "grammar_micro_drill"
    word_id: str
    lemma: str
    prompt: str
    options: list[str]
    correct_index: int


class ExerciseSessionResponse(BaseModel):
    """Response to GET /exercises."""

    session_id: str
    exercises: list[dict]  # Union of the three exercise types


class ExerciseAnswer(BaseModel):
    """Single answer submission."""

    exercise_id: str
    word_id: str
    answer: str
    exercise_type: str


class ExerciseCompleteRequest(BaseModel):
    """Request to POST /exercises/complete."""

    session_id: str
    page: int
    answers: list[ExerciseAnswer]


class ExerciseResult(BaseModel):
    """Result for a single exercise."""

    exercise_id: str
    correct: bool
    correct_form: str


class WordUpgrade(BaseModel):
    """Word status upgrade."""

    word_id: str
    lemma: str
    old_status: str
    new_status: str


class ExerciseCompleteResponse(BaseModel):
    """Response to POST /exercises/complete."""

    results: list[ExerciseResult]
    upgrades: list[WordUpgrade]


class ExerciseSnoozeRequest(BaseModel):
    """Request to POST /exercises/snooze."""

    page: int


class ExerciseSnoozeResponse(BaseModel):
    """Response to POST /exercises/snooze."""

    snooze_until_page: int
