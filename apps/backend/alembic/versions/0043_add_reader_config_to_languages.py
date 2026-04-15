"""add reader_config to languages

Revision ID: 0043
Revises: 0042
Create Date: 2026-04-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0043"
down_revision = "0042"
branch_labels = None
depends_on = None

# Sensible per-language defaults for reader panel display.
# Keys match ReaderConfig fields. Missing keys fall back to the model defaults.
_LANGUAGE_DEFAULTS: dict[str, dict] = {
    "ru": {"show_reading": False, "show_case": True, "show_case_question": True, "show_mood": False, "show_dep_rel": False, "show_gender": True, "show_feats": True},
    "pl": {"show_reading": False, "show_case": True, "show_case_question": True, "show_mood": False, "show_dep_rel": False, "show_gender": True, "show_feats": True},
    "uk": {"show_reading": False, "show_case": True, "show_case_question": True, "show_mood": False, "show_dep_rel": False, "show_gender": True, "show_feats": True},
    "cs": {"show_reading": False, "show_case": True, "show_case_question": True, "show_mood": False, "show_dep_rel": False, "show_gender": True, "show_feats": True},
    "sk": {"show_reading": False, "show_case": True, "show_case_question": True, "show_mood": False, "show_dep_rel": False, "show_gender": True, "show_feats": True},
    "de": {"show_reading": False, "show_case": True, "show_case_question": True, "show_mood": False, "show_dep_rel": False, "show_gender": True, "show_feats": False},
    "la": {"show_reading": False, "show_case": True, "show_case_question": False, "show_mood": True,  "show_dep_rel": False, "show_gender": True, "show_feats": True},
    "fi": {"show_reading": False, "show_case": True, "show_case_question": False, "show_mood": False, "show_dep_rel": False, "show_gender": False,"show_feats": True},
    "et": {"show_reading": False, "show_case": True, "show_case_question": False, "show_mood": False, "show_dep_rel": False, "show_gender": False,"show_feats": True},
    "fr": {"show_reading": False, "show_case": False, "show_case_question": False, "show_mood": True,  "show_dep_rel": False, "show_gender": True, "show_feats": False},
    "es": {"show_reading": False, "show_case": False, "show_case_question": False, "show_mood": True,  "show_dep_rel": False, "show_gender": True, "show_feats": False},
    "it": {"show_reading": False, "show_case": False, "show_case_question": False, "show_mood": True,  "show_dep_rel": False, "show_gender": True, "show_feats": False},
    "pt": {"show_reading": False, "show_case": False, "show_case_question": False, "show_mood": True,  "show_dep_rel": False, "show_gender": True, "show_feats": False},
    "zh": {"show_reading": True,  "show_case": False, "show_case_question": False, "show_mood": False, "show_dep_rel": True,  "show_gender": False,"show_feats": False},
    "ja": {"show_reading": True,  "show_case": False, "show_case_question": False, "show_mood": False, "show_dep_rel": True,  "show_gender": False,"show_feats": False},
    "ko": {"show_reading": False, "show_case": False, "show_case_question": False, "show_mood": False, "show_dep_rel": True,  "show_gender": False,"show_feats": False},
    "en": {"show_reading": False, "show_case": False, "show_case_question": False, "show_mood": False, "show_dep_rel": False, "show_gender": False,"show_feats": False},
}


def upgrade() -> None:
    op.add_column(
        "languages",
        sa.Column("reader_config", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    # Backfill per-language defaults for any languages already in the DB
    conn = op.get_bind()
    for code, cfg in _LANGUAGE_DEFAULTS.items():
        import json
        conn.execute(
            sa.text("UPDATE languages SET reader_config = :cfg WHERE code = :code"),
            {"cfg": json.dumps(cfg), "code": code},
        )


def downgrade() -> None:
    op.drop_column("languages", "reader_config")
