from pydantic import BaseModel


class UserCreate(BaseModel):
    email: str
    username: str
    password: str  # plain text — hashed in UserService.register


class UserUpdate(BaseModel):
    username: str | None = None
    password: str | None = None  # plain text — hashed in UserService.update if provided
