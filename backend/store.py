"""
store.py — Data access facade for TaxMantri.

Provides a consistent, high-level API for persisting and retrieving domain objects.
All agent routes use these functions — no agent touches SQLAlchemy directly.

Design principles:
  - All functions are async and accept an AsyncSession parameter
  - No raw SQL: ORM-only queries
  - Logs only profile_id / session_id — never salary values, PAN, or names (CLAUDE.md rule)
  - Returns domain Pydantic objects (not ORM instances) so callers are persistence-agnostic

Function signatures mirror the CLAUDE.md Task 1.5 in-memory store API
so future phases never need to change how they call persistence.
"""
import logging
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.evaluator_agent.schemas import TaxResult
from backend.agents.input_agent.schemas import UserFinancialProfile
from backend.models.chat_history import ChatHistoryORM
from backend.models.profile import ProfileORM
from backend.models.session import SessionORM
from backend.models.session_event import SessionEventORM
from backend.models.tax_result import TaxResultORM

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Profile operations
# ---------------------------------------------------------------------------

async def save_profile(
    db: AsyncSession,
    profile: UserFinancialProfile,
    session_id: str = "",
) -> str:
    """
    Persist a UserFinancialProfile to the profiles table.

    Returns the profile_id (either supplied or auto-generated).
    Uses flush() (not commit()) — caller / get_db() dependency handles commit.
    """
    orm = ProfileORM(
        id=profile.profile_id,
        session_id=session_id,
        profile_data=profile.model_dump(),
        input_method=profile.input_method.value,
    )
    db.add(orm)
    await db.flush()
    logger.info("Saved profile profile_id=%s input_method=%s", profile.profile_id, profile.input_method.value)
    return profile.profile_id


async def get_profile(
    db: AsyncSession,
    profile_id: str,
) -> Optional[UserFinancialProfile]:
    """
    Retrieve a UserFinancialProfile by profile_id.
    Returns None if no profile found (caller raises 404).
    """
    result = await db.execute(
        select(ProfileORM).where(ProfileORM.id == profile_id)
    )
    orm = result.scalar_one_or_none()
    if orm is None:
        return None
    return UserFinancialProfile.model_validate(orm.profile_data)


# ---------------------------------------------------------------------------
# Tax result operations
# ---------------------------------------------------------------------------

async def save_result(db: AsyncSession, result: TaxResult) -> None:
    """
    Persist a TaxResult linked to a profile_id.
    One result per profile (unique constraint on profile_id).
    If a result already exists for this profile_id, it is replaced.
    """
    # Check for existing result to support upsert semantics
    existing = await db.execute(
        select(TaxResultORM).where(TaxResultORM.profile_id == result.profile_id)
    )
    orm = existing.scalar_one_or_none()

    if orm is None:
        orm = TaxResultORM(
            profile_id=result.profile_id,
            result_data=result.model_dump(),
            recommended_regime=result.recommended_regime,
        )
        db.add(orm)
    else:
        orm.result_data = result.model_dump()
        orm.recommended_regime = result.recommended_regime

    await db.flush()
    logger.info(
        "Saved tax result profile_id=%s recommended_regime=%s",
        result.profile_id,
        result.recommended_regime,
    )


async def get_result(
    db: AsyncSession,
    profile_id: str,
) -> Optional[TaxResult]:
    """
    Retrieve a TaxResult by profile_id.
    Returns None if calculation hasn't been run yet.
    """
    result = await db.execute(
        select(TaxResultORM).where(TaxResultORM.profile_id == profile_id)
    )
    orm = result.scalar_one_or_none()
    if orm is None:
        return None
    return TaxResult.model_validate(orm.result_data)


# ---------------------------------------------------------------------------
# Session state operations
# ---------------------------------------------------------------------------

async def get_session(
    db: AsyncSession,
    session_id: str,
) -> Optional[dict]:
    """
    Retrieve session wizard progress from PostgreSQL.
    Returns None if session not found.
    Note: Redis (cache.py) is the primary session store; this is the durable fallback.
    """
    result = await db.execute(
        select(SessionORM).where(SessionORM.id == session_id)
    )
    orm = result.scalar_one_or_none()
    if orm is None:
        return None
    return orm.data


async def set_session(
    db: AsyncSession,
    session_id: str,
    data: dict,
) -> None:
    """
    Upsert session wizard progress in PostgreSQL.
    Resets updated_at on every write.
    Note: Caller is also responsible for writing to Redis (cache.py) for TTL management.
    """
    result = await db.execute(
        select(SessionORM).where(SessionORM.id == session_id)
    )
    orm = result.scalar_one_or_none()

    if orm is None:
        orm = SessionORM(id=session_id, data=data)
        db.add(orm)
    else:
        orm.data = data  # SQLAlchemy detects mutation and marks dirty

    await db.flush()
    logger.info("Updated session session_id=%s", session_id)


# ---------------------------------------------------------------------------
# Chat history operations (Phase 5 — RAG-07)
# ---------------------------------------------------------------------------

async def save_chat_message(
    db: AsyncSession,
    session_id: str,
    question: str,
    answer: str,
    confidence: str,
) -> None:
    """
    Persist a single Q&A exchange to the chat_history table.
    Called on EVERY response — including cache hits and low-confidence answers.
    Logs only session_id (not question text — potential PII per CLAUDE.md rule).
    """
    orm = ChatHistoryORM(
        id=str(uuid.uuid4()),
        session_id=session_id,
        question=question,
        answer=answer,
        confidence=confidence,
    )
    db.add(orm)
    await db.flush()
    logger.info("Saved chat message session_id=%s confidence=%s", session_id, confidence)


