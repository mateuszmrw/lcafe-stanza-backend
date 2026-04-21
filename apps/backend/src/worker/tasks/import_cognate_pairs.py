import csv
import logging

from src.infrastructure.db.engine import AsyncSessionFactory
from src.infrastructure.db.repositories.cognate_repo import CognateRepository, _VALID_COGNATE_TYPES

logger = logging.getLogger(__name__)

_cognate_repo = CognateRepository()

_REQUIRED_FIELDS = {"l1_lemma", "l1_language", "l2_lemma", "l2_language", "cognate_type", "source"}
_FLOAT_FIELDS = {"similarity_score", "semantic_score"}


async def import_cognate_pairs(ctx: dict, file_path: str) -> None:
    logger.info("import_cognate_pairs: reading %s", file_path)
    with open(file_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows: list[dict] = []
        skipped = 0
        for line_no, row in enumerate(reader, start=2):
            missing = _REQUIRED_FIELDS - set(row.keys())
            if missing:
                logger.warning("line %d: missing fields %s — skipped", line_no, missing)
                skipped += 1
                continue

            cognate_type = row["cognate_type"].strip()
            if cognate_type not in _VALID_COGNATE_TYPES:
                logger.warning("line %d: invalid cognate_type %r — skipped", line_no, cognate_type)
                skipped += 1
                continue

            record: dict = {
                "l1_lemma": row["l1_lemma"].strip(),
                "l1_language": row["l1_language"].strip(),
                "l2_lemma": row["l2_lemma"].strip(),
                "l2_language": row["l2_language"].strip(),
                "cognate_type": cognate_type,
                "source": row["source"].strip(),
                "l1_meaning": row.get("l1_meaning", "").strip() or None,
                "l2_meaning": row.get("l2_meaning", "").strip() or None,
            }

            for field in _FLOAT_FIELDS:
                raw = row.get(field, "").strip()
                try:
                    record[field] = float(raw) if raw else None
                except ValueError:
                    logger.warning("line %d: invalid %s value %r — set to null", line_no, field, raw)
                    record[field] = None

            if not record["l1_lemma"] or not record["l2_lemma"]:
                logger.warning("line %d: empty lemma — skipped", line_no)
                skipped += 1
                continue

            rows.append(record)

    # CogNet lists the same word pair under multiple synset IDs — deduplicate by PK
    seen: dict[tuple, dict] = {}
    for row in rows:
        key = (row["l1_lemma"], row["l1_language"], row["l2_lemma"], row["l2_language"])
        if key not in seen:
            seen[key] = row
    rows = list(seen.values())

    async with AsyncSessionFactory() as session:
        imported = await _cognate_repo.bulk_upsert(session, rows)

        # Track the languages seen in this import to update last_imported_at
        l2_languages = {r["l2_language"] for r in rows}
        for l2 in l2_languages:
            await _cognate_repo.mark_imported(session, l2)

        await session.commit()

    logger.info(
        "import_cognate_pairs: done — imported=%d skipped=%d total=%d",
        imported,
        skipped,
        imported + skipped,
    )
