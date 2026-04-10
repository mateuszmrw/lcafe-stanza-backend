import uuid
from datetime import datetime

from pydantic import BaseModel


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime
    active_language_id: int | None = None
    active_language_code: str | None = None
    active_language_name: str | None = None
    proficiency_level: str | None = None
    native_language_code: str | None = None
    auto_ignore_proper_nouns: bool = False

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    username: str | None = None
    password: str | None = None


class ActiveLanguageRequest(BaseModel):
    language_id: int


class ApiKeyResponse(BaseModel):
    provider_slug: str
    exists: bool


class ApiKeyUpsertRequest(BaseModel):
    api_key: str


VALID_PROFICIENCY_LEVELS = {"A1", "A2", "B1", "B2", "C1", "C2"}


class ProficiencyUpdateRequest(BaseModel):
    proficiency_level: str | None = None
    native_language_code: str | None = None
    auto_ignore_proper_nouns: bool | None = None
