"""Remove Claude as an LLM provider — OpenAI-only cascade

Revision ID: 0054
Revises: 0053
Create Date: 2026-04-16

The LLM integration was simplified to OpenAI-only. Delete any stored system
API key for Claude first (no ON DELETE CASCADE on system_api_keys.provider_id),
then remove the provider row itself.
"""

from alembic import op

revision = "0054"
down_revision = "0053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM system_api_keys
        WHERE provider_id IN (
            SELECT id FROM providers WHERE type = 'llm' AND slug = 'claude'
        )
        """
    )
    op.execute("DELETE FROM providers WHERE type = 'llm' AND slug = 'claude'")


def downgrade() -> None:
    op.execute(
        """
        INSERT INTO providers (type, slug, name, description, is_builtin)
        VALUES ('llm', 'claude', 'Claude', 'Anthropic Claude models for grammar explanation', true)
        ON CONFLICT (type, slug) DO NOTHING
        """
    )
