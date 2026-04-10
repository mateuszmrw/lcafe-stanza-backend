import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, require_admin
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.word_frequency_repo import WordFrequencyRepository

router = APIRouter(prefix="/admin/frequencies", tags=["admin"])
_freq_repo = WordFrequencyRepository()

_BATCH_SIZE = 2000


class FrequencyStats(BaseModel):
    language_code: str
    has_entries: bool


class ImportResult(BaseModel):
    language_code: str
    inserted: int
    deleted: int


@router.get("/stats/{language_code}", response_model=FrequencyStats)
async def get_frequency_stats(
    language_code: str,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> FrequencyStats:
    has = await _freq_repo.has_entries(session, language_code.lower())
    return FrequencyStats(language_code=language_code.lower(), has_entries=has)


@router.post("/upload/{language_code}", response_model=ImportResult)
async def upload_frequencies(
    language_code: str,
    file: UploadFile,
    replace: bool = True,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> ImportResult:
    """Upload a TSV frequency list for a language.

    Expected format (one entry per line, tab-separated):
        lemma<TAB>rank[<TAB>per_million]

    Lines starting with '#' are treated as comments and skipped.
    A header line (lemma\\trank or lemma\\trank\\tper_million) is auto-detected and skipped.
    ?replace=true (default) deletes existing entries for the language first.
    """
    if not file.filename or not file.filename.endswith((".tsv", ".txt", ".csv")):
        raise HTTPException(status_code=400, detail="Expected a .tsv, .txt, or .csv file")

    lang = language_code.lower()
    deleted = 0

    if replace:
        deleted = await _freq_repo.delete_language(session, lang)

    content = await file.read()
    lines = content.decode("utf-8", errors="replace").splitlines()

    inserted = 0
    batch: list[dict] = []

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            parts = line.split(",")
        if len(parts) < 2:
            continue

        lemma = parts[0].strip().lower()
        if not lemma or lemma == "lemma":  # skip header row
            continue

        try:
            rank = int(parts[1].strip())
        except ValueError:
            continue

        per_million: float | None = None
        if len(parts) >= 3:
            try:
                per_million = float(parts[2].strip())
            except ValueError:
                pass

        batch.append({
            "id": uuid.uuid4(),
            "language_code": lang,
            "lemma": lemma,
            "rank": rank,
            "per_million": per_million,
        })

        if len(batch) >= _BATCH_SIZE:
            inserted += await _freq_repo.bulk_upsert(session, batch)
            batch = []

    if batch:
        inserted += await _freq_repo.bulk_upsert(session, batch)

    await session.commit()
    return ImportResult(language_code=lang, inserted=inserted, deleted=deleted)


@router.delete("/{language_code}", response_model=ImportResult)
async def delete_frequencies(
    language_code: str,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> ImportResult:
    """Delete all frequency entries for a language."""
    lang = language_code.lower()
    deleted = await _freq_repo.delete_language(session, lang)
    await session.commit()
    return ImportResult(language_code=lang, inserted=0, deleted=deleted)
