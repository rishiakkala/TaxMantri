"""
models/tax_result.py — SQLAlchemy ORM model for tax calculation results.

Table: tax_results
One-to-one relationship with profiles (profile_id unique index).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class TaxResultORM(Base):
    """
    ORM model for a complete tax regime comparison result.

    result_data: Full TaxResult serialized as JSONB (both regimes, suggestions, rationale).
    recommended_regime: Denormalized for fast querying and analytics without parsing JSONB.
    """
    __tablename__ = "tax_results"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    profile_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        nullable=False,
        index=True,
        unique=True,     # One result per profile
        comment="References profiles.id — one-to-one relationship",
    )
    result_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Full TaxResult serialized as JSONB",
    )
    recommended_regime: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        comment="'old' or 'new' — denormalized for analytics queries",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
