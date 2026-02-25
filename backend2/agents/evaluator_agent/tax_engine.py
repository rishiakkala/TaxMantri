"""
TaxMantri Tax Engine — AY 2025-26 (Budget 2025)
Pure Python, zero LLM, deterministic. Same input → same output.

IMPORTANT: This file uses AY 2025-26 rules.
CLAUDE.md contains AY 2024-25 values — do NOT use those slab breakpoints.
New regime slabs were COMPLETELY REVISED in Budget 2025 (Finance Act 2025):
  Old: 3L/6L/9L/12L/15L breakpoints
  New: 4L/8L/12L/16L/20L/24L breakpoints  ← use these
"""
from __future__ import annotations

from backend.agents.input_agent.schemas import UserFinancialProfile
from backend.agents.evaluator_agent.schemas import (
    TaxResult, RegimeResult, DeductionBreakdown,
)

# ===========================================================================
# ASSESSMENT YEAR CONSTANT (verified by TEST-02)
# ===========================================================================

ASSESSMENT_YEAR = "AY2025-26"

# ===========================================================================
# OLD REGIME SLAB BREAKPOINTS (unchanged from AY 2024-25)
# ===========================================================================

OLD_SLAB_2_5L = 250_000
OLD_SLAB_5L   = 500_000
OLD_SLAB_10L  = 1_000_000

# ===========================================================================
# NEW REGIME SLAB BREAKPOINTS — Budget 2025 (COMPLETELY REVISED)
# AY 2024-25 breakpoints were 3L/6L/9L/12L/15L — do NOT use those.
# ===========================================================================

NEW_SLAB_4L  = 400_000
NEW_SLAB_8L  = 800_000
NEW_SLAB_12L = 1_200_000
NEW_SLAB_16L = 1_600_000
NEW_SLAB_20L = 2_000_000
NEW_SLAB_24L = 2_400_000

# ===========================================================================
# DEDUCTION CAP CONSTANTS
# ===========================================================================

OLD_STD_DEDUCTION        = 50_000
NEW_STD_DEDUCTION        = 75_000

CAP_80C                  = 150_000

CAP_80D_SELF_UNDER60     = 25_000    # age_bracket == "under60"
CAP_80D_SELF_SENIOR      = 50_000    # age_bracket in ("60_79", "80plus")
CAP_80D_PARENTS_NON_SENIOR = 25_000  # parent_senior_citizen == False
CAP_80D_PARENTS_SENIOR   = 50_000    # parent_senior_citizen == True

CAP_80CCD1B              = 50_000    # Employee NPS — old regime only
# NOTE: Budget 2024 raised private-sector 80CCD(2) cap to 14%.
# Using 10% per project specification (CONTEXT.md). Update for production.
CAP_80CCD2_PCT           = 0.10      # Employer NPS cap — both regimes

CAP_80TTA                = 10_000    # Savings interest — under60, old regime only
CAP_80TTB                = 50_000    # All interest — senior citizen, old regime only
CAP_24B                  = 200_000   # Home loan interest — old regime only

CESS_RATE                = 0.04

# ===========================================================================
# 87A REBATE PARAMETERS — AY 2025-26
# ===========================================================================

OLD_87A_MAX_REBATE       = 12_500
OLD_87A_TAXABLE_CEILING  = 500_000

NEW_87A_MAX_REBATE       = 60_000
NEW_87A_TAXABLE_CEILING  = 1_200_000   # Effective ₹12L taxable income ceiling

# ---------------------------------------------------------------------------
# 87A Rebate Mechanics — AY 2025-26
# ---------------------------------------------------------------------------
# OLD REGIME:
#   - If taxable_income <= 5,00,000: rebate = min(slab_tax, 12,500)
#   - Net tax = slab_tax - rebate (always 0 for taxable <= 5L)
#   - Above 5L: NO rebate at all
#
# NEW REGIME (Budget 2025):
#   - If taxable_income <= 12,00,000: rebate = min(slab_tax, 60,000)
#   - Net tax = 0 for taxable <= 12L (slab_tax at 12L exactly = 60,000 = max rebate)
#   - At taxable 12,00,001: slab_tax = 60,000.15, rebate applies BUT income > ceiling
#     CORRECTION: 87A only applies when taxable_income <= NEW_87A_TAXABLE_CEILING.
#     Above ₹12L: NO rebate. Full slab_tax applies.
#   - For gross salary (salaried): ₹75K std deduction → gross ₹12.75L → taxable ₹12L → tax ₹0
# ---------------------------------------------------------------------------

# ===========================================================================
# SLAB TABLES — list[tuple[ceiling, rate]]
# ===========================================================================

