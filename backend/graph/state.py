"""
state.py — Shared TaxMantriState TypedDict for the LangGraph pipeline.

This is the single source of truth that flows through all three agent nodes:
  InputAgent → MatcherAgent → EvaluatorAgent

All agent nodes read from and write to this state. LangGraph merges updates
returned by each node automatically.
"""
from __future__ import annotations

from typing import Annotated, Any, Optional
from typing_extensions import TypedDict
import operator


# ---------------------------------------------------------------------------
# TaxMantriState — the shared graph state
# ---------------------------------------------------------------------------

class TaxMantriState(TypedDict, total=False):
    """
    Shared state passed through all nodes in the TaxMantri LangGraph pipeline.

    Fields are grouped by which agent produces them.
    'total=False' means all fields are optional at graph construction time —
    each node adds/overwrites only the fields it is responsible for.
    """

    # ---- Raw input (set before graph.invoke) --------------------------------
    profile_id: Optional[str]            # Pre-confirmed profile UUID (skips re-validation)
    raw_input: dict                      # Original request payload (manual form data)
    input_method: str                    # "manual" | "ocr"
    file_path: Optional[str]             # Temp file path for OCR uploads (None for manual)
    ocr_session_id: Optional[str]        # Redis session_id for OCR confirm flow

    # ---- InputAgent outputs -------------------------------------------------
    profile: Optional[Any]              # UserFinancialProfile instance (typed in agent)
    profile_dict: Optional[dict]        # Serializable dict version for JSON responses
    input_errors: Annotated[list[str], operator.add]   # Accumulates errors across retries
    input_confidence: float              # 0.0–1.0 overall profile confidence

    # ---- MatcherAgent outputs -----------------------------------------------
    tax_queries: list[str]               # Auto-generated queries from profile
    retrieved_chunks: list[dict]         # FAISS+BM25 retrieved knowledge base chunks
    citations: list[dict]               # Validated citations [{section, excerpt}]
    law_context: str                     # Synthesized legal context for evaluator
    matcher_confidence: str             # "high" | "low"

    # ---- EvaluatorAgent outputs ---------------------------------------------
    tax_result: Optional[dict]          # Serialized TaxResult dict
    recommendation: str                  # "old" | "new"
    savings_amount: float
    rationale: str                       # LLM-grounded rationale citing actual laws
    old_suggestions: list[str]
    new_suggestions: list[str]

    # ---- Control flow -------------------------------------------------------
    current_agent: str                   # "input" | "matcher" | "evaluator" | "done"
    errors: Annotated[list[str], operator.add]          # Global error accumulator
    should_stop: bool                    # True if InputAgent found fatal errors
