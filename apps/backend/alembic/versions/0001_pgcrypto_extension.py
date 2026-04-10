"""Enable pgcrypto extension

Revision ID: 0001
Revises:
Create Date: 2026-04-09
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")


def downgrade() -> None:
    pass  # intentionally a no-op — dropping pgcrypto could break other DB objects