OLD_REGIME_SLABS: list[tuple[float, float]] = [
    (250_000,      0.00),   # 0–2.5L: 0%
    (500_000,      0.05),   # 2.5–5L: 5%
    (1_000_000,    0.20),   # 5–10L: 20%
    (float("inf"), 0.30),   # >10L: 30%
]

NEW_REGIME_SLABS: list[tuple[float, float]] = [
    (400_000,      0.00),   # 0–4L: 0%
    (800_000,      0.05),   # 4–8L: 5%
    (1_200_000,    0.10),   # 8–12L: 10%
    (1_600_000,    0.15),   # 12–16L: 15%
    (2_000_000,    0.20),   # 16–20L: 20%
    (2_400_000,    0.25),   # 20–24L: 25%
    (float("inf"), 0.30),   # >24L: 30%
]


# ===========================================================================
# INTERNAL HELPERS (pure functions — no side effects, no I/O)
# ===========================================================================

def _calculate_slab_tax(taxable_income: float, slabs: list[tuple[float, float]]) -> float:
    """
    Apply progressive slab tax to taxable_income using a bracket-list pattern.
    Accumulates tax on each bracket, stops when taxable_income <= previous ceiling.
    """
    tax = 0.0
    prev_ceiling = 0.0
    for ceiling, rate in slabs:
        if taxable_income <= prev_ceiling:
            break
        slab_income = min(taxable_income, ceiling) - prev_ceiling
        tax += slab_income * rate
        prev_ceiling = ceiling
    return tax


def calculate_hra_exemption(profile: UserFinancialProfile) -> float:
    """
    HRA exemption under Section 10(13A), Rule 2A.
    Returns the minimum of three components. Returns 0 if no HRA received or no rent paid.

    Component 1: HRA received from employer
    Component 2: 50% of basic_salary (metro) or 40% (non-metro)
    Component 3: max(0, annual_rent - 10% of basic_salary)  ← MUST clip at 0
    """
    hra = profile.hra_received or 0.0
    rent = profile.monthly_rent_paid or 0.0
    if hra == 0 or rent == 0:
        return 0.0
    metro_pct = 0.50 if profile.city_type == "metro" else 0.40
    annual_rent = rent * 12
    component_1 = hra
    component_2 = metro_pct * profile.basic_salary
    component_3 = max(0.0, annual_rent - 0.10 * profile.basic_salary)
    return min(component_1, component_2, component_3)


def _calculate_80d(profile: UserFinancialProfile) -> float:
    """
    80D deduction: independent caps for self and parents — NO combined cap.
    Self cap: age-bracket-dependent.
    Parent cap: parent_senior_citizen flag.
    """
    self_cap   = CAP_80D_SELF_SENIOR if profile.age_bracket in ("60_79", "80plus") else CAP_80D_SELF_UNDER60
    parent_cap = CAP_80D_PARENTS_SENIOR if profile.parent_senior_citizen else CAP_80D_PARENTS_NON_SENIOR
    self_ded   = min(profile.health_insurance_self or 0.0, self_cap)
    parent_ded = min(profile.health_insurance_parents or 0.0, parent_cap)
    return self_ded + parent_ded   # No combined ceiling — each is independent


def _calculate_80tta_ttb_old(profile: UserFinancialProfile) -> float:
    """
    Old regime only. Under60 → 80TTA (savings interest, cap ₹10K).
    Senior (60_79 or 80plus) → 80TTB (all interest income, cap ₹50K).
    New regime: do NOT call this function — neither 80TTA nor 80TTB applies.
    """
    amount = profile.savings_interest_80tta or 0.0
    if profile.age_bracket == "under60":
        return min(amount, CAP_80TTA)
    else:
        return min(amount, CAP_80TTB)


def _apply_87a_old(taxable_income: float, tax: float) -> float:
    """
    Old regime 87A rebate.
    If taxable_income <= ₹5,00,000: rebate = min(tax, ₹12,500) → net = tax - rebate.
    If taxable_income > ₹5,00,000: no rebate, full tax applies.
    """
    if taxable_income <= OLD_87A_TAXABLE_CEILING:
        return max(0.0, tax - min(tax, OLD_87A_MAX_REBATE))
    return tax


def _apply_87a_new(taxable_income: float, tax: float) -> float:
    """
    New regime 87A rebate (AY 2025-26, Budget 2025).
    If taxable_income <= ₹12,00,000: rebate = min(tax, ₹60,000) → net = tax - rebate.
    If taxable_income > ₹12,00,000: NO rebate at all. Full tax applies.

    At exactly ₹12L: slab_tax = ₹60,000 = max rebate → net = ₹0.
    At ₹13L: income > ceiling → no rebate → full ₹75,000 slab tax.
    """
    if taxable_income <= NEW_87A_TAXABLE_CEILING:
        return max(0.0, tax - min(tax, NEW_87A_MAX_REBATE))
    return tax


