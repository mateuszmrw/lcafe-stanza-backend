import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class LanguageResponse(BaseModel):
    id: int
    code: str
    name: str
    flag_emoji: Optional[str]
    is_active: bool

    model_config = {"from_attributes": True}


class LanguageCreateRequest(BaseModel):
    code: str
    name: str
    flag_emoji: Optional[str] = None


class LanguageUpdateRequest(BaseModel):
    name: Optional[str] = None
    flag_emoji: Optional[str] = None
    is_active: Optional[bool] = None


class NlpConfigResponse(BaseModel):
    language_id: int
    provider_id: uuid.UUID
    config: dict

    model_config = {"from_attributes": True}


class NlpConfigUpdateRequest(BaseModel):
    provider_id: uuid.UUID
    config: dict = {}


class ProviderResponse(BaseModel):
    id: uuid.UUID
    type: str
    slug: str
    name: str
    description: Optional[str]
    is_builtin: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ProviderPatchRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class UserAdminResponse(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime
    proficiency_level: Optional[str] = None
    native_language_code: Optional[str] = None

    model_config = {"from_attributes": True}


class UserAdminUpdateRequest(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None
    proficiency_level: Optional[str] = None
    native_language_code: Optional[str] = None

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("user", "admin"):
            raise ValueError("role must be 'user' or 'admin'")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v

    @field_validator("proficiency_level")
    @classmethod
    def proficiency_must_be_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("A1", "A2", "B1", "B2", "C1", "C2"):
            raise ValueError("proficiency_level must be A1–C2")
        return v


class UserAdminCreateRequest(BaseModel):
    email: str
    username: str
    password: str
    role: str = "user"
    proficiency_level: Optional[str] = None
    native_language_code: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: str) -> str:
        if v not in ("user", "admin"):
            raise ValueError("role must be 'user' or 'admin'")
        return v
