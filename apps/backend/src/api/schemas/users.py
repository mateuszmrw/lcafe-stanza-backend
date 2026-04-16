import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


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
    auto_ignore_proper_nouns: bool = True

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=255)

    @field_validator("username")
    @classmethod
    def _username_not_blank(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("Username cannot be blank")
        return v


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
