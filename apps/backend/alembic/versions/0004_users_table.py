"""Create users table with optional admin seed

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.Text, unique=True, nullable=False),
        sa.Column("username", sa.Text, unique=True, nullable=False),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("role", sa.Text, nullable=False, server_default=sa.text("'user'")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("refresh_token_hash", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    _seed_admin_user()


def _seed_admin_user() -> None:
    try:
        import bcrypt

        from src.core.config import get_settings

        settings = get_settings()
        if not settings.admin_email or not settings.admin_password:
            return

        password_hash = bcrypt.hashpw(
            settings.admin_password.encode(), bcrypt.gensalt()
        ).decode()

        op.execute(
            sa.text(
                """
                INSERT INTO users (email, username, password_hash, role)
                VALUES (:email, :username, :password_hash, 'admin')
                ON CONFLICT (email) DO NOTHING
                """
            ).bindparams(
                email=settings.admin_email,
                username=settings.admin_email.split("@")[0],
                password_hash=password_hash,
            )
        )
    except Exception:
        pass  # admin seed is optional — never fail the migration


def downgrade() -> None:
    op.drop_table("users")
