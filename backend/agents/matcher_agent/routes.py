"""
routes.py — MatcherAgent HTTP endpoints.

POST /api/query  — FAQ cache check → hybrid retrieval → Mistral generation → persist → return
GET  /api/chat/history — Return session Q&A history from PostgreSQL

No JWT authentication in v1 (hackathon decision — deferred to v2/AUTH-01).
app.state resources (retriever, mistral, rag_semaphore) are set in main.py lifespan.
"""
import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.matcher_agent.llm_service import build_profile_summary, generate_answer
from backend.agents.matcher_agent.retriever import TaxRetriever
from backend.agents.matcher_agent.schemas import QueryRequest, RAGResponse
from backend.cache import get_faq_cache, set_faq_cache
from backend.database import get_db
from backend.store import get_chat_history, get_profile, save_chat_message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Matcher Agent"])


@router.post("/query")
async def query_endpoint(
    body: QueryRequest,
    request: Request,
    debug: bool = Query(default=False, description="Include top-3 retrieved chunks in response"),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a plain-English tax question and receive a Mistral-generated answer
    grounded in the Phase 4 knowledge base with [Section X, IT Act 1961] citations.

    Flow:
      1. Check Redis FAQ cache (TTL 1h) — return immediately on hit
      2. Retrieve top-10 chunks via TaxRetriever.hybrid_search() (FAISS + BM25 + RRF)
      3. Build optional PII-stripped profile_summary if profile_id provided
      4. Call Mistral API via generate_answer() with asyncio.Semaphore(2) rate limiting
      5. Store result in Redis FAQ cache
      6. Store Q&A in PostgreSQL chat_history (every response, including cache hits)
      7. Return RAGResponse (or JSONResponse with retrieved_chunks if debug=True)

    Returns 503 if Phase 4 indexes have not been built (TaxRetriever not loaded).

    Note: No response_model declared on this route because the debug=True path returns a
    JSONResponse (a different response type) to attach retrieved_chunks without requiring
    RAGResponse to allow extra fields. The non-debug path returns RAGResponse(**...) directly.
    """
    redis = request.app.state.redis

    # ── 1. FAQ cache check ──────────────────────────────────────────────────
    cached_data = await get_faq_cache(redis, body.question)
    if cached_data is not None:
        logger.info("FAQ cache hit for session_id=%s", body.session_id)
        cached_data["cached"] = True
        # Store in chat_history even on cache hit — history is complete (CONTEXT.md)
        await save_chat_message(
            db,
            body.session_id,
            body.question,
            cached_data.get("answer", ""),
            cached_data.get("confidence", "low"),
        )
        return RAGResponse(**cached_data)

    # ── 2. Retrieval ────────────────────────────────────────────────────────
    retriever: Optional[TaxRetriever] = request.app.state.retriever
    if retriever is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "RAG knowledge base is not available. "
                "Run: python backend/agents/matcher_agent/build_index.py to build indexes."
            ),
        )
    chunks = retriever.hybrid_search(body.question, top_k=10)
    logger.info("Retrieval complete session_id=%s chunks=%d", body.session_id, len(chunks))

    # ── 3. Profile summary (PII-stripped numeric summary only) ────────────
    profile_summary: Optional[str] = None
    if body.profile_id:
        profile = await get_profile(db, body.profile_id)
        if profile is not None:
            profile_summary = build_profile_summary(profile)

    # ── 4. LLM generation + citation validation ─────────────────────────
    mistral = request.app.state.mistral
    semaphore: asyncio.Semaphore = request.app.state.rag_semaphore
    result = await generate_answer(mistral, body.question, chunks, profile_summary, semaphore)
    result["cached"] = False

    # ── 5. Persist to chat_history (cache miss path) ─────────────────────
    await save_chat_message(
        db,
        body.session_id,
        body.question,
        result["answer"],
        result["confidence"],
    )

    # ── 6. Cache the result (exclude retrieved_chunks — not relevant to cache) ──
    cacheable = {k: v for k, v in result.items() if k != "retrieved_chunks"}
    await set_faq_cache(redis, body.question, cacheable)

    # ── 7. Return — two explicit paths based on debug flag ───────────────
    #
    # debug=True: return JSONResponse with retrieved_chunks attached.
    #   RAGResponse does NOT have a retrieved_chunks field (it is not part of the
    #   schema contract). We use JSONResponse to bypass Pydantic serialization
    #   and include the debug payload without modifying RAGResponse.
    #
    # debug=False: return RAGResponse constructed from result, explicitly excluding
    #   retrieved_chunks so that RAGResponse(**...) does not receive unknown fields.
    #
    if debug:
        retrieved_chunks = [
            {
                "section_ref": c.get("section_ref", ""),
                "text_excerpt": c.get("text", "")[:200],
            }
            for c in chunks[:3]
        ]
        rag_fields = {k: v for k, v in result.items() if k != "retrieved_chunks"}
        response_body = RAGResponse(**rag_fields).model_dump()
        response_body["retrieved_chunks"] = retrieved_chunks
        return JSONResponse(content=response_body)

    # debug=False: strip retrieved_chunks (if present) before constructing RAGResponse
    rag_fields = {k: v for k, v in result.items() if k != "retrieved_chunks"}
    return RAGResponse(**rag_fields)


@router.get("/chat/history")
async def chat_history_endpoint(
    session_id: str = Query(..., description="Session ID to retrieve Q&A history for"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Return all Q&A exchanges for a session in chronological order.

    Returns an empty messages list if the session has no prior queries.
    Each message includes: question, answer, confidence, created_at (ISO 8601).
    """
    messages = await get_chat_history(db, session_id)
    logger.info("Chat history request session_id=%s messages=%d", session_id, len(messages))
    return {"session_id": session_id, "messages": messages}
