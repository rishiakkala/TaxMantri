"""
tax_tools.py — LangChain tools wrapping the deterministic tax engine and optimizer.

The tax_engine.py is CA-verified with 50+ passing tests — it is NEVER modified.
These tools simply wrap it for LangGraph tool-calling.

Tools:
  calculate_old_regime_tool  — old regime slab tax calculation
  calculate_new_regime_tool  — new regime slab tax calculation (Budget 2025 slabs)
  compare_regimes_tool       — full comparison with recommendation + suggestions
  get_itr1_mapping_tool      — maps profile values to ITR-1 fields
"""
from __future__ import annotations

import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _profile_from_dict(profile_dict: dict):
    """Reconstruct UserFinancialProfile from a dict."""
    from backend.agents.input_agent.schemas import UserFinancialProfile
    return UserFinancialProfile.model_validate(profile_dict)


@tool
def calculate_old_regime_tool(profile_dict: dict) -> dict:
    """
    Calculates income tax under the Old Regime for AY 2025-26.

    Applies deductions: Standard Deduction ₹50K, HRA (Rule 2A), 80C, 80D,
    80CCD(1B), 80TTA/TTB, Section 24(b), Professional Tax.
    Applies 87A rebate if taxable income ≤ ₹5L. Adds 4% cess.

    Args:
        profile_dict: UserFinancialProfile serialized as dict.

    Returns:
        dict: RegimeResult fields (gross_income, total_deductions, taxable_income,
              tax_before_cess, cess, total_tax, deduction_breakdown)
    """
    from backend.agents.evaluator_agent.tax_engine import calculate_old_regime

    try:
        profile = _profile_from_dict(profile_dict)
        result = calculate_old_regime(profile)
        data = result.model_dump()
        logger.info("Old regime calculated total_tax=%.2f", result.total_tax)
        return {"success": True, "result": data, "error": None}
    except Exception as exc:
        logger.error("calculate_old_regime_tool failed: %s", exc)
        return {"success": False, "result": None, "error": str(exc)}


@tool
def calculate_new_regime_tool(profile_dict: dict) -> dict:
    """
    Calculates income tax under the New Regime for AY 2025-26 (Budget 2025, Section 115BAC).

    Applies only: Standard Deduction ₹75K and Employer NPS 80CCD(2).
    Uses revised Budget 2025 slabs: 0-4L/4-8L/8-12L/12-16L/16-20L/20-24L/>24L.
    Applies 87A rebate up to ₹60K if taxable income ≤ ₹12L. Adds 4% cess.

    Args:
        profile_dict: UserFinancialProfile serialized as dict.

    Returns:
        dict: RegimeResult fields (gross_income, total_deductions, taxable_income,
              tax_before_cess, cess, total_tax, deduction_breakdown)
    """
    from backend.agents.evaluator_agent.tax_engine import calculate_new_regime

    try:
        profile = _profile_from_dict(profile_dict)
        result = calculate_new_regime(profile)
        data = result.model_dump()
        logger.info("New regime calculated total_tax=%.2f", result.total_tax)
        return {"success": True, "result": data, "error": None}
    except Exception as exc:
        logger.error("calculate_new_regime_tool failed: %s", exc)
        return {"success": False, "result": None, "error": str(exc)}


@tool
def compare_regimes_tool(profile_dict: dict) -> dict:
    """
    Compares Old vs New Regime tax liability and recommends the better option.

    Ties go to New Regime (simpler, per project spec).
    Also generates rule-based optimization suggestions for each regime.

    Args:
        profile_dict: UserFinancialProfile serialized as dict.

    Returns:
        dict with keys:
          - old_regime (dict): Full RegimeResult for Old Regime
          - new_regime (dict): Full RegimeResult for New Regime
          - recommended_regime (str): "old" | "new"
          - savings_amount (float): Tax saved by choosing recommended regime
          - rationale (str): Basic rationale string (will be enhanced by EvaluatorAgent LLM)
          - old_regime_suggestions (list[str]): Tips to reduce old regime tax
          - new_regime_suggestions (list[str]): Tips to reduce new regime tax
    """
    from backend.agents.evaluator_agent.tax_engine import compare_regimes

    try:
        profile = _profile_from_dict(profile_dict)
        result = compare_regimes(profile)
        data = result.model_dump()
        logger.info(
            "Regime comparison done recommended=%s savings=%.2f",
            result.recommended_regime,
            result.savings_amount,
        )
        return {"success": True, "result": data, "error": None}
    except Exception as exc:
        logger.error("compare_regimes_tool failed: %s", exc)
        return {"success": False, "result": None, "error": str(exc)}


@tool
def get_itr1_mapping_tool(profile_dict: dict, tax_result_dict: dict) -> dict:
    """
    Maps the taxpayer's financial values to ITR-1 Sahaj form fields.

    Provides field name, schedule, amount, and notes for each applicable
    ITR-1 field. Used by the frontend's collapsible ITR-1 table.

    Args:
        profile_dict: UserFinancialProfile serialized as dict.
        tax_result_dict: TaxResult serialized as dict (from compare_regimes_tool).

    Returns:
        dict with keys:
          - success (bool)
          - mapping (list[dict]): Each entry has {itr1_field, schedule, value, regime, note}
          - error (str | None)
    """
    from backend.agents.evaluator_agent.itr1_mapper import build_itr1_mapping
    from backend.agents.evaluator_agent.schemas import TaxResult

    try:
        profile = _profile_from_dict(profile_dict)
        tax_result = TaxResult.model_validate(tax_result_dict)
        entries = build_itr1_mapping(profile, tax_result)
        data = [entry.model_dump() for entry in entries]
        logger.info("ITR-1 mapping generated %d entries", len(data))
        return {"success": True, "mapping": data, "error": None}
    except Exception as exc:
        logger.error("get_itr1_mapping_tool failed: %s", exc)
        return {"success": False, "mapping": [], "error": str(exc)}