async def get_chat_history(
    db: AsyncSession,
    session_id: str,
) -> list[dict]:
    """
    Retrieve all Q&A exchanges for a session, ordered by created_at ascending
    (oldest first — chronological message order for UI display).
    Returns empty list if session has no prior messages.
    """
    result = await db.execute(
        select(ChatHistoryORM)
        .where(ChatHistoryORM.session_id == session_id)
        .order_by(ChatHistoryORM.created_at.asc())
    )
    rows = result.scalars().all()
    return [
        {
            "question": row.question,
            "answer": row.answer,
            "confidence": row.confidence,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Session event operations
# ---------------------------------------------------------------------------

async def save_session_event(
    db: AsyncSession,
    session_id: str,
    event_type: str,
    payload: dict,
) -> None:
    """
    Persist a single UI interaction event to the session_events table.
    payload must be PII-free — only structural data like tab names or regime strings.
    Logs only session_id and event_type (not payload values — may contain user choices).
    """
    orm = SessionEventORM(
        id=str(uuid.uuid4()),
        session_id=session_id,
        event_type=event_type,
        payload=payload,
    )
    db.add(orm)
    await db.flush()
    logger.info("Saved session event session_id=%s event_type=%s", session_id, event_type)


async def get_session_events(
    db: AsyncSession,
    session_id: str,
) -> list[dict]:
    """
    Retrieve all UI events for a session, ordered by created_at ascending.
    Returns empty list if no events exist.
    """
    result = await db.execute(
        select(SessionEventORM)
        .where(SessionEventORM.session_id == session_id)
        .order_by(SessionEventORM.created_at.asc())
    )
    rows = result.scalars().all()
    return [
        {
            "event_type": row.event_type,
            "payload": row.payload,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


# Topic keyword mapping — used by get_session_summary to tag questions by subject
_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "HRA": ["hra", "house rent", "rent allowance"],
    "80C": ["80c", "ppf", "elss", "nsc", "life insurance"],
    "NPS": ["nps", "national pension", "80ccd"],
    "80D": ["80d", "health insurance", "medical insurance"],
    "Home Loan": ["home loan", "housing loan", "section 24", "interest on loan"],
    "Standard Deduction": ["standard deduction"],
    "Regime": ["regime", "old regime", "new regime"],
    "Tax Slabs": ["slab", "tax rate", "income tax rate"],
    "ITR-1": ["itr", "itr-1", "income tax return", "filing"],
    "Capital Gains": ["capital gain", "ltcg", "stcg"],
}


def _extract_topics(questions: list[str]) -> list[str]:
    """Return topic labels that appear in any of the questions (case-insensitive)."""
    combined = " ".join(questions).lower()
    return [
        topic
        for topic, keywords in _TOPIC_KEYWORDS.items()
        if any(kw in combined for kw in keywords)
    ]


async def get_session_summary(
    db: AsyncSession,
    session_id: str,
) -> dict:
    """
    Derive and return a structured session summary from chat_history + session_events.

    Computed metrics:
      - question_count, high_confidence_pct
      - session_duration_s (first_event → last_event across both tables)
      - topics_asked (keyword-matched against chat questions)
      - tabs_visited, pdf_downloaded, regime_compared, pages_visited
    """
    chat_rows = await get_chat_history(db, session_id)
    event_rows = await get_session_events(db, session_id)

    # ── Chat metrics ────────────────────────────────────────────────────────
    question_count = len(chat_rows)
    high_count = sum(1 for r in chat_rows if r["confidence"] == "high")
    high_confidence_pct = round(high_count / question_count * 100, 1) if question_count else 0.0
    topics_asked = _extract_topics([r["question"] for r in chat_rows])

    # ── UI event metrics ─────────────────────────────────────────────────────
    tabs_visited = list({
        e["payload"].get("tab")
        for e in event_rows
        if e["event_type"] == "tab_click" and e["payload"].get("tab")
    })
    pdf_downloaded = any(e["event_type"] == "pdf_download" for e in event_rows)
    regime_compared = any(e["event_type"] == "regime_compare" for e in event_rows)
    pages_visited = list({
        e["payload"].get("page")
        for e in event_rows
        if e["event_type"] == "page_view" and e["payload"].get("page")
    })

    # ── Session duration ─────────────────────────────────────────────────────
    all_timestamps = [r["created_at"] for r in chat_rows] + [e["created_at"] for e in event_rows]
    started_at = min(all_timestamps) if all_timestamps else None
    last_active_at = max(all_timestamps) if all_timestamps else None
    if started_at and last_active_at:
        from datetime import datetime as _dt
        fmt = "%Y-%m-%dT%H:%M:%S.%f%z" if "." in started_at else "%Y-%m-%dT%H:%M:%S%z"
        try:
            t0 = _dt.fromisoformat(started_at)
            t1 = _dt.fromisoformat(last_active_at)
            duration_s = int((t1 - t0).total_seconds())
        except ValueError:
            duration_s = 0
    else:
        duration_s = 0

    return {
        "session_id": session_id,
        "started_at": started_at,
        "last_active_at": last_active_at,
        "duration_seconds": duration_s,
        "question_count": question_count,
        "high_confidence_pct": high_confidence_pct,
        "topics_asked": topics_asked,
        "tabs_visited": tabs_visited,
        "pdf_downloaded": pdf_downloaded,
        "regime_compared": regime_compared,
        "pages_visited": pages_visited,
        "chat_history": chat_rows,
    }
