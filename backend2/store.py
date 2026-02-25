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
