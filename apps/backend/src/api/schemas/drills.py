from typing import Literal

from pydantic import BaseModel


class DrillQuestion(BaseModel):
    id: str
    type: Literal["fill_blank", "multiple_choice", "case_identification"]
    lemma: str
    display_lemma: str
    prompt: str
    form_type: str
    sentence: str | None = None
    highlighted_word: str | None = None  # for case_identification: word to highlight in sentence
    options: list[str] | None = None
    correct_form: str
    accepted_forms: list[str] = []  # all valid answers (for scoring in Redis)


class DrillSessionResponse(BaseModel):
    session_id: str
    available: bool
    reason: str | None = None
    questions: list[DrillQuestion] = []
    drill_type: str = "form_production"


class AvailableDrill(BaseModel):
    type: str
    name: str
    description: str
    available: bool
    reason: str | None = None


class AvailableDrillsResponse(BaseModel):
    drills: list[AvailableDrill]


class DrillAnswerSubmit(BaseModel):
    question_id: str
    answer: str


class DrillSubmitRequest(BaseModel):
    session_id: str
    answers: list[DrillAnswerSubmit]


class DrillResult(BaseModel):
    question_id: str
    correct: bool
    user_answer: str
    correct_form: str
    lemma: str
    form_type: str


class DrillSubmitResponse(BaseModel):
    score: int
    total: int
    results: list[DrillResult]
