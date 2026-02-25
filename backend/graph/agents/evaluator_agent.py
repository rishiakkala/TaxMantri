"""
evaluator_agent.py — EvaluatorAgent LangGraph node.

Responsibility: Tax Calculation + Recommendation (Old vs New Regime)

The EvaluatorAgent:
  1. Receives structured profile from InputAgent and law_context from MatcherAgent
  2. Runs the deterministic CA-verified tax engine for both regimes (no LLM)
  3. Uses Mistral to generate a personalized rationale GROUNDED IN actual law_context
     (citations from MatcherAgent are woven into the recommendation text)
  4. Assembles the final TaxResult

The tax calculation itself is 100% deterministic — Mistral is only used for the
human-facing rationale text, not for any numerical computation.
"""
from __future__ import annotations

import logging

from backend.graph.state import TaxMantriState

logger = logging.getLogger(__name__)

# System prompt for the rationale LLM call
EVALUATOR_SYSTEM = """You are TaxMantri's EvaluatorAgent. Your job is to explain a tax regime recommendation
to an Indian salaried taxpayer in plain language.

Rules:
1. The tax numbers are provided to you — do NOT recalculate or modify them.
2. Cite the specific IT Act sections from the law_context provided.
3. Keep the rationale to 2-4 sentences maximum.
4. Be warm, professional, and clear — explain WHY the recommended regime is better in simple terms.
5. Use ₹ symbol for all amounts. Format large numbers with commas (₹1,50,000 not 150000).
6. Do NOT add financial advice beyond what the IT Act numbers support.
"""


async def evaluator_agent_node(state: TaxMantriState) -> dict:
    """
    EvaluatorAgent node — runs tax calculation and generates grounded recommendation.

    Reads:
      state["profile"]       — UserFinancialProfile (from InputAgent)
      state["profile_dict"]  — dict version of profile
      state["law_context"]   — synthesized legal context (from MatcherAgent)
      state["citations"]     — validated IT Act citations (from MatcherAgent)

    Writes:
      state["tax_result"]         — full TaxResult as serializable dict
      state["recommendation"]     — "old" | "new"
      state["savings_amount"]     — tax saved by choosing recommended regime
      state["rationale"]          — LLM-grounded rationale with actual law citations
      state["old_suggestions"]    — optimization tips for old regime
      state["new_suggestions"]    — optimization tips for new regime
      state["current_agent"]      — "evaluator"
    """
    from backend.graph.tools.tax_tools import compare_regimes_tool
    from backend.graph.graph import get_mistral_client, get_rag_semaphore
    from backend.agents.matcher_agent.llm_service import (
        MISTRAL_MODEL, MISTRAL_TEMPERATURE, MISTRAL_MAX_TOKENS
    )

    profile = state.get("profile")
    profile_dict = state.get("profile_dict", {})
    law_context = state.get("law_context", "")
    citations = state.get("citations", [])

    if profile is None:
        logger.error("EvaluatorAgent received no profile")
        return {
            "tax_result": None,
            "recommendation": "new",
            "savings_amount": 0.0,
            "rationale": "Unable to calculate — profile not available.",
            "old_suggestions": [],
            "new_suggestions": [],
            "current_agent": "evaluator",
        }

    logger.info("EvaluatorAgent starting for profile_id=%s", profile.profile_id)

    # -------------------------------------------------------------------------
    # Step 1: Run deterministic tax engine (wraps CA-verified tax_engine.py)
    # -------------------------------------------------------------------------
    comparison = compare_regimes_tool.invoke({"profile_dict": profile_dict})

    if not comparison.get("success"):
        error_msg = comparison.get("error", "Tax calculation failed")
        logger.error("EvaluatorAgent tax calculation failed: %s", error_msg)
        return {
            "tax_result": None,
            "errors": [error_msg],
            "current_agent": "evaluator",
        }

    tax_result = comparison["result"]  # Full TaxResult dict
    recommended = tax_result["recommended_regime"]
    savings = tax_result["savings_amount"]
    engine_rationale = tax_result.get("rationale", "")
    old_total = tax_result["old_regime"]["total_tax"]
    new_total = tax_result["new_regime"]["total_tax"]
    old_deductions = tax_result["old_regime"]["total_deductions"]

    logger.info(
        "EvaluatorAgent tax done recommended=%s old_tax=%.2f new_tax=%.2f savings=%.2f",
        recommended, old_total, new_total, savings,
    )

    # -------------------------------------------------------------------------
    # Step 2: Generate LLM-grounded rationale using law_context from MatcherAgent
    # Only use LLM if we have law context; otherwise fall back to engine_rationale
    # -------------------------------------------------------------------------
    grounded_rationale = engine_rationale  # default fallback

    if law_context:
        client = get_mistral_client()
        if client is not None:
            # Build a focused prompt for rationale generation
            citation_refs = ", ".join(
                c.get("section", "") for c in citations[:4] if c.get("section")
            ) or "applicable IT Act sections"

            user_prompt = f"""Tax calculation results for AY 2025-26:
- Old Regime tax: ₹{old_total:,.0f} (total deductions: ₹{old_deductions:,.0f})
- New Regime tax: ₹{new_total:,.0f}
- Recommended: {'Old' if recommended == 'old' else 'New'} Regime
- Tax savings: ₹{savings:,.0f}

Law context from knowledge base:
{law_context[:1200]}

Relevant sections: {citation_refs}

Write a 2-4 sentence recommendation rationale explaining why the {recommended} regime is better for this taxpayer, citing the specific sections above."""

            try:
                semaphore = get_rag_semaphore()
                async with semaphore:
                    response = await client.chat.complete_async(
                        model=MISTRAL_MODEL,
                        messages=[
                            {"role": "system", "content": EVALUATOR_SYSTEM},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.2,
                        max_tokens=300,
                    )
                grounded_rationale = response.choices[0].message.content or engine_rationale
                logger.info("EvaluatorAgent LLM rationale generated len=%d", len(grounded_rationale))
            except Exception as exc:
                logger.warning("EvaluatorAgent LLM rationale failed, using engine default: %s", exc)
                grounded_rationale = engine_rationale

    # -------------------------------------------------------------------------
    # Step 3: Inject grounded rationale and citations into tax_result
    # -------------------------------------------------------------------------
    tax_result["rationale"] = grounded_rationale
    tax_result["citations"] = citations  # Attach MatcherAgent citations to result

    return {
        "tax_result": tax_result,
        "recommendation": recommended,
        "savings_amount": savings,
        "rationale": grounded_rationale,
        "old_suggestions": tax_result.get("old_regime_suggestions", []),
        "new_suggestions": tax_result.get("new_regime_suggestions", []),
        "current_agent": "evaluator",
    }
