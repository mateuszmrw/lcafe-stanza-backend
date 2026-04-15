import json
import re

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, require_admin
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.dictionary_entry_repo import DictionaryEntryRepository

router = APIRouter(prefix="/admin/dictionary", tags=["admin"])
_entry_repo = DictionaryEntryRepository()

_BATCH_SIZE = 1000

# Register/style tags from kaikki.org sense.tags and gloss prefixes like "(informal) ..."
_REGISTER_TAGS = frozenset({
    "informal", "formal", "archaic", "colloquial", "slang", "vulgar",
    "offensive", "regional", "dialectal", "rare", "obsolete", "poetic",
    "literary", "technical", "dated", "historical", "derogatory",
    "figurative", "euphemistic",
})

_LABEL_PREFIX_RE = re.compile(r"^\(([^)]+)\)\s+")


class DictionaryPairStats(BaseModel):
    source_lang: str
    target_lang: str
    entry_count: int


class UploadResult(BaseModel):
    source_lang: str
    target_lang: str
    inserted: int
    deleted: int


@router.get("/stats", response_model=list[DictionaryPairStats])
async def get_dictionary_stats(
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> list[DictionaryPairStats]:
    """Return entry counts per source→target language pair in the local dictionary."""
    pairs = await _entry_repo.list_language_pairs(session)
    return [
        DictionaryPairStats(source_lang=src, target_lang=tgt, entry_count=cnt)
        for src, tgt, cnt in pairs
    ]


@router.post("/upload/{source_lang}/{target_lang}", response_model=UploadResult)
async def upload_dictionary(
    source_lang: str,
    target_lang: str,
    file: UploadFile,
    replace: bool = True,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> UploadResult:
    """Upload a kaikki.org JSONL file for a source→target language pair.

    source_lang: ISO 639-1 code of the language being read (e.g. "ru")
    target_lang: ISO 639-1 code of the language definitions are written in (e.g. "en")

    Each line: JSON with word, pos, senses[].glosses[] fields.
    ?replace=true (default) deletes the existing pair first.
    """
    if not file.filename or not file.filename.endswith((".jsonl", ".json")):
        raise HTTPException(status_code=400, detail="Expected a .jsonl or .json file")

    src = source_lang.lower()
    tgt = target_lang.lower()
    deleted = 0

    if replace:
        deleted = await _entry_repo.delete_pair(session, src, tgt)

    inserted = 0
    batch: list[dict] = []

    content = await file.read()
    for line in content.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        word = obj.get("word", "").strip()
        if not word:
            continue

        pos = obj.get("pos", "")
        glosses: list[str] = []
        all_labels: set[str] = set()
        for sense in obj.get("senses", []):
            # Extract register labels from structured tags
            for tag in sense.get("tags", []):
                t = tag.lower()
                if t in _REGISTER_TAGS:
                    all_labels.add(t)
            for sense_gloss in sense.get("glosses", []):
                # Extract parenthetical labels from gloss prefix, then strip them
                m = _LABEL_PREFIX_RE.match(sense_gloss)
                if m:
                    for part in m.group(1).split(","):
                        t = part.strip().lower()
                        if t in _REGISTER_TAGS:
                            all_labels.add(t)
                    glosses.append(sense_gloss[m.end():])
                else:
                    glosses.append(sense_gloss)

        forms: list[dict] = [
            {"form": f.get("form", ""), "tags": f.get("tags", [])}
            for f in obj.get("forms", [])
            if f.get("form") and f.get("form") not in ("-", "—", "–")
        ]
        etymology = obj.get("etymology_text") or obj.get("etymology") or None

        batch.append({
            "word": word.lower(),
            "source_lang": src,
            "target_lang": tgt,
            "pos": pos,
            "glosses": glosses,
            "forms": forms,
            "etymology": etymology,
            "labels": sorted(all_labels),
        })

        if len(batch) >= _BATCH_SIZE:
            inserted += await _entry_repo.bulk_insert(session, batch)
            batch = []

    if batch:
        inserted += await _entry_repo.bulk_insert(session, batch)

    await session.commit()
    return UploadResult(source_lang=src, target_lang=tgt, inserted=inserted, deleted=deleted)


@router.delete("/{source_lang}/{target_lang}", response_model=UploadResult)
async def delete_dictionary_pair(
    source_lang: str,
    target_lang: str,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> UploadResult:
    """Delete all entries for a specific source→target language pair."""
    src = source_lang.lower()
    tgt = target_lang.lower()
    deleted = await _entry_repo.delete_pair(session, src, tgt)
    await session.commit()
    return UploadResult(source_lang=src, target_lang=tgt, inserted=0, deleted=deleted)
