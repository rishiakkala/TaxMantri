"""initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-02-22 12:00:00.000000 UTC

Creates the three core tables:
  - profiles      (UserFinancialProfile storage, JSONB blob)
  - tax_results   (TaxResult storage, JSONB blob + denormalized regime column)
  - sessions      (Wizard session state, JSONB blob)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- profiles table ---
    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False, comment="UUID primary key — matches UserFinancialProfile.profile_id"),
        sa.Column("session_id", sa.String(length=36), nullable=False, comment="Session that created this profile — used for wizard flow lookup"),
        sa.Column("profile_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment="Full UserFinancialProfile serialized as JSONB. All financial data in blob."),
        sa.Column("input_method", sa.String(length=10), nullable=False, comment="'ocr' or 'manual' — mirrors InputMethod enum"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_profiles_session_id"), "profiles", ["session_id"], unique=False)

    # --- tax_results table ---
    op.create_table(
        "tax_results",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=False), nullable=False, comment="References profiles.id — one-to-one relationship"),
        sa.Column("result_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment="Full TaxResult serialized as JSONB"),
        sa.Column("recommended_regime", sa.String(length=3), nullable=False, comment="'old' or 'new' — denormalized for analytics queries"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id"),
    )
    op.create_index(op.f("ix_tax_results_profile_id"), "tax_results", ["profile_id"], unique=False)

    # --- sessions table ---
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=36), nullable=False, comment="Session UUID — matches the Redis key 'session:{id}'"),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment="Wizard progress state. Must not contain PAN or taxpayer name."),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("sessions")
    op.drop_index(op.f("ix_tax_results_profile_id"), table_name="tax_results")
    op.drop_table("tax_results")
    op.drop_index(op.f("ix_profiles_session_id"), table_name="profiles")
    op.drop_table("profiles")
