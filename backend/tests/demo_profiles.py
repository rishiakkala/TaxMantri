"""
Demo profile fixtures for TaxMantri end-to-end tests — AY 2025-26

Three CA-verified profiles used as the primary integration test data set.
Expected values derived from step-by-step hand-computation in Phase 2 CONTEXT.md
and verified by the tax engine test suite (test_tax_engine.py).

All monetary tolerance: ±₹50 (consistent with pytest.approx(abs=50) in test suite).
"""
from __future__ import annotations
from typing import Any

# ---------------------------------------------------------------------------
# Profile 1: Priya — ₹12L basic, metro, partial deductions
# ---------------------------------------------------------------------------
_PRIYA_PROFILE: dict[str, Any] = dict(
    basic_salary=1_200_000,
    hra_received=300_000,
    monthly_rent_paid=15_000,       # annual = 180,000
    city_type="metro",
    age_bracket="under60",
    parent_senior_citizen=False,
    input_method="manual",
    other_allowances=0,
    professional_tax=0,
    investments_80c=100_000,
    health_insurance_self=20_000,
    health_insurance_parents=0,
    employee_nps_80ccd1b=0,
    employer_nps_80ccd2=0,
    home_loan_interest=0,
    savings_interest_80tta=0,
    other_income=0,
)
# HRA Rule 2A: comp1=300000, comp2=50%*1200000=600000, comp3=180000-120000=60000 → 60000
# OLD: gross=1500000, ded=230000(std50+hra60+80c100+80d20), taxable=1270000
# slab: 12500+100000+81000=193500, no 87A (>5L), cess=7740, total=201240
# NEW: gross=1500000, std=75000, taxable=1425000 (>12L, no rebate)
# slab: 0+20000+40000+33750=93750, cess=3750, total=97500
_PRIYA_EXPECTED: dict[str, Any] = dict(
    expected_old_tax=201_240,
    expected_new_tax=97_500,
    expected_regime="new",
    expected_savings=103_740,
)

# ---------------------------------------------------------------------------
# Profile 2: Rahul — ₹25L basic, metro, max deductions, senior-citizen parents
# ---------------------------------------------------------------------------
_RAHUL_PROFILE: dict[str, Any] = dict(
    basic_salary=2_500_000,
    hra_received=800_000,
    monthly_rent_paid=35_000,       # annual = 420,000
    city_type="metro",
    age_bracket="under60",
    parent_senior_citizen=True,     # senior citizen parents → 80D parents cap 50,000
    input_method="manual",
    other_allowances=0,
    professional_tax=0,
    investments_80c=150_000,        # maxed
    health_insurance_self=25_000,
    health_insurance_parents=50_000,    # senior citizen cap
    employee_nps_80ccd1b=50_000,
    employer_nps_80ccd2=120_000,
    home_loan_interest=200_000,         # maxed at Section 24(b) cap
    savings_interest_80tta=0,
    other_income=0,
)
# HRA: comp1=800000, comp2=50%*2500000=1250000, comp3=420000-250000=170000 → 170000
# OLD: gross=3300000, ded=695000(std50+hra170+80c150+80d75+nps50+24b200), taxable=2605000
# slab: 12500+100000+481500=594000, no 87A, cess=23760, total=617760
# NEW: gross=3300000, std=75000+empl_nps=120000=195000, taxable=3105000
# slab: 0+20000+40000+60000+80000+100000+30%*705000=511500, cess=20460, total=531960
_RAHUL_EXPECTED: dict[str, Any] = dict(
    expected_old_tax=617_760,
    expected_new_tax=531_960,
    expected_regime="new",
    expected_savings=85_800,
)

# ---------------------------------------------------------------------------
# Profile 3: Anita — ₹8L basic, non-metro, minimal deductions
# ---------------------------------------------------------------------------
_ANITA_PROFILE: dict[str, Any] = dict(
    basic_salary=800_000,
    hra_received=0,
    monthly_rent_paid=0,
    city_type="non_metro",
    age_bracket="under60",
    parent_senior_citizen=False,
    input_method="manual",
    other_allowances=0,
    professional_tax=0,
    investments_80c=50_000,
    health_insurance_self=0,
    health_insurance_parents=0,
    employee_nps_80ccd1b=0,
    employer_nps_80ccd2=0,
    home_loan_interest=0,
    savings_interest_80tta=0,
    other_income=0,
)
# OLD: gross=800000, ded=100000(std50+80c50), taxable=700000 (>5L, no 87A)
# slab: 12500+40000=52500, cess=2100, total=54600
# NEW: gross=800000, std=75000, taxable=725000 (<12L, 87A applies)
# slab: 0+16250=16250 (4L→7.25L), 87A: rebate=16250 (<=60000), net=0, total=0
_ANITA_EXPECTED: dict[str, Any] = dict(
    expected_old_tax=54_600,
    expected_new_tax=0,
    expected_regime="new",
    expected_savings=54_600,
)

# ---------------------------------------------------------------------------
# Public API — single dict keyed by profile name
# ---------------------------------------------------------------------------
DEMO_PROFILES: dict[str, dict[str, Any]] = {
    "priya": {"profile": _PRIYA_PROFILE, "expected": _PRIYA_EXPECTED},
    "rahul": {"profile": _RAHUL_PROFILE, "expected": _RAHUL_EXPECTED},
    "anita": {"profile": _ANITA_PROFILE, "expected": _ANITA_EXPECTED},
}

__all__ = ["DEMO_PROFILES"]
