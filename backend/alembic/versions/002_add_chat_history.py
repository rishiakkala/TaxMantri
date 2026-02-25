"""add_chat_history

Revision ID: 002_add_chat_history
Revises: 001_initial_schema
Create Date: 2026-02-23 00:00:00.000000 UTC

Adds the chat_history table for RAG Q&A session persistence.
One row per Q&A exchange. Indexed by session_id for fast history retrieval.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_add_chat_history"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_history",
        sa.Column("id", sa.String(36), nullable=False, comment="UUID row identifier"),
        sa.Column(
            "session_id", sa.String(36), nullable=False,
            comment="Session identifier — groups messages by user session",
        ),
        sa.Column("question", sa.Text(), nullable=False, comment="User question text"),
        sa.Column("answer", sa.Text(), nullable=False, comment="Generated answer text"),
        sa.Column(
            "confidence", sa.String(4), nullable=False,
            comment="'high' or 'low' from ConfidenceLevel enum",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chat_history_session_id",
        "chat_history",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_chat_history_session_id", table_name="chat_history")
    op.drop_table("chat_history")
