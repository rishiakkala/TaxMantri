"""add_session_events

Revision ID: 004_add_session_events
Revises: 003_add_results_profile_fk
Create Date: 2026-02-24 00:00:00.000000 UTC

Creates the session_events table for UI interaction tracking.
One row per frontend event (tab_click, page_view, pdf_download, regime_compare).
Used by GET /api/session/summary to derive session metrics and build LLM context.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_add_session_events"
down_revision: Union[str, None] = "003_add_results_profile_fk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session_events",
        sa.Column("id", sa.String(36), nullable=False, comment="UUID row identifier"),
        sa.Column(
            "session_id",
            sa.String(36),
            nullable=False,
            comment="Session identifier — groups events by user session",
        ),
        sa.Column(
            "event_type",
            sa.String(50),
            nullable=False,
            comment="Category of UI action: tab_click, page_view, pdf_download, regime_compare",
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(),
            nullable=False,
            comment="Structured event context. Must not contain PAN or taxpayer name.",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_session_events_session_id",
        "session_events",
        ["session_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_session_events_session_id", table_name="session_events")
    op.drop_table("session_events")
