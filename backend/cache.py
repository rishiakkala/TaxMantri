"""
cache.py — Redis caching layer for TaxMantri.

Namespace conventions (locked by CONTEXT.md):
  session:{session_id}       → wizard progress dict       TTL 24h (86400s)
  faq:{sha256(question)}     → RAG answer for question    TTL 1h  (3600s)

Design:
  - Uses redis.asyncio (async client, part of redis-py 5.x — do NOT use aioredis separately)
  - Pool created once in lifespan, stored on app.state.redis
  - Helper functions take the client as a param — no module-level global state
  - FAQ key uses SHA-256 of lowercased, stripped question for deterministic cache hits
  - Logs only session_id (not data values) — no PII in logs
"""
import hashlib
import json
import logging
from typing import Optional

import redis.asyncio as aioredis

from backend.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TTL constants (seconds)
# ---------------------------------------------------------------------------
SESSION_TTL: int = 86400   # 24 hours
FAQ_TTL: int = 3600        # 1 hour

# ---------------------------------------------------------------------------
# Key prefix constants
# ---------------------------------------------------------------------------
SESSION_PREFIX = "session"
FAQ_PREFIX = "faq"


# ---------------------------------------------------------------------------
# Key builders
# ---------------------------------------------------------------------------

def make_session_key(session_id: str) -> str:
    """Build Redis key for session wizard progress: session:{session_id}"""
    return f"{SESSION_PREFIX}:{session_id}"


def make_faq_key(question: str) -> str:
    """
    Build Redis key for FAQ cache entry.
    Normalizes question (lowercase + strip) before hashing to maximize hit rate.
    Key format: faq:{sha256hex}
    """
    normalized = question.strip().lower()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"{FAQ_PREFIX}:{digest}"


# ---------------------------------------------------------------------------
# Pool factory — called once in lifespan
# ---------------------------------------------------------------------------

async def create_redis_pool() -> aioredis.Redis:
    """
    Create and return an async Redis connection pool.
    Called once in FastAPI lifespan startup — stored on app.state.redis.
    Verifies connectivity with PING before returning.
    """
    client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=20,
    )
    await client.ping()
    logger.info("Redis connection pool established at %s", settings.redis_url)
    return client


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

async def get_session_data(
    client: aioredis.Redis, session_id: str
) -> Optional[dict]:
    """
    Retrieve wizard progress dict from Redis.
    Returns None if session expired or never existed.
    """
    key = make_session_key(session_id)
    raw = await client.get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def set_session_data(
    client: aioredis.Redis, session_id: str, data: dict
) -> None:
    """
    Store wizard progress in Redis with TTL 24h.
    Overwrites existing value and resets TTL on every write.
    Note: caller should also persist to PostgreSQL via store.set_session() for durability.
    """
    key = make_session_key(session_id)
    await client.setex(key, SESSION_TTL, json.dumps(data))
    logger.info("Session data updated session_id=%s ttl=%ds", session_id, SESSION_TTL)


# ---------------------------------------------------------------------------
# FAQ cache helpers
# ---------------------------------------------------------------------------

async def get_faq_cache(
    client: aioredis.Redis, question: str
) -> Optional[dict]:
    """
    Check FAQ cache for a prior answer to this question.
    Returns the cached RAGResponse dict or None on cache miss.
    """
    key = make_faq_key(question)
    raw = await client.get(key)
    if raw is None:
        return None
    logger.info("FAQ cache hit key=%s", key)
    return json.loads(raw)


async def set_faq_cache(
    client: aioredis.Redis, question: str, response: dict
) -> None:
    """
    Store a RAG response dict in the FAQ cache with TTL 1h.
    Response is serialized to JSON for storage.
    """
    key = make_faq_key(question)
    await client.setex(key, FAQ_TTL, json.dumps(response))
    logger.info("FAQ response cached key=%s ttl=%ds", key, FAQ_TTL)
