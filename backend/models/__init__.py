"""
models/__init__.py — imports all ORM models so Alembic's env.py
sees them via Base.metadata when generating migrations.

Import order matters for potential FK dependencies (none yet, but future-proofing).
"""
from backend.models.profile import ProfileORM
from backend.models.session import SessionORM
from backend.models.tax_result import TaxResultORM
from backend.models.chat_history import ChatHistoryORM
from backend.models.session_event import SessionEventORM

__all__ = ["ProfileORM", "TaxResultORM", "SessionORM", "ChatHistoryORM", "SessionEventORM"]