# ===========================================================================
# OLD REGIME CALCULATOR
# ===========================================================================

def calculate_old_regime(profile: UserFinancialProfile) -> RegimeResult:
    """
    Old regime tax calculation for AY 2025-26.

    Deductions allowed: std deduction ₹50K, HRA Rule 2A, 80C, 80D, 80CCD(1B),
    80TTA/TTB, Section 24(b), professional tax.
    NOT allowed: employer NPS 80CCD(2).
    87A: rebate up to ₹12,500 if taxable <= ₹5L.
    Cess: 4% on post-87A tax.
    """
    # Step 1: Gross income (HRA is included — exemption is deducted separately)
    gross_income = (
        profile.basic_salary
        + (profile.hra_received or 0.0)
        + (profile.lta or 0.0)
        + (profile.special_allowance or 0.0)
        + (profile.other_allowances or 0.0)
        + (profile.other_income or 0.0)
    )

    # Step 2: Deduction breakdown
    ded_std      = float(OLD_STD_DEDUCTION)
    ded_hra      = calculate_hra_exemption(profile)
    ded_80c      = min(profile.investments_80c or 0.0, CAP_80C)
    ded_80d      = _calculate_80d(profile)
    ded_80ccd1b  = min(profile.employee_nps_80ccd1b or 0.0, CAP_80CCD1B)
    ded_80ccd2   = 0.0   # employer NPS NOT deductible in old regime
    ded_80tta    = _calculate_80tta_ttb_old(profile)
    ded_24b      = min(profile.home_loan_interest or 0.0, CAP_24B)
    ded_pt       = profile.professional_tax or 0.0   # exact amount, no cap (statutory max validated by schema)

    total_deductions = (
        ded_std + ded_hra + ded_80c + ded_80d + ded_80ccd1b
        + ded_80ccd2 + ded_80tta + ded_24b + ded_pt
    )

    # Step 3: Taxable income (never negative)
    taxable_income = max(0.0, gross_income - total_deductions)

    # Step 4: Slab tax
    slab_tax = _calculate_slab_tax(taxable_income, OLD_REGIME_SLABS)

    # Step 5: 87A rebate
    tax_after_87a = _apply_87a_old(taxable_income, slab_tax)

    # Step 6: Cess (on post-87A tax — NOT on pre-87A tax)
    cess = round(tax_after_87a * CESS_RATE, 2)

    # Step 7: Final tax
    total_tax = round(tax_after_87a + cess, 2)

    return RegimeResult(
        gross_income=gross_income,
        total_deductions=total_deductions,
        taxable_income=taxable_income,
        tax_before_cess=round(tax_after_87a, 2),   # AFTER 87A, BEFORE cess
        cess=cess,
        total_tax=total_tax,
        deduction_breakdown=DeductionBreakdown(
            standard_deduction=ded_std,
            hra_exemption=ded_hra,
            section_80c=ded_80c,
            section_80d=ded_80d,
            section_80ccd1b=ded_80ccd1b,
            section_80ccd2=ded_80ccd2,
            section_80tta_ttb=ded_80tta,
            section_24b=ded_24b,
            professional_tax=ded_pt,
        ),
    )


# ===========================================================================
# NEW REGIME CALCULATOR
# ===========================================================================

