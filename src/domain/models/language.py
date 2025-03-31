from pydantic import BaseModel

class InstallLanguageRequest(BaseModel):
    language: str

