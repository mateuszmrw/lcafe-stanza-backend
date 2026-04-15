import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, require_admin
from src.domain.dictionary.parser_factory import get_parser, supported_slugs
from src.infrastructure.db.models.dictionary_entries import DictionaryEntry as DictionaryEntryModel
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.dictionary_entry_repo import DictionaryEntryRepository
from src.infrastructure.db.repositories.dictionary_sources_repo import DictionarySourcesRepository
from src.infrastructure.cc_cedict.repository import CcCedictRepository
from src.infrastructure.dict_cc.repository import DictCcRepository
from src.infrastructure.krdict.repository import KrdictRepository
from src.infrastructure.openrussian.repository import OpenRussianRepository

router = APIRouter(prefix="/admin/dictionary", tags=["admin"])
_entry_repo = DictionaryEntryRepository()
_sources_repo = DictionarySourcesRepository()
_openrussian_repo = OpenRussianRepository()
_cc_cedict_repo = CcCedictRepository()
_dict_cc_repo = DictCcRepository()
_krdict_repo = KrdictRepository()

# Slugs that use their own storage table instead of dictionary_entries
_CUSTOM_REPOS = {
    "openrussian": _openrussian_repo,
    "cc-cedict": _cc_cedict_repo,
    "dict.cc": _dict_cc_repo,
    "krdict": _krdict_repo,
}


async def _count_for_source(session: AsyncSession, slug: str) -> int:
    repo = _CUSTOM_REPOS.get(slug)
    if repo:
        return await repo.count(session)
    return await _entry_repo.count_by_source_dict(session, slug)


async def _delete_for_source(session: AsyncSession, slug: str) -> None:
    repo = _CUSTOM_REPOS.get(slug)
    if repo:
        await repo.delete_all(session)
    else:
        await _entry_repo.delete_by_source_dict(session, slug)

_BATCH_SIZE = 1000


# ── Schemas ────────────────────────────────────────────────────────────────────


class DictionaryPairStats(BaseModel):
    source_lang: str
    target_lang: str
    entry_count: int


class UploadResult(BaseModel):
    source_lang: str
    target_lang: str
    source_dict: str
    inserted: int
    deleted: int


class DictionarySourceResponse(BaseModel):
    slug: str
    name: str
    description: str | None
    supported_pairs: list[dict]
    priority: int
    is_active: bool
    entry_count: int


class DictionarySourceCreate(BaseModel):
    slug: str
    name: str
    description: str | None = None
    supported_pairs: list[dict] = []
    priority: int = 5


class DictionarySourceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    priority: int | None = None
    is_active: bool | None = None
    supported_pairs: list[dict] | None = None


# ── Language pair stats (existing) ────────────────────────────────────────────