def calculate_new_regime(profile: UserFinancialProfile) -> RegimeResult:
    """
    New regime tax calculation for AY 2025-26 (Budget 2025, Section 115BAC).

    Deductions allowed: std deduction ₹75K and employer NPS 80CCD(2) only.
    NOT allowed: HRA, 80C, 80D, 80CCD(1B), 80TTA/TTB, 24(b), professional tax.
    87A: rebate up to ₹60,000 if taxable <= ₹12L.
    Cess: 4% on post-87A tax.

    Budget 2025 slabs: 0-4L/4-8L/8-12L/12-16L/16-20L/20-24L/>24L
    Note: employer NPS cap = 10% of basic_salary (project spec; Budget 2024 raised to 14%).
    """
    # Step 1: Gross income (same definition as old regime)
    gross_income = (
        profile.basic_salary
        + (profile.hra_received or 0.0)
        + (profile.lta or 0.0)
        + (profile.special_allowance or 0.0)
        + (profile.other_allowances or 0.0)
        + (profile.other_income or 0.0)
    )

    # Step 2: New regime deductions (only two items allowed)
    ded_std = float(NEW_STD_DEDUCTION)
    # Employer NPS: capped at 10% of basic (project spec; Budget 2024 raised to 14%)
    employer_nps_cap = CAP_80CCD2_PCT * profile.basic_salary
    ded_80ccd2 = min(profile.employer_nps_80ccd2 or 0.0, employer_nps_cap)

    total_deductions = ded_std + ded_80ccd2

    # Step 3: Taxable income
    taxable_income = max(0.0, gross_income - total_deductions)

    # Step 4: Slab tax (Budget 2025 7-slab structure)
    slab_tax = _calculate_slab_tax(taxable_income, NEW_REGIME_SLABS)

    # Step 5: 87A rebate — ONLY if taxable_income <= ₹12L
    tax_after_87a = _apply_87a_new(taxable_income, slab_tax)

    # Step 6: Cess (on post-87A tax)
    cess = round(tax_after_87a * CESS_RATE, 2)

    # Step 7: Final tax
    total_tax = round(tax_after_87a + cess, 2)

    return RegimeResult(
        gross_income=gross_income,
        total_deductions=total_deductions,
        taxable_income=taxable_income,
        tax_before_cess=round(tax_after_87a, 2),
        cess=cess,
        total_tax=total_tax,
        deduction_breakdown=DeductionBreakdown(
            standard_deduction=ded_std,
            section_80ccd2=ded_80ccd2,
            # All other fields default to 0 — not available in new regime
        ),
    )


# ===========================================================================
# COMPARE REGIMES — public API
# ===========================================================================

def compare_regimes(profile: UserFinancialProfile) -> TaxResult:
    """
    Compare old and new regime tax for the given profile.
    Recommends lower-tax regime; ties go to New Regime (simpler, per CONTEXT.md).
    Generates rationale (2-3 sentences) and optimization suggestions.

    Uses a local import of optimizer to avoid circular import at module level
    (optimizer.py imports constants from this module).
    """
    # Local import — breaks circular: tax_engine → optimizer → tax_engine(constants)
    from backend.agents.evaluator_agent.optimizer import (
        generate_old_suggestions,
        generate_new_suggestions,
    )

    # Step 1: Calculate both regimes
    old = calculate_old_regime(profile)
    new = calculate_new_regime(profile)

    # Step 2: Determine winner
    if old.total_tax < new.total_tax:
        recommended = "old"
        savings = new.total_tax - old.total_tax
    elif new.total_tax < old.total_tax:
        recommended = "new"
        savings = old.total_tax - new.total_tax
    else:
        # Tie → New Regime per CONTEXT.md
        recommended = "new"
        savings = 0.0

    # Step 3: Build rationale string (2-3 sentences per CONTEXT.md spec)
    if savings == 0.0:
        # Tie case
        rationale = (
            f"Both regimes result in the same tax (₹{old.total_tax:,.0f}). "
            "New Regime recommended as the simpler option with no mandatory investment requirements."
        )
    elif recommended == "old":
        # Old wins — list top deductions that drove the win
        bd = old.deduction_breakdown
        key_deds: list[str] = []
        if bd.hra_exemption > 0:
            key_deds.append(f"HRA exemption ₹{bd.hra_exemption:,.0f}")
        if bd.section_80c > 0:
            key_deds.append(f"80C ₹{bd.section_80c:,.0f}")
        if bd.section_80d > 0:
            key_deds.append(f"80D ₹{bd.section_80d:,.0f}")
        if bd.section_24b > 0:
            key_deds.append(f"Section 24(b) ₹{bd.section_24b:,.0f}")
        top_deds = ", ".join(key_deds[:3]) if key_deds else "available deductions"
        rationale = (
            f"Old Regime saves ₹{savings:,.0f} over the New Regime. "
            f"Old Regime tax: ₹{old.total_tax:,.0f} vs New Regime tax: ₹{new.total_tax:,.0f}. "
            f"Key deductions: {top_deds}."
        )
    else:
        # New wins
        rationale = (
            f"New Regime saves ₹{savings:,.0f} over the Old Regime. "
            f"New Regime tax: ₹{new.total_tax:,.0f} vs Old Regime tax: ₹{old.total_tax:,.0f}. "
            f"Your total eligible Old Regime deductions (₹{old.total_deductions:,.0f}) "
            f"are insufficient to overcome the lower New Regime slab rates."
        )

    # Step 4: Generate suggestions
    old_suggestions = generate_old_suggestions(profile, old)
    new_suggestions = generate_new_suggestions(profile, new)

    return TaxResult(
        old_regime=old,
        new_regime=new,
        recommended_regime=recommended,
        savings_amount=round(savings, 2),
        rationale=rationale,
        old_regime_suggestions=old_suggestions,
        new_regime_suggestions=new_suggestions,
    )
