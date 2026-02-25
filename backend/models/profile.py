"""
models/profile.py — SQLAlchemy ORM model for user financial profiles.

Table: profiles
Storage strategy: JSONB blob for all financial data.
Rationale: Keeps salary figures inside an opaque blob so SQL query logs
(even with echo=True) never expose individual salary values in WHERE clauses.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class ProfileORM(Base):
    """
    ORM model for a user's financial profile.

    profile_data: Full UserFinancialProfile as JSONB — all monetary fields
                  are inside this blob, NOT in separate queryable columns.
                  PII protection: SQL logs never see salary values in WHERE.

    Phase 3 (INPUT-08) will add pan_hash (SHA-256 hex) as a separate column
    when PAN field is optionally provided by the user.
    """
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="UUID primary key — matches UserFinancialProfile.profile_id",
    )
    session_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="Session that created this profile — used for wizard flow lookup",
    )
    profile_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Full UserFinancialProfile serialized as JSONB. All financial data in blob.",
    )
    input_method: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="'ocr' or 'manual' — mirrors InputMethod enum",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
