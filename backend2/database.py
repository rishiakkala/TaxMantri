"""
database.py — SQLAlchemy 2.0 async engine and session factory.

This module owns ALL database connection infrastructure.
Nothing else in the codebase creates engines or sessions directly.

Usage in routes (via dependency injection):
    from backend.database import get_db
    async def my_route(db: AsyncSession = Depends(get_db)): ...

Usage in store.py (direct call — store manages its own session scope):
    from backend.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session: ...
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.config import settings


# ---------------------------------------------------------------------------
# Declarative base — ALL ORM models inherit from this
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """
    SQLAlchemy declarative base.
    All ORM models in backend/models/ inherit from Base.
    Defined here (not in models/) to prevent circular imports in alembic/env.py.
    """
    pass


# ---------------------------------------------------------------------------
# Async engine — one per application lifetime
# ---------------------------------------------------------------------------
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,      # Logs SQL statements in debug mode (safe: no PII in WHERE clauses)
    pool_size=5,              # Core connection pool size
    max_overflow=10,          # Extra connections under peak load
    pool_pre_ping=True,       # Detect and discard stale connections before each use
)

# ---------------------------------------------------------------------------
# Session factory — produces AsyncSession instances
# ---------------------------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,   # Keep objects usable after commit without re-querying
)


# ---------------------------------------------------------------------------
# FastAPI dependency — yields session, commits or rolls back
# ---------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an AsyncSession per request.

    Automatically commits on success or rolls back on exception.
    Always closes the session after the request (via async context manager).

    Usage:
        async def route(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
