
from pydantic import BaseModel

class ImportTextRequest(BaseModel):
    chunkSize: int
    importText: str

class GetWebsiteTextRequest(BaseModel):
    url: str