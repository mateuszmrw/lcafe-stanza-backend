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


class FrequencyLanguageStat(BaseModel):
    language_code: str
    entry_count: int


class ImportResult(BaseModel):
    language_code: str
    inserted: int
    deleted: int


@router.get("/stats", response_model=list[FrequencyLanguageStat])
async def list_frequency_stats(
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> list[FrequencyLanguageStat]:
    """Return entry counts for every loaded frequency language."""
    rows = await _freq_repo.list_all_stats(session)
    return [FrequencyLanguageStat(language_code=lang, entry_count=cnt) for lang, cnt in rows]


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
    auto_rank = 0

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            parts = line.split(",")
        if not parts:
            continue

        lemma = parts[0].strip().lower()
        if not lemma:
            continue

        # Parse the numeric column before accepting the row.
        # If it's not a valid number this is a header row (e.g. "word,count") — skip it.
        per_million: float | None = None
        if len(parts) >= 2:
            try:
                per_million = float(parts[1].strip())
            except ValueError:
                continue  # non-numeric second column → header row

        # The file is sorted most-common-first; use row position as rank.
        auto_rank += 1

        batch.append({
            "id": uuid.uuid4(),
            "language_code": lang,
            "lemma": lemma,
            "rank": auto_rank,
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
