import os
from datetime import datetime
from typing import Optional

from arq import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_arq_pool, get_db, require_admin
from src.core.config import get_settings
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.cognate_repo import CognateRepository

router = APIRouter(prefix="/admin/cognates", tags=["admin"])
_cognate_repo = CognateRepository()


class CognateUploadResponse(BaseModel):
    enqueued: bool
    filename: str


class CognatePairStatus(BaseModel):
    l2: str
    l1_codes: list[str]


class CognateStatusResponse(BaseModel):
    row_count: int
    last_imported_at: Optional[datetime]
    pairs: list[CognatePairStatus]


@router.post("/upload", response_model=CognateUploadResponse)
async def upload_cognates(
    file: UploadFile,
    _: User = Depends(require_admin),
    arq: ArqRedis = Depends(get_arq_pool),
) -> CognateUploadResponse:
    """Accept a TSV cognate pairs file, save it to disk, and enqueue the import worker task."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    if not file.filename.endswith((".tsv", ".txt")):
        raise HTTPException(status_code=400, detail="Expected a .tsv or .txt file")

    settings = get_settings()
    max_bytes = settings.max_upload_bytes
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max {max_bytes // (1024 * 1024)} MB.",
        )

    cognates_dir = os.path.join(settings.storage_root, "cognates")
    os.makedirs(cognates_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = os.path.basename(file.filename).replace(" ", "_")
    dest_path = os.path.join(cognates_dir, f"{timestamp}_{safe_filename}")

    with open(dest_path, "wb") as f:
        f.write(content)

    await arq.enqueue_job("import_cognate_pairs", dest_path)
    return CognateUploadResponse(enqueued=True, filename=safe_filename)


@router.get("/status", response_model=CognateStatusResponse)
async def get_cognate_status(
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> CognateStatusResponse:
    """Return cognate table row count, last import time, and supported language pairs."""
    status = await _cognate_repo.get_status(session)
    return CognateStatusResponse(
        row_count=status["row_count"],
        last_imported_at=status["last_imported_at"],
        pairs=[CognatePairStatus(l2=p["l2"], l1_codes=p["l1_codes"]) for p in status["pairs"]],
    )