@router.get("/stats", response_model=list[DictionaryPairStats])
async def get_dictionary_stats(
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> list[DictionaryPairStats]:
    """Entry counts per source→target language pair."""
    pairs = await _entry_repo.list_language_pairs(session)
    return [
        DictionaryPairStats(source_lang=src, target_lang=tgt, entry_count=cnt)
        for src, tgt, cnt in pairs
    ]


# ── Dictionary sources CRUD ────────────────────────────────────────────────────


@router.get("/sources", response_model=list[DictionarySourceResponse])
async def list_sources(
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> list[DictionarySourceResponse]:
    """List all registered dictionary sources with their entry counts."""
    sources = await _sources_repo.list_all(session)
    result = []
    for source in sources:
        count = await _count_for_source(session, source.slug)
        result.append(
            DictionarySourceResponse(
                slug=source.slug,
                name=source.name,
                description=source.description,
                supported_pairs=source.supported_pairs,
                priority=source.priority,
                is_active=source.is_active,
                entry_count=count,
            )
        )
    return result


@router.post("/sources", response_model=DictionarySourceResponse, status_code=201)
async def create_source(
    body: DictionarySourceCreate,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> DictionarySourceResponse:
    """Register a new dictionary source (e.g. before importing its data)."""
    existing = await _sources_repo.get_by_slug(session, body.slug)
    if existing:
        raise HTTPException(status_code=409, detail=f"Source '{body.slug}' already exists")

    source = await _sources_repo.create(
        session,
        slug=body.slug,
        name=body.name,
        description=body.description,
        supported_pairs=body.supported_pairs,
        priority=body.priority,
    )
    await session.commit()
    return DictionarySourceResponse(
        slug=source.slug,
        name=source.name,
        description=source.description,
        supported_pairs=source.supported_pairs,
        priority=source.priority,
        is_active=source.is_active,
        entry_count=0,
    )


@router.patch("/sources/{slug}", response_model=DictionarySourceResponse)
async def update_source(
    slug: str,
    body: DictionarySourceUpdate,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> DictionarySourceResponse:
    """Update priority, active flag, or metadata for a dictionary source."""
    source = await _sources_repo.update(
        session,
        slug=slug,
        priority=body.priority,
        is_active=body.is_active,
        name=body.name,
        description=body.description,
        supported_pairs=body.supported_pairs,
    )
    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{slug}' not found")
    await session.commit()
    count = await _count_for_source(session, slug)
    return DictionarySourceResponse(
        slug=source.slug,
        name=source.name,
        description=source.description,
        supported_pairs=source.supported_pairs,
        priority=source.priority,
        is_active=source.is_active,
        entry_count=count,
    )


@router.delete("/sources/{slug}", status_code=204)
async def delete_source(
    slug: str,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete a dictionary source and all of its entries."""
    source = await _sources_repo.get_by_slug(session, slug)
    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{slug}' not found")
    await _delete_for_source(session, slug)
    await _sources_repo.delete(session, slug)
    await session.commit()


# ── Upload ─────────────────────────────────────────────────────────────────────


@router.post("/upload/{source_lang}/{target_lang}", response_model=UploadResult)
async def upload_dictionary(
    source_lang: str,
    target_lang: str,
    file: UploadFile,
    source_slug: str = "wiktionary",
    replace: bool = True,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> UploadResult:
    """Upload a dictionary file for a source→target language pair.

    source_slug selects the parser (default: "wiktionary").
    Supported slugs are determined by the parser factory.
    replace=true (default) deletes existing entries for this source+pair first.
    """
    parse = get_parser(source_slug)
    if parse is None:
        raise HTTPException(
            status_code=400,
            detail=f"No parser registered for source_slug='{source_slug}'. "
                   f"Supported: {supported_slugs()}",
        )

    src = source_lang.lower()
    tgt = target_lang.lower()
    deleted = 0

    content = await file.read()
    rows = parse(content, src, tgt)

    custom_repo = _CUSTOM_REPOS.get(source_slug)
    if custom_repo:
        if replace:
            deleted = await custom_repo.delete_all(session)
        inserted = 0
        for i in range(0, len(rows), _BATCH_SIZE):
            inserted += await custom_repo.bulk_insert(session, rows[i : i + _BATCH_SIZE])
    else:
        if replace:
            result = await session.execute(
                sa.delete(DictionaryEntryModel).where(
                    DictionaryEntryModel.source_lang == src,
                    DictionaryEntryModel.target_lang == tgt,
                    DictionaryEntryModel.source_dict == source_slug,
                )
            )
            deleted = result.rowcount
        for row in rows:
            row["source_dict"] = source_slug
        inserted = 0
        for i in range(0, len(rows), _BATCH_SIZE):
            inserted += await _entry_repo.bulk_insert(session, rows[i : i + _BATCH_SIZE])

    await session.commit()
    return UploadResult(
        source_lang=src,
        target_lang=tgt,
        source_dict=source_slug,
        inserted=inserted,
        deleted=deleted,
    )


# ── Delete pair (existing, kept for compatibility) ────────────────────────────


@router.delete("/{source_lang}/{target_lang}", response_model=UploadResult)
async def delete_dictionary_pair(
    source_lang: str,
    target_lang: str,
    source_slug: str = "wiktionary",
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> UploadResult:
    """Delete entries for a specific source→target pair (and optionally a specific dict source)."""
    src = source_lang.lower()
    tgt = target_lang.lower()
    deleted = await _entry_repo.delete_pair(session, src, tgt)
    await session.commit()
    return UploadResult(
        source_lang=src, target_lang=tgt, source_dict=source_slug,
        inserted=0, deleted=deleted,
    )
