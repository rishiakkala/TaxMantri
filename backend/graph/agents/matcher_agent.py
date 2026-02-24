"""
matcher_agent.py — MatcherAgent LangGraph node.

Responsibility: RAG Retrieval + Act Identification (with citations)

The MatcherAgent:
  1. Receives the structured UserFinancialProfile from InputAgent
  2. Auto-generates relevant IT Act section queries from the profile
  3. Runs hybrid FAISS+BM25 retrieval for each query
  4. Synthesizes a law context summary using Mistral (grounded in retrieved chunks)
  5. Validates all citations against actual KB chunks

Output: retrieved_chunks, citations, law_context — fed to EvaluatorAgent for
LLM-grounded rationale generation that cites real IT Act sections.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.graph.state import TaxMantriState

logger = logging.getLogger(__name__)


async def matcher_agent_node(state: TaxMantriState) -> dict:
    """
    MatcherAgent node — retrieves relevant tax law context for the taxpayer's profile.

    Reads:
      state["profile"]      — UserFinancialProfile (set by InputAgent)
      state["profile_dict"] — dict version of profile

    Writes:
      state["tax_queries"]        — auto-generated queries from profile
      state["retrieved_chunks"]   — FAISS+BM25 retrieved KB chunks
      state["citations"]          — validated IT Act citations
      state["law_context"]        — synthesized legal context string
      state["matcher_confidence"] — "high" | "low"
      state["current_agent"]      — "matcher"
    """
    from backend.graph.tools.rag_tools import (
        generate_tax_queries_tool,
        rag_search_tool,
        llm_answer_tool,
    )
    from backend.agents.matcher_agent.llm_service import build_profile_summary

    profile = state.get("profile")
    profile_dict = state.get("profile_dict", {})

    if profile is None:
        logger.error("MatcherAgent received no profile from InputAgent")
        return {
            "tax_queries": [],
            "retrieved_chunks": [],
            "citations": [],
            "law_context": "",
            "matcher_confidence": "low",
            "current_agent": "matcher",
        }

    logger.info("MatcherAgent starting for profile_id=%s", profile.profile_id)

    # -------------------------------------------------------------------------
    # Step 1: Auto-generate relevant IT Act queries from profile
    # -------------------------------------------------------------------------
    query_result = generate_tax_queries_tool.invoke({"profile": profile_dict})
    queries: list[str] = query_result.get("queries", [])
    sections_identified: list[str] = query_result.get("sections_identified", [])

    logger.info(
        "MatcherAgent generated %d queries for sections: %s",
        len(queries),
        ", ".join(sections_identified[:5]),
    )

    # -------------------------------------------------------------------------
    # Step 2: Retrieve chunks for each query, deduplicate by chunk_id
    # -------------------------------------------------------------------------
    all_chunks: dict[str, dict] = {}

    for query in queries:
        search_result = rag_search_tool.invoke({"query": query, "top_k": 6})
        if search_result.get("success"):
            for chunk in search_result.get("chunks", []):
                chunk_id = chunk.get("chunk_id", "")
                if chunk_id and chunk_id not in all_chunks:
                    all_chunks[chunk_id] = chunk

    retrieved_chunks = list(all_chunks.values())
    logger.info("MatcherAgent retrieved %d unique chunks across %d queries", len(retrieved_chunks), len(queries))

    # -------------------------------------------------------------------------
    # Step 3: Build profile summary for LLM context (PII-stripped)
    # -------------------------------------------------------------------------
    try:
        profile_summary = build_profile_summary(profile)
    except Exception:
        profile_summary = None

    # -------------------------------------------------------------------------
    # Step 4: Generate a synthesized law context using Mistral
    # Only call LLM if we have retrieved chunks to ground the answer
    # -------------------------------------------------------------------------
    all_citations: list[dict] = []
    law_context_parts: list[str] = []
    overall_confidence = "low"

    if retrieved_chunks:
        # Synthesize a consolidated context question
        synthesis_question = (
            f"Based on the taxpayer's profile (basic salary ₹{profile_dict.get('basic_salary', 0):,.0f}, "
            f"city: {profile_dict.get('city_type', 'metro')}, age: {profile_dict.get('age_bracket', 'under60')}), "
            f"which IT Act sections apply and what are their deduction limits for AY 2025-26? "
            f"Relevant sections: {', '.join(sections_identified[:6])}."
        )

        llm_result = llm_answer_tool.invoke({
            "question": synthesis_question,
            "chunks": retrieved_chunks[:10],  # limit context window
            "profile_summary": profile_summary,
        })

        if llm_result.get("answer"):
            law_context_parts.append(llm_result["answer"])
            all_citations.extend(llm_result.get("citations", []))
            overall_confidence = llm_result.get("confidence", "low")

    # Fallback: build minimal context from chunk texts if LLM unavailable
    if not law_context_parts and retrieved_chunks:
        for chunk in retrieved_chunks[:5]:
            section_ref = chunk.get("section_ref", "Unknown")
            law_context_parts.append(f"[{section_ref}]: {chunk['text'][:200]}...")
        overall_confidence = "low"

    law_context = "\n\n".join(law_context_parts)

    # Deduplicate citations by section name
    seen_sections = set()
    unique_citations = []
    for c in all_citations:
        sec = c.get("section", "")
        if sec not in seen_sections:
            seen_sections.add(sec)
            unique_citations.append(c)

    logger.info(
        "MatcherAgent complete chunks=%d citations=%d confidence=%s",
        len(retrieved_chunks),
        len(unique_citations),
        overall_confidence,
    )

    return {
        "tax_queries": queries,
        "retrieved_chunks": retrieved_chunks,
        "citations": unique_citations,
        "law_context": law_context,
        "matcher_confidence": overall_confidence,
        "current_agent": "matcher",
    }
