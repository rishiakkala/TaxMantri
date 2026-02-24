"""
schemas.py — EvaluatorAgent Pydantic v2 data contracts (AY 2025-26).

Defines:
  - DeductionBreakdown  (itemised deductions per regime — combined 80D field)
  - RegimeResult        (full tax computation for one regime)
  - TaxResult           (dual-regime comparison — main EvaluatorAgent output)
  - ITR1FieldMap        (ITR-1 schedule field mapping — Phase 7)

PHASE 2 NOTE:
  - DeductionBreakdown uses section_80d (combined self+parents) — old regime only.
  - TaxResult has separate old_regime_suggestions / new_regime_suggestions lists.
  - RegimeResult.profile_id removed; TaxResult.profile_id is Optional (set after storage).
"""
from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# DeductionBreakdown — itemised deductions applied in one regime
# ---------------------------------------------------------------------------

class DeductionBreakdown(BaseModel):
    """
    Itemised deductions used in a regime calculation.

    All values are the ACTUAL deduction applied (after caps), not the raw input.
    For example, section_80c=150000 means ₹1.5L was applied even if input was ₹2L.

    New regime: only standard_deduction and section_80ccd2 will be non-zero.
    All other fields default to 0 for new regime.
    """
    model_config = ConfigDict(extra="forbid")

    standard_deduction: float = 0         # ₹50K old / ₹75K new
    hra_exemption: float = 0              # Rule 2A min-of-3 — old regime only
    section_80c: float = 0               # Cap ₹1,50,000 — old regime only
    section_80d: float = 0               # 80D self + parents combined — old regime only
    section_80ccd1b: float = 0           # Employee NPS, cap ₹50K — old regime only
    section_80ccd2: float = 0            # Employer NPS, cap 10% basic — BOTH regimes
    section_80tta_ttb: float = 0         # 80TTA/80TTB — old regime only
    section_24b: float = 0               # Home loan interest, cap ₹2L — old regime only
    professional_tax: float = 0          # Section 16 — old regime only


# ---------------------------------------------------------------------------
# RegimeResult — full tax calculation for one regime
# ---------------------------------------------------------------------------

class RegimeResult(BaseModel):
    """
    Complete tax computation result for a single regime (old or new).

    Computation sequence (CRITICAL — order determines correctness):
      1. gross_income = basic + hra + allowances + other_income
      2. total_deductions = sum of applicable capped deductions
      3. taxable_income = max(0, gross_income - total_deductions)
      4. slab_tax = progressive bracket calculation
      5. Apply 87A rebate → tax_before_cess (= 0 if eligible)
      6. cess = 4% of tax_before_cess   ← NOT on pre-87A tax
      7. total_tax = tax_before_cess + cess
    """
    model_config = ConfigDict(extra="forbid")

    gross_income: float
    total_deductions: float
    taxable_income: float
    tax_before_cess: float       # After 87A rebate, before 4% cess
    cess: float                  # 4% of tax_before_cess
    total_tax: float             # tax_before_cess + cess (final payable amount)
    deduction_breakdown: DeductionBreakdown


# ---------------------------------------------------------------------------
# TaxResult — regime comparison output (public API of tax engine)
# ---------------------------------------------------------------------------

class TaxResult(BaseModel):
    """
    Output of compare_regimes() — the central EvaluatorAgent response schema.

    Contains full calculations for both regimes, the recommendation (lower tax),
    savings amount, plain-language rationale, and separate suggestion lists.

    old_regime_suggestions: headroom in 80C, 80D, NPS, 24b (old regime only).
    new_regime_suggestions: employer NPS 80CCD(2) headroom (new regime only).
    """
    model_config = ConfigDict(extra="forbid")

    profile_id: Optional[str] = None     # Set by caller after persisting to DB

    old_regime: RegimeResult
    new_regime: RegimeResult

    recommended_regime: str              # "old" | "new"
    savings_amount: float                # abs(old_tax - new_tax)
    rationale: str                       # 2-3 sentences per CONTEXT.md format

    # Separate lists — never merge these into a single field
    old_regime_suggestions: List[str] = []   # Up to 3, sorted by saving desc
    new_regime_suggestions: List[str] = []   # Up to 3, sorted by saving desc


# ---------------------------------------------------------------------------
# ITR1FieldMap — ITR-1 schedule field mapping (Phase 7)
# ---------------------------------------------------------------------------

class ITR1FieldMap(BaseModel):
    """Maps a computed financial value to a specific ITR-1 form field."""
    model_config = ConfigDict(extra="forbid")

    itr1_field: str      # e.g. "Schedule S – Salary"
    schedule: str        # e.g. "Schedule S", "Part B-TI"
    value: float
    source_field: str    # Source UserFinancialProfile field, e.g. "basic_salary"
    regime: Literal["old", "new"]    # Which regime this entry belongs to
    note: Optional[str] = None       # Rule 2A breakdown for HRA; None for all other fields


__all__ = [
    "DeductionBreakdown",
    "RegimeResult",
    "TaxResult",
    "ITR1FieldMap",
]
