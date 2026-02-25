"""add_fk_tax_results_profile_id

Revision ID: 003_add_results_profile_fk
Revises: 002_add_chat_history
Create Date: 2026-02-23 00:00:00.000000 UTC

Adds a proper FOREIGN KEY constraint from tax_results.profile_id → profiles.id
with ON DELETE CASCADE so orphaned tax_result rows are prevented at the DB level.

Migration 001 created the unique index on tax_results.profile_id but omitted the
FK constraint. This migration adds it without touching any data.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_add_results_profile_fk"
down_revision: Union[str, None] = "002_add_chat_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key(
        constraint_name="fk_tax_results_profile_id",
        source_table="tax_results",
        referent_table="profiles",
        local_cols=["profile_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        constraint_name="fk_tax_results_profile_id",
        table_name="tax_results",
        type_="foreignkey",
    )
