from fastapi.responses import JSONResponse
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health():
    return JSONResponse(content={"status": "ok"})