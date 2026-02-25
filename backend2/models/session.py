"""
models/session.py — SQLAlchemy ORM model for wizard session state.

Table: sessions

Dual-store pattern:
  - Redis (primary):    TTL-enforced 24h wizard progress cache (fast)
  - PostgreSQL (here):  Durable fallback / audit trail (persistent across Redis restarts)

Routes use Redis first for session reads; PostgreSQL is synced on writes.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class SessionORM(Base):
    """
    ORM model for user session / wizard progress state.

    data: Arbitrary JSON dict — wizard step number, partial profile fields, etc.
          Must NOT contain PAN, names, or other directly identifying data.
    """
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="Session UUID — matches the Redis key 'session:{id}'",
    )
    data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Wizard progress state. Must not contain PAN or taxpayer name.",
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
