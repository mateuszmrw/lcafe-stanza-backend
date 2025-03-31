from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    project_name: str = "CafeLingua Stanza Backend"
    debug: bool = False
    languages: list[str] = ["russian", "polish"] 
    use_gpu: bool = False
    model_dir: str = "stanza_resources"

    class Config:
        case_sensitive = True
        env_file = ".env"

@lru_cache
def get_settings() -> Settings:
    return Settings()