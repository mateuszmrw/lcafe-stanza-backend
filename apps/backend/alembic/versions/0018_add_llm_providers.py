"""Add openai and claude as LLM providers

Revision ID: 0018
Revises: 0017
Create Date: 2026-04-10
"""

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO providers (type, slug, name, description, is_builtin)
        VALUES
          ('llm', 'openai', 'OpenAI', 'OpenAI GPT models for grammar explanation', true),
          ('llm', 'claude', 'Claude', 'Anthropic Claude models for grammar explanation', true)
        ON CONFLICT (type, slug) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM providers WHERE type = 'llm' AND slug IN ('openai', 'claude')")
