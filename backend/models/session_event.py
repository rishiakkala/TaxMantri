"""
models/session_event.py — SQLAlchemy ORM for UI interaction events.

Table: session_events
One row per UI event fired by the frontend (tab_click, page_view, pdf_download, etc.).
Used to build the session_context string injected into the LLM prompt and for the
GET /api/session/summary derived-metrics endpoint.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class SessionEventORM(Base):
    """
    ORM model for a single UI interaction event.

    event_type: category of action — tab_click, page_view, pdf_download, regime_compare.
    payload:    structured context — e.g. {"tab": "deductions"} or {"regime": "new"}.
                Must NOT contain PAN, names, or other PII.
    session_id: indexed for fast per-session retrieval.
    """
    __tablename__ = "session_events"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="UUID row identifier",
    )
    session_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="Session identifier — groups events by user session",
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Category of UI action: tab_click, page_view, pdf_download, regime_compare",
    )
    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Structured event context. Must not contain PAN or taxpayer name.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
