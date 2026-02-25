"""
rag_tools.py — LangChain tools wrapping the MatcherAgent RAG + LLM pipeline.

Tools:
  rag_search_tool          — hybrid FAISS+BM25 retrieval from knowledge base
  generate_tax_queries_tool — auto-generates relevant queries from a financial profile
  llm_answer_tool          — Mistral answer generation with citation validation
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def rag_search_tool(query: str, top_k: int = 8) -> dict:
    """
    Searches the TaxMantri knowledge base using hybrid FAISS + BM25 retrieval.

    Uses Reciprocal Rank Fusion to combine dense (semantic) and sparse (keyword)
    results. Knowledge base contains 19 Income Tax Act sections for AY 2025-26.

    Args:
        query: A natural language tax law question or section reference.
        top_k: Number of chunks to retrieve (default 8).

    Returns:
        dict with keys:
          - success (bool)
          - chunks (list[dict]): Retrieved chunks with {chunk_id, text, section_ref, source}
          - count (int): Number of chunks retrieved
          - error (str | None)
    """
    # Import here to avoid circular imports at module level.
    # The retriever is loaded at FastAPI startup; we import it lazily from app.state
    # via a module-level singleton set by graph.py after startup.
    from backend.graph.graph import get_retriever

    retriever = get_retriever()
    if retriever is None:
        return {
            "success": False,
            "chunks": [],
            "count": 0,
            "error": "RAG index not loaded. Run: python -m backend.agents.matcher_agent.build_index",
        }

    try:
        chunks = retriever.hybrid_search(query, top_k=top_k)
        logger.info("RAG search query=%r returned %d chunks", query[:60], len(chunks))
        return {
            "success": True,
            "chunks": chunks,
            "count": len(chunks),
            "error": None,
        }
    except Exception as exc:
        logger.error("RAG search failed: %s", exc)
        return {
            "success": False,
            "chunks": [],
            "count": 0,
            "error": str(exc),
        }


@tool
def generate_tax_queries_tool(profile: dict) -> dict:
    """
    Auto-generates relevant Income Tax Act queries from a taxpayer's financial profile.

    Analyzes which sections of the IT Act are relevant based on the profile's
    income components and deductions, then creates specific retrieval queries.
    This makes the MatcherAgent context-aware without needing a user question.

    Args:
        profile: UserFinancialProfile as a dict (serialized from InputAgent output).

    Returns:
        dict with keys:
          - queries (list[str]): List of targeted tax law queries
          - sections_identified (list[str]): IT Act sections identified as relevant
    """
    queries: list[str] = []
    sections: list[str] = []

    # Always relevant
    queries.append("income tax slabs AY 2025-26 old regime new regime comparison section 115BAC")
    sections.append("Section 115BAC")

    queries.append("standard deduction salaried employee section 16 AY 2025-26")
    sections.append("Section 16")

    queries.append("section 87A tax rebate AY 2025-26 new regime 12 lakh")
    sections.append("Section 87A")

    # HRA — Section 10(13A) + Rule 2A
    hra = profile.get("hra_received") or 0
    rent = profile.get("monthly_rent_paid") or 0
    if hra > 0 and rent > 0:
        city = profile.get("city_type", "metro")
        queries.append(
            f"HRA exemption section 10(13A) Rule 2A {city} city minimum of three components"
        )
        sections.append("Section 10(13A)")

    # 80C
    investments_80c = profile.get("investments_80c") or 0
    if investments_80c > 0:
        queries.append("section 80C deduction limit 1.5 lakh ELSS PPF LIC EPF")
        sections.append("Section 80C")

    # 80D health insurance
    health_self = profile.get("health_insurance_self") or 0
    health_parents = profile.get("health_insurance_parents") or 0
    parent_senior = profile.get("parent_senior_citizen", False)
    if health_self > 0 or health_parents > 0:
        queries.append(
            f"section 80D health insurance deduction {'senior citizen parents' if parent_senior else 'non-senior parents'}"
        )
        sections.append("Section 80D")

    # NPS 80CCD(1B) — old regime only
    emp_nps = profile.get("employee_nps_80ccd1b") or 0
    if emp_nps > 0:
        queries.append("section 80CCD(1B) NPS employee contribution 50000 additional deduction")
        sections.append("Section 80CCD(1B)")

    # NPS 80CCD(2) — employer, both regimes
    employer_nps = profile.get("employer_nps_80ccd2") or 0
    if employer_nps > 0:
        queries.append("section 80CCD(2) employer NPS contribution 10 percent basic salary both regimes")
        sections.append("Section 80CCD(2)")

    # Home loan interest — Section 24(b)
    home_loan = profile.get("home_loan_interest") or 0
    if home_loan > 0:
        queries.append("section 24(b) home loan interest deduction 2 lakh self-occupied property old regime")
        sections.append("Section 24(b)")

    # Savings interest — 80TTA / 80TTB
    savings = profile.get("savings_interest_80tta") or 0
    age = profile.get("age_bracket", "under60")
    if savings > 0:
        if age in ("60_79", "80plus"):
            queries.append("section 80TTB senior citizen savings account FD interest 50000")
            sections.append("Section 80TTB")
        else:
            queries.append("section 80TTA savings account interest 10000 deduction")
            sections.append("Section 80TTA")

    # LTA — Section 10(5)
    lta = profile.get("lta") or 0
    if lta > 0:
        queries.append("LTA leave travel allowance section 10(5) exemption")
        sections.append("Section 10(5)")

    logger.info(
        "Generated %d queries for %d sections from profile", len(queries), len(sections)
    )
    return {"queries": queries, "sections_identified": sections}


@tool
def llm_answer_tool(
    question: str,
    chunks: list[dict],
    profile_summary: Optional[str] = None,
    mistral_config: Optional[dict] = None,
) -> dict:
    """
    Generates a grounded tax law answer using Mistral, with citation validation.

    Sends retrieved knowledge base chunks as context. Citations are validated
    against chunk text to ensure they are not hallucinated.

    Args:
        question: The tax law question to answer.
        chunks: Retrieved KB chunks from rag_search_tool.
        profile_summary: Optional PII-stripped numeric profile summary for context.
        mistral_config: Optional dict with {api_key} if not using app.state.

    Returns:
        dict with keys:
          - answer (str): Mistral's grounded answer
          - citations (list[dict]): Validated {section, excerpt} citations
          - confidence (str): "high" | "low"
          - error (str | None)
    """
    import asyncio
    from backend.agents.matcher_agent.llm_service import (
        build_user_prompt,
        validate_citations,
        SYSTEM_PROMPT,
        MISTRAL_MODEL,
        MISTRAL_TEMPERATURE,
        MISTRAL_MAX_TOKENS,
    )
    from backend.graph.graph import get_mistral_client, get_rag_semaphore

    client = get_mistral_client()
    if client is None:
        return {
            "answer": "Mistral client not available.",
            "citations": [],
            "confidence": "low",
            "error": "Mistral client not initialized",
        }

    prompt = build_user_prompt(question, chunks, profile_summary)

    async def _call():
        semaphore = get_rag_semaphore()
        async with semaphore:
            response = await client.chat.complete_async(
                model=MISTRAL_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=MISTRAL_TEMPERATURE,
                max_tokens=MISTRAL_MAX_TOKENS,
            )
        return response.choices[0].message.content or ""

    try:
        # Run async inside tool (tools are sync; we run the coroutine here)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, _call())
                    answer_text = future.result(timeout=30)
            else:
                answer_text = loop.run_until_complete(_call())
        except RuntimeError:
            answer_text = asyncio.run(_call())

        citations, confidence = validate_citations(answer_text, chunks)
        logger.info(
            "LLM answer generated citations=%d confidence=%s", len(citations), confidence
        )
        return {
            "answer": answer_text,
            "citations": citations,
            "confidence": confidence,
            "error": None,
        }
    except Exception as exc:
        logger.error("llm_answer_tool failed: %s", exc)
        return {
            "answer": "",
            "citations": [],
            "confidence": "low",
            "error": str(exc),
        }
