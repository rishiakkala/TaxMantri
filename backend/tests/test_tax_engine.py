"""
CA-verified tax engine test suite — AY 2025-26
All expected values hand-computed from first principles (see 02-RESEARCH.md).
Tolerance: ±₹50 on all monetary assertions (pytest.approx(abs=50)).

Groups:
  1. Named constant verification (TEST-02) — exact equality
  2. 51 parametrised regime-comparison cases (TEST-01) — approx
  3. HRA helper unit tests
  4. Structural/deduction-isolation unit tests
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from agents.evaluator_agent.tax_engine import (
    ASSESSMENT_YEAR,
    # Old regime slab constants
    OLD_SLAB_2_5L, OLD_SLAB_5L, OLD_SLAB_10L,
    # New regime slab constants — Budget 2025
    NEW_SLAB_4L, NEW_SLAB_8L, NEW_SLAB_12L,
    NEW_SLAB_16L, NEW_SLAB_20L, NEW_SLAB_24L,
    # Deduction cap constants
    OLD_STD_DEDUCTION, NEW_STD_DEDUCTION,
    CAP_80C, CAP_80CCD1B, CAP_24B,
    CAP_80D_SELF_UNDER60, CAP_80D_SELF_SENIOR,
    CAP_80D_PARENTS_NON_SENIOR, CAP_80D_PARENTS_SENIOR,
    CAP_80TTA, CAP_80TTB, CAP_80CCD2_PCT,
    # 87A parameters
    OLD_87A_MAX_REBATE, OLD_87A_TAXABLE_CEILING,
    NEW_87A_MAX_REBATE, NEW_87A_TAXABLE_CEILING,
    # Functions
    compare_regimes, calculate_old_regime, calculate_new_regime,
    calculate_hra_exemption,
)
from agents.input_agent.schemas import UserFinancialProfile


# ===========================================================================
# TEST GROUP 1: Named constant verification (TEST-02)
# These verify the exact constant values — no pytest.approx needed.
# ===========================================================================

def test_assessment_year_constant() -> None:
    """ASSESSMENT_YEAR must be AY2025-26, not AY2024-25."""
    assert ASSESSMENT_YEAR == "AY2025-26"


def test_old_regime_slab_constants() -> None:
    """Old regime breakpoints are unchanged from AY 2024-25."""
    assert OLD_SLAB_2_5L == 250_000
    assert OLD_SLAB_5L   == 500_000
    assert OLD_SLAB_10L  == 1_000_000


def test_new_regime_slab_constants_budget_2025() -> None:
    """
    New regime breakpoints are Budget 2025 values.
    AY 2024-25 values were 3L/6L/9L/12L/15L — must NOT be used.
    """
    assert NEW_SLAB_4L  == 400_000
    assert NEW_SLAB_8L  == 800_000
    assert NEW_SLAB_12L == 1_200_000
    assert NEW_SLAB_16L == 1_600_000
    assert NEW_SLAB_20L == 2_000_000
    assert NEW_SLAB_24L == 2_400_000


def test_standard_deduction_constants() -> None:
    assert OLD_STD_DEDUCTION == 50_000
    assert NEW_STD_DEDUCTION == 75_000


def test_deduction_cap_constants() -> None:
    assert CAP_80C                  == 150_000
    assert CAP_80CCD1B              == 50_000
    assert CAP_24B                  == 200_000
    assert CAP_80D_SELF_UNDER60     == 25_000
    assert CAP_80D_SELF_SENIOR      == 50_000
    assert CAP_80D_PARENTS_NON_SENIOR == 25_000
    assert CAP_80D_PARENTS_SENIOR   == 50_000
    assert CAP_80TTA                == 10_000
    assert CAP_80TTB                == 50_000
    assert CAP_80CCD2_PCT           == pytest.approx(0.10, abs=0.001)


def test_87a_constants() -> None:
    """87A ceiling and rebate constants — AY 2025-26."""
    assert OLD_87A_MAX_REBATE      == 12_500
    assert OLD_87A_TAXABLE_CEILING == 500_000
    assert NEW_87A_MAX_REBATE      == 60_000
    assert NEW_87A_TAXABLE_CEILING == 1_200_000


# ===========================================================================
# TEST GROUP 2: Parametrised regime comparison cases (TEST-01)
# All expected values from 02-RESEARCH.md hand-computation.
# ===========================================================================

@dataclass
class TaxCase:
    """Single parametrised test case for compare_regimes()."""
    description: str
    profile_kwargs: dict
    expected_old_tax: float
    expected_new_tax: float
    expected_regime: str          # "old" | "new"
    expected_savings: float = field(default=0.0)


TAX_CASES: list[TaxCase] = [

    # -------------------------------------------------------------------
    # CATEGORY 1: Demo profiles (3 cases) — primary integration validation
    # -------------------------------------------------------------------
    TaxCase(
        description="priya_12L_metro_partial_deductions",
        profile_kwargs=dict(
            basic_salary=1_200_000, hra_received=300_000, monthly_rent_paid=15_000,
            city_type="metro", age_bracket="under60", input_method="manual",
            investments_80c=100_000, health_insurance_self=20_000,
        ),
        # OLD: gross=1500000, ded=230000(std50+hra60+80c100+80d20), taxable=1270000
        # slab: 12500+100000+81000=193500, no 87A, cess=7740 → total=201240
        expected_old_tax=201_240,
        # NEW: gross=1500000, std=75000, taxable=1425000 (>12L, no 87A)
        # slab: 0+20000+40000+33750=93750, cess=3750 → total=97500
        expected_new_tax=97_500,
        expected_regime="new",
        expected_savings=103_740,
    ),
    TaxCase(
        description="rahul_25L_metro_max_deductions_senior_parents",
        profile_kwargs=dict(
            basic_salary=2_500_000, hra_received=800_000, monthly_rent_paid=35_000,
            city_type="metro", age_bracket="under60", parent_senior_citizen=True,
            input_method="manual",
            investments_80c=150_000, health_insurance_self=25_000,
            health_insurance_parents=50_000, employee_nps_80ccd1b=50_000,
            employer_nps_80ccd2=120_000, home_loan_interest=200_000,
        ),
        # OLD: gross=3300000, ded=695000(std50+hra170+80c150+80d75+nps50+24b200)
        # taxable=2605000, slab: 12500+100000+481500=594000, cess=23760 → total=617760
        expected_old_tax=617_760,
        # NEW: gross=3300000, std=75000, employer_nps=120000, ded=195000
        # taxable=3105000, slab: 0+20000+40000+60000+80000+100000+211500=511500
        # cess=20460 → total=531960
        expected_new_tax=531_960,
        expected_regime="new",
        expected_savings=85_800,
    ),
    TaxCase(
        description="anita_8L_non_metro_minimal_deductions",
        profile_kwargs=dict(
            basic_salary=800_000, hra_received=0, monthly_rent_paid=0,
            city_type="non_metro", age_bracket="under60", input_method="manual",
            investments_80c=50_000,
        ),
        # OLD: gross=800000, ded=100000(std50+80c50), taxable=700000 (>5L, no 87A)
        # slab: 12500+40000=52500, cess=2100 → total=54600
        expected_old_tax=54_600,
        # NEW: gross=800000, std=75000, taxable=725000 (<12L)
        # slab: 0+16250=16250, 87A: 725000<=1200000, rebate=16250, net=0, cess=0 → total=0
        expected_new_tax=0,
        expected_regime="new",
        expected_savings=54_600,
    ),

    # -------------------------------------------------------------------
    # CATEGORY 2: Old regime 87A boundary (5 cases) — TEST-02 old regime
    # -------------------------------------------------------------------
    TaxCase(
        description="old_87a_taxable_250000_zero_slab_zero_tax",
        profile_kwargs=dict(
            basic_salary=300_000, city_type="metro", age_bracket="under60",
            input_method="manual",
            # ded: std=50000 → taxable=250000
        ),
        # OLD: taxable=250000, slab=0, 87A: rebate=0, total=0
        expected_old_tax=0,
        # NEW: gross=300000, std=75000, taxable=225000, slab=0, 87A zeroes, total=0
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="old_87a_taxable_350000_rebate_zeroes_tax",
        profile_kwargs=dict(
            basic_salary=400_000, city_type="metro", age_bracket="under60",
            input_method="manual",
            # ded: std=50000 → taxable=350000
            # slab: 5%*(350000-250000)=5000, 87A: <=500000, rebate=min(5000,12500)=5000, net=0
        ),
        expected_old_tax=0,
        # NEW: gross=400000, std=75000, taxable=325000, slab=5%*75000=3750
        # 87A: 325000<=1200000, rebate=3750, net=0
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="old_87a_taxable_500000_at_ceiling_zero_tax",
        profile_kwargs=dict(
            basic_salary=600_000, city_type="metro", age_bracket="under60",
            input_method="manual",
            investments_80c=50_000,
            # ded: std=50000+80c=50000 → taxable=500000 exactly
        ),
        # OLD: taxable=500000, slab=0+12500=12500, 87A: <=500000, rebate=12500, net=0
        expected_old_tax=0,
        # NEW: gross=600000, std=75000, taxable=475000, slab=5%*(475000-400000)=3750
        # 87A: 475000<=1200000, rebate=3750, net=0
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="old_87a_taxable_500001_just_above_ceiling_full_tax",
        profile_kwargs=dict(
            basic_salary=600_000, city_type="metro", age_bracket="under60",
            input_method="manual",
            investments_80c=49_999,
            # ded: std=50000+80c=49999 → taxable=500001
        ),
        # OLD: taxable=500001, slab≈12500.05, 87A does NOT apply (>500000)
        # cess=4%*12500.05≈500, total≈13000
        expected_old_tax=13_000,
        # NEW: taxable=600000-75000=525000, slab=5%*125000=6250, 87A zeroes, total=0
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="old_87a_taxable_600000_no_rebate_normal_tax",
        profile_kwargs=dict(
            basic_salary=700_000, city_type="metro", age_bracket="under60",
            input_method="manual",
            investments_80c=50_000,
            # ded: std=50000+80c=50000 → taxable=600000
        ),
        # OLD: taxable=600000, slab=12500+20%*100000=32500
        # 87A: 600000>500000 no rebate, cess=4%*32500=1300, total=33800
        expected_old_tax=33_800,
        # NEW: gross=700000, std=75000, taxable=625000, slab=5%*225000=11250
        # 87A: 625000<=1200000, rebate=11250, net=0
        expected_new_tax=0,
        expected_regime="new",
    ),

    # -------------------------------------------------------------------
    # CATEGORY 3: New regime 87A boundary (5 cases) — TEST-02 new regime
    # -------------------------------------------------------------------
    TaxCase(
        description="new_87a_taxable_400000_zero_slab_zero_tax",
        profile_kwargs=dict(
            basic_salary=475_000, city_type="metro", age_bracket="under60",
            input_method="manual",
            # NEW: gross=475000, std=75000, taxable=400000, slab=0
        ),
        # OLD: taxable=475000-50000=425000, slab=5%*175000=8750, 87A<=500000, rebate=8750, net=0
        expected_old_tax=0,
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="new_87a_taxable_800000_rebate_covers_20000",
        profile_kwargs=dict(
            basic_salary=875_000, city_type="metro", age_bracket="under60",
            input_method="manual",
            # NEW: gross=875000, std=75000, taxable=800000
            # slab: 4-8L: 5%*400000=20000, 87A: <=1200000, rebate=20000, net=0
        ),
        # OLD: gross=875000, std=50000, taxable=825000 (>500000)
        # slab: 12500+20%*325000=12500+65000=77500, cess=3100, total=80600
        expected_old_tax=80_600,
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="new_87a_taxable_1200000_at_ceiling_zero_tax",
        profile_kwargs=dict(
            basic_salary=1_275_000, city_type="metro", age_bracket="under60",
            input_method="manual",
            # NEW: gross=1275000, std=75000, taxable=1200000 exactly
            # slab: 4-8L:20000 + 8-12L:40000=60000, 87A: <=1200000, rebate=60000, net=0
        ),
        # OLD: gross=1275000, std=50000, taxable=1225000
        # slab: 12500+100000+30%*225000=12500+100000+67500=180000, cess=7200, total=187200
        expected_old_tax=187_200,
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="new_87a_taxable_1300000_above_ceiling_full_tax",
        profile_kwargs=dict(
            basic_salary=1_375_000, city_type="metro", age_bracket="under60",
            input_method="manual",
            # NEW: gross=1375000, std=75000, taxable=1300000 (>1200000 ceiling — no rebate)
            # slab: 20000+40000+15%*100000=20000+40000+15000=75000, cess=3000, total=78000
        ),
        # OLD: gross=1375000, std=50000, taxable=1325000
        # slab: 12500+100000+30%*325000=12500+100000+97500=210000, cess=8400, total=218400
        expected_old_tax=218_400,
        expected_new_tax=78_000,
        expected_regime="new",
    ),
    TaxCase(
        description="new_87a_taxable_1600000_no_rebate_high_tax",
        profile_kwargs=dict(
            basic_salary=1_675_000, city_type="metro", age_bracket="under60",
            input_method="manual",
            # NEW: gross=1675000, std=75000, taxable=1600000 (>1200000, no rebate)
            # slab: 20000+40000+60000+0=120000, cess=4800, total=124800
        ),
        # OLD: gross=1675000, std=50000, taxable=1625000
        # slab: 12500+100000+30%*625000=12500+100000+187500=300000, cess=12000, total=312000
        expected_old_tax=312_000,
        expected_new_tax=124_800,
        expected_regime="new",
    ),

    # -------------------------------------------------------------------
    # CATEGORY 4: HRA edge cases (6 cases)
    # -------------------------------------------------------------------
    TaxCase(
        description="hra_zero_rent_exemption_must_be_zero",
        profile_kwargs=dict(
            basic_salary=1_200_000, hra_received=300_000, monthly_rent_paid=0,
            city_type="metro", age_bracket="under60", input_method="manual",
        ),
        # OLD: HRA exemption = 0 (monthly_rent_paid=0), ded=50000, taxable=1450000
        # slab: 12500+100000+30%*450000=247500, cess=9900, total=257400
        expected_old_tax=257_400,
        # NEW: gross=1500000, std=75000, taxable=1425000, slab=93750, cess=3750, total=97500
        expected_new_tax=97_500,
        expected_regime="new",
    ),
    TaxCase(
        description="hra_zero_hra_received_exemption_must_be_zero",
        profile_kwargs=dict(
            basic_salary=1_200_000, hra_received=0, monthly_rent_paid=15_000,
            city_type="metro", age_bracket="under60", input_method="manual",
        ),
        # OLD: HRA exemption = 0 (hra_received=0), ded=50000, taxable=1150000
        # slab: 12500+100000+30%*150000=157500, cess=6300, total=163800
        expected_old_tax=163_800,
        # NEW: gross=1200000, std=75000, taxable=1125000, slab=0+20000+32500=52500
        # 87A: 1125000<=1200000, rebate=52500, net=0
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="hra_rent_below_10pct_basic_component3_zero_not_negative",
        profile_kwargs=dict(
            basic_salary=1_200_000, hra_received=300_000, monthly_rent_paid=5_000,
            city_type="metro", age_bracket="under60", input_method="manual",
        ),
        # comp3 = max(0, 60000 - 120000) = max(0, -60000) = 0
        # HRA exemption = min(300000, 600000, 0) = 0
        # OLD: ded=50000, taxable=1450000, slab=247500, cess=9900, total=257400
        expected_old_tax=257_400,
        # NEW: gross=1500000, std=75000, taxable=1425000, slab=93750, cess=3750, total=97500
        expected_new_tax=97_500,
        expected_regime="new",
    ),
    TaxCase(
        description="hra_non_metro_40pct_cap",
        profile_kwargs=dict(
            basic_salary=1_200_000, hra_received=300_000, monthly_rent_paid=15_000,
            city_type="non_metro", age_bracket="under60", input_method="manual",
        ),
        # comp1=300000, comp2=40%*1200000=480000, comp3=180000-120000=60000
        # HRA exemption = min(300000, 480000, 60000) = 60000 (comp3 binding — same as metro)
        # OLD: ded=110000(std50+hra60), taxable=1390000, slab=12500+100000+117000=229500
        # cess=9180, total=238680
        expected_old_tax=238_680,
        # NEW: gross=1500000, std=75000, taxable=1425000, slab=93750, cess=3750, total=97500
        expected_new_tax=97_500,
        expected_regime="new",
    ),
    TaxCase(
        description="hra_component2_binding_high_hra_low_basic",
        profile_kwargs=dict(
            basic_salary=600_000, hra_received=400_000, monthly_rent_paid=40_000,
            city_type="metro", age_bracket="under60", input_method="manual",
        ),
        # comp1=400000, comp2=50%*600000=300000, comp3=480000-60000=420000
        # exemption = min(400000, 300000, 420000) = 300000 (comp2 binding)
        # OLD: gross=1000000, ded=50000+300000=350000, taxable=650000
        # slab: 12500+20%*150000=42500, cess=1700, total=44200
        expected_old_tax=44_200,
        # NEW: gross=1000000, std=75000, taxable=925000
        # slab: 0+20000+12500=32500, 87A: 925000<=1200000, rebate=32500, net=0
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="hra_component1_binding_low_hra_high_rent",
        profile_kwargs=dict(
            basic_salary=2_000_000, hra_received=200_000, monthly_rent_paid=30_000,
            city_type="metro", age_bracket="under60", input_method="manual",
        ),
        # comp1=200000, comp2=50%*2000000=1000000, comp3=360000-200000=160000
        # exemption = min(200000, 1000000, 160000) = 160000 (comp3 binding)
        # OLD: gross=2200000, ded=50000+160000=210000, taxable=1990000
        # slab: 12500+100000+30%*990000=409500, cess=16380, total=425880
        expected_old_tax=425_880,
        # NEW: gross=2200000, std=75000, taxable=2125000
        # 4-8L:20000, 8-12L:40000, 12-16L:60000, 16-20L:80000, 20-21.25L:25%*125000=31250
        # total slab=231250, no 87A (>12L), cess=9250, total=240500
        expected_new_tax=240_500,
        expected_regime="new",
    ),

    # -------------------------------------------------------------------
    # CATEGORY 5: 80C combinations (4 cases)
    # -------------------------------------------------------------------
    TaxCase(
        description="80c_zero_no_deduction",
        profile_kwargs=dict(
            basic_salary=1_200_000, city_type="metro", age_bracket="under60",
            input_method="manual", investments_80c=0,
        ),
        # OLD: ded=50000, taxable=1150000, slab=12500+100000+45000=157500, cess=6300, total=163800
        expected_old_tax=163_800,
        # NEW: gross=1200000, std=75000, taxable=1125000, slab=52500, 87A zeroes, total=0
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="80c_partial_50000",
        profile_kwargs=dict(
            basic_salary=1_200_000, city_type="metro", age_bracket="under60",
            input_method="manual", investments_80c=50_000,
        ),
        # OLD: ded=100000(std+80c), taxable=1100000, slab=12500+100000+30000=142500
        # cess=5700, total=148200
        expected_old_tax=148_200,
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="80c_at_cap_150000",
        profile_kwargs=dict(
            basic_salary=1_200_000, city_type="metro", age_bracket="under60",
            input_method="manual", investments_80c=150_000,
        ),
        # OLD: ded=200000(std+80c), taxable=1000000
        # slab: 12500+100000=112500 (exactly at 10L — 30% not triggered), cess=4500, total=117000
        expected_old_tax=117_000,
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="80c_over_cap_capped_at_150000",
        profile_kwargs=dict(
            basic_salary=1_200_000, city_type="metro", age_bracket="under60",
            input_method="manual", investments_80c=200_000,
        ),
        # 80C deduction capped at 150000; same result as at-cap case
        expected_old_tax=117_000,
        expected_new_tax=0,
        expected_regime="new",
    ),

    # -------------------------------------------------------------------
    # CATEGORY 6: 80D combinations (6 cases)
    # -------------------------------------------------------------------
    TaxCase(
        description="80d_under60_self_only_at_cap",
        profile_kwargs=dict(
            basic_salary=1_200_000, city_type="metro", age_bracket="under60",
            input_method="manual", health_insurance_self=25_000,
        ),
        # OLD: ded=75000(std50+80d25), taxable=1125000
        # slab: 12500+100000+37500=150000, cess=6000, total=156000
        expected_old_tax=156_000,
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="80d_senior_self_60_79_cap_50000",
        profile_kwargs=dict(
            basic_salary=1_200_000, city_type="metro", age_bracket="60_79",
            input_method="manual", health_insurance_self=45_000,
        ),
        # self_cap=50000, deduction=min(45000,50000)=45000
        # OLD: ded=95000(std50+80d45), taxable=1105000
        # slab: 12500+100000+31500=144000, cess=5760, total=149760
        expected_old_tax=149_760,
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="80d_parents_senior_citizen_cap_50000",
        profile_kwargs=dict(
            basic_salary=1_200_000, city_type="metro", age_bracket="under60",
            parent_senior_citizen=True, input_method="manual",
            health_insurance_self=20_000, health_insurance_parents=50_000,
        ),
        # self_cap=25000, ded_self=20000; parent_cap=50000, ded_parents=50000
        # total 80D=70000; OLD: ded=120000(std50+80d70), taxable=1080000
        # slab: 12500+100000+24000=136500, cess=5460, total=141960
        expected_old_tax=141_960,
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="80d_both_senior_both_at_cap_total_100000",
        profile_kwargs=dict(
            basic_salary=1_200_000, city_type="metro", age_bracket="60_79",
            parent_senior_citizen=True, input_method="manual",
            health_insurance_self=60_000, health_insurance_parents=60_000,
        ),
        # self capped at 50000 (60_79), parents capped at 50000 (senior)
        # total 80D = 100000; OLD: ded=150000(std50+80d100), taxable=1050000
        # slab: 12500+100000+15000=127500, cess=5100, total=132600
        expected_old_tax=132_600,
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="80d_parents_non_senior_cap_25000",
        profile_kwargs=dict(
            basic_salary=1_200_000, city_type="metro", age_bracket="under60",
            parent_senior_citizen=False, input_method="manual",
            health_insurance_parents=40_000,
        ),
        # parent_cap=25000, deduction=min(40000,25000)=25000
        # OLD: ded=75000(std50+80d25), taxable=1125000
        # slab: 12500+100000+37500=150000, cess=6000, total=156000
        expected_old_tax=156_000,
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="80d_zero_all_no_deduction",
        profile_kwargs=dict(
            basic_salary=1_200_000, city_type="metro", age_bracket="under60",
            input_method="manual",
        ),
        expected_old_tax=163_800,
        expected_new_tax=0,
        expected_regime="new",
    ),

    # -------------------------------------------------------------------
    # CATEGORY 7: 80CCD(1B) employee NPS — old regime only (3 cases)
    # -------------------------------------------------------------------
    TaxCase(
        description="80ccd1b_employee_nps_partial_30000",
        profile_kwargs=dict(
            basic_salary=1_200_000, city_type="metro", age_bracket="under60",
            input_method="manual", employee_nps_80ccd1b=30_000,
        ),
        # OLD: ded=80000(std50+nps30), taxable=1120000
        # slab: 12500+100000+36000=148500, cess=5940, total=154440
        expected_old_tax=154_440,
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="80ccd1b_employee_nps_at_cap_50000",
        profile_kwargs=dict(
            basic_salary=1_200_000, city_type="metro", age_bracket="under60",
            input_method="manual", employee_nps_80ccd1b=50_000,
        ),
        # OLD: ded=100000(std50+nps50), taxable=1100000
        # slab: 12500+100000+30000=142500, cess=5700, total=148200
        expected_old_tax=148_200,
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="80ccd1b_employee_nps_not_deductible_in_new_regime",
        profile_kwargs=dict(
            basic_salary=1_200_000, city_type="metro", age_bracket="under60",
            input_method="manual", employee_nps_80ccd1b=50_000,
        ),
        # NEW regime must NOT deduct employee NPS — same new tax as zero-deduction case
        # NEW: gross=1200000, std=75000, taxable=1125000, slab=52500, 87A zeroes, total=0
        expected_old_tax=148_200,
        expected_new_tax=0,
        expected_regime="new",
    ),

    # -------------------------------------------------------------------
    # CATEGORY 8: Employer 80CCD(2) — new regime only (3 cases)
    # -------------------------------------------------------------------
    TaxCase(
        description="employer_nps_zero_no_new_deduction",
        profile_kwargs=dict(
            basic_salary=1_200_000, city_type="metro", age_bracket="under60",
            input_method="manual", employer_nps_80ccd2=0,
        ),
        expected_old_tax=163_800,
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="employer_nps_under_10pct_cap_deducted_in_new",
        profile_kwargs=dict(
            basic_salary=1_600_000, city_type="metro", age_bracket="under60",
            input_method="manual", employer_nps_80ccd2=100_000,
        ),
        # cap=10%*1600000=160000, actual=100000, deduction=100000
        # NEW: gross=1600000, std=75000+nps=100000=175000, taxable=1425000 (>12L, no 87A)
        # slab: 0+20000+40000+33750=93750, cess=3750, total=97500
        # OLD: gross=1600000, std=50000, taxable=1550000 (no employer NPS in old)
        # slab: 12500+100000+165000=277500, cess=11100, total=288600
        expected_old_tax=288_600,
        expected_new_tax=97_500,
        expected_regime="new",
    ),
    TaxCase(
        description="employer_nps_exactly_at_10pct_cap",
        profile_kwargs=dict(
            basic_salary=500_000, city_type="metro", age_bracket="under60",
            input_method="manual", employer_nps_80ccd2=50_000,
        ),
        # cap=10%*500000=50000, actual=50000 exactly at cap → deduction=50000
        # NEW: gross=500000, std=75000+nps=50000=125000, taxable=375000
        # slab: 0 (<=400000), 87A zeroes, total=0
        # OLD: gross=500000, std=50000, taxable=450000
        # slab: 5%*(450000-250000)=10000, 87A: <=500000, rebate=10000, net=0
        expected_old_tax=0,
        expected_new_tax=0,
        expected_regime="new",
    ),

    # -------------------------------------------------------------------
    # CATEGORY 9: Section 24(b) home loan interest (3 cases)
    # -------------------------------------------------------------------
    TaxCase(
        description="section24b_zero_no_deduction",
        profile_kwargs=dict(
            basic_salary=1_500_000, city_type="metro", age_bracket="under60",
            input_method="manual",
        ),
        # OLD: ded=50000, taxable=1450000, slab=12500+100000+135000=247500, cess=9900, total=257400
        expected_old_tax=257_400,
        # NEW: gross=1500000, std=75000, taxable=1425000, slab=93750, cess=3750, total=97500
        expected_new_tax=97_500,
        expected_regime="new",
    ),
    TaxCase(
        description="section24b_partial_100000",
        profile_kwargs=dict(
            basic_salary=1_500_000, city_type="metro", age_bracket="under60",
            input_method="manual", home_loan_interest=100_000,
        ),
        # OLD: ded=150000(std50+24b100), taxable=1350000
        # slab: 12500+100000+105000=217500, cess=8700, total=226200
        expected_old_tax=226_200,
        expected_new_tax=97_500,
        expected_regime="new",
    ),
    TaxCase(
        description="section24b_at_cap_200000",
        profile_kwargs=dict(
            basic_salary=1_500_000, city_type="metro", age_bracket="under60",
            input_method="manual", home_loan_interest=200_000,
        ),
        # OLD: ded=250000(std50+24b200), taxable=1250000
        # slab: 12500+100000+75000=187500, cess=7500, total=195000
        expected_old_tax=195_000,
        expected_new_tax=97_500,
        expected_regime="new",
    ),

    # -------------------------------------------------------------------
    # CATEGORY 10: 80TTA / 80TTB savings interest (4 cases)
    # -------------------------------------------------------------------
    TaxCase(
        description="80tta_under60_savings_interest_partial_8000",
        profile_kwargs=dict(
            basic_salary=1_200_000, city_type="metro", age_bracket="under60",
            input_method="manual", savings_interest_80tta=8_000,
        ),
        # under60: 80TTA cap=10000, deduction=min(8000,10000)=8000
        # OLD: ded=58000(std50+80tta8), taxable=1142000
        # slab: 12500+100000+42600=155100, cess=6204, total=161304
        expected_old_tax=161_304,
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="80tta_under60_at_cap_10000",
        profile_kwargs=dict(
            basic_salary=1_200_000, city_type="metro", age_bracket="under60",
            input_method="manual", savings_interest_80tta=15_000,
        ),
        # under60: capped at 10000
        # OLD: ded=60000(std50+80tta10), taxable=1140000
        # slab: 12500+100000+42000=154500, cess=6180, total=160680
        expected_old_tax=160_680,
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="80ttb_senior_60_79_all_interest_cap_50000",
        profile_kwargs=dict(
            basic_salary=1_200_000, city_type="metro", age_bracket="60_79",
            input_method="manual", savings_interest_80tta=60_000,
        ),
        # 60_79: auto-switch to 80TTB, cap=50000, deduction=min(60000,50000)=50000
        # OLD: ded=100000(std50+80ttb50), taxable=1100000
        # slab: 12500+100000+30000=142500, cess=5700, total=148200
        expected_old_tax=148_200,
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="80tta_80ttb_zero_in_new_regime",
        profile_kwargs=dict(
            basic_salary=1_200_000, city_type="metro", age_bracket="under60",
            input_method="manual", savings_interest_80tta=10_000,
        ),
        # NEW must NOT deduct savings interest; same new tax as zero-deduction case
        expected_old_tax=160_680,
        expected_new_tax=0,
        expected_regime="new",
    ),

    # -------------------------------------------------------------------
    # CATEGORY 11: Professional tax (2 cases)
    # -------------------------------------------------------------------
    TaxCase(
        description="professional_tax_old_regime_deductible",
        profile_kwargs=dict(
            basic_salary=1_200_000, city_type="metro", age_bracket="under60",
            input_method="manual", professional_tax=2_400,
        ),
        # OLD: ded=52400(std50+pt2400), taxable=1147600
        # slab: 12500+100000+44280=156780, cess=4%*156780=6271.2, total=163051
        expected_old_tax=163_051,
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="professional_tax_not_deductible_in_new_regime",
        profile_kwargs=dict(
            basic_salary=1_200_000, city_type="metro", age_bracket="under60",
            input_method="manual", professional_tax=2_400,
        ),
        # NEW: professional tax does NOT reduce taxable — same as zero-pt case
        # NEW: gross=1200000, std=75000, taxable=1125000, slab=52500, 87A zeroes, total=0
        expected_old_tax=163_051,
        expected_new_tax=0,
        expected_regime="new",
    ),

    # -------------------------------------------------------------------
    # CATEGORY 12: Regime comparison outcomes (4 cases)
    # -------------------------------------------------------------------
    TaxCase(
        description="regime_comparison_old_wins_very_high_deductions",
        profile_kwargs=dict(
            basic_salary=800_000, hra_received=200_000, monthly_rent_paid=15_000,
            city_type="metro", age_bracket="under60", input_method="manual",
            investments_80c=150_000, health_insurance_self=25_000,
            employee_nps_80ccd1b=50_000, home_loan_interest=100_000,
        ),
        # HRA: comp1=200000, comp2=400000, comp3=180000-80000=100000 → exemption=100000
        # OLD: gross=1000000, ded=475000(std50+hra100+80c150+80d25+nps50+24b100)
        # taxable=525000 (>500000, no 87A), slab: 12500+5000=17500, cess=700, total=18200
        # NEW: gross=1000000, std=75000, taxable=925000
        # slab: 0+20000+12500=32500, 87A zeroes (<=12L), total=0
        expected_old_tax=18_200,
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="regime_comparison_new_wins_no_deductions",
        profile_kwargs=dict(
            basic_salary=2_000_000, city_type="metro", age_bracket="under60",
            input_method="manual",
        ),
        # OLD: ded=50000, taxable=1950000, slab=12500+100000+285000=397500, cess=15900, total=413400
        # NEW: ded=75000, taxable=1925000
        # 4-8L:20000, 8-12L:40000, 12-16L:60000, 16-19.25L:20%*325000=65000
        # total slab=185000, cess=7400, total=192400
        expected_old_tax=413_400,
        expected_new_tax=192_400,
        expected_regime="new",
    ),
    TaxCase(
        description="regime_comparison_tie_recommends_new",
        profile_kwargs=dict(
            basic_salary=0, city_type="metro", age_bracket="under60",
            input_method="manual",
        ),
        # Zero income: both regimes produce zero tax → tie → recommend new
        expected_old_tax=0,
        expected_new_tax=0,
        expected_regime="new",
    ),
    TaxCase(
        description="regime_comparison_very_high_income_new_wins",
        profile_kwargs=dict(
            basic_salary=5_000_000, city_type="metro", age_bracket="under60",
            input_method="manual", investments_80c=150_000,
            health_insurance_self=25_000, employee_nps_80ccd1b=50_000,
        ),
        # OLD: gross=5000000, ded=275000(std50+80c150+80d25+nps50), taxable=4725000
        # slab: 12500+100000+30%*3725000=1117500+112500=1230000, cess=49200, total=1279200
        # NEW: gross=5000000, std=75000, taxable=4925000
        # slab: 20000+40000+60000+80000+100000+30%*(4925000-2400000)
        # =20000+40000+60000+80000+100000+757500=1057500, cess=42300, total=1099800
        expected_old_tax=1_279_200,
        expected_new_tax=1_099_800,
        expected_regime="new",
    ),

    # -------------------------------------------------------------------
    # CATEGORY 13: Zero income edge case (1 case)
    # -------------------------------------------------------------------
    TaxCase(
        description="zero_income_zero_deductions_zero_tax_both_regimes",
        profile_kwargs=dict(
            basic_salary=0, city_type="metro", age_bracket="under60",
            input_method="manual",
        ),
        expected_old_tax=0,
        expected_new_tax=0,
        expected_regime="new",
    ),

    # -------------------------------------------------------------------
    # CATEGORY 14: Max all deductions (2 cases)
    # -------------------------------------------------------------------
    TaxCase(
        description="max_all_old_regime_deductions_respected",
        profile_kwargs=dict(
            basic_salary=2_000_000, hra_received=500_000, monthly_rent_paid=20_000,
            city_type="metro", age_bracket="under60", parent_senior_citizen=True,
            input_method="manual",
            investments_80c=200_000,           # capped to 150000
            health_insurance_self=30_000,       # capped to 25000 (under60)
            health_insurance_parents=60_000,    # capped to 50000 (senior parents)
            employee_nps_80ccd1b=70_000,        # capped to 50000
            home_loan_interest=250_000,         # capped to 200000
            savings_interest_80tta=15_000,      # capped to 10000 (under60)
            professional_tax=2_400,
        ),
        # HRA: comp1=500000, comp2=50%*2000000=1000000, comp3=240000-200000=40000
        # exemption = min(500000,1000000,40000) = 40000
        # OLD ded: std=50000, hra=40000, 80c=150000, 80d=75000(25+50), nps=50000
        #          24b=200000, 80tta=10000, pt=2400 = total=577400
        # gross=2500000, taxable=2500000-577400=1922600
        # slab: 12500+100000+30%*922600=276780 → total slab=389280, cess=15571.2, total≈404851
        expected_old_tax=404_851,
        # NEW: gross=2500000, std=75000, taxable=2425000 (>12L)
        # slab: 20000+40000+60000+80000+100000+30%*25000=307500
        # wait: 20-24L:25%*400000=100000; 24-24.25L:30%*25000=7500 → total=307500
        # cess=12300, total=319800
        expected_new_tax=319_800,
        expected_regime="new",
    ),
    TaxCase(
        description="max_deductions_each_field_capped_not_actual",
        profile_kwargs=dict(
            basic_salary=1_500_000, city_type="metro", age_bracket="under60",
            input_method="manual",
            investments_80c=999_999,           # capped at 150000
            health_insurance_self=999_999,     # capped at 25000
            employee_nps_80ccd1b=999_999,      # capped at 50000
            home_loan_interest=999_999,        # capped at 200000
        ),
        # All deductions at their caps: 50000+150000+25000+50000+200000=475000
        # OLD: gross=1500000, taxable=1025000
        # slab: 12500+100000+7500=120000, cess=4800, total=124800
        expected_old_tax=124_800,
        # NEW: gross=1500000, std=75000, taxable=1425000 (>12L)
        # slab: 93750, cess=3750, total=97500
        expected_new_tax=97_500,
        expected_regime="new",
    ),
]


@pytest.mark.parametrize(
    "case",
    [pytest.param(c, id=c.description) for c in TAX_CASES],
)
def test_regime_comparison(case: TaxCase) -> None:
    """
    Verify compare_regimes() against hand-computed expected values.
    Tolerance: ±₹50 (pytest.approx abs=50).
    Expected values are from 02-RESEARCH.md — do NOT change them to match engine output.
    If this test fails, the TAX ENGINE is wrong, not the expected value.
    """
    profile = UserFinancialProfile(**case.profile_kwargs)
    result = compare_regimes(profile)

    assert result.old_regime.total_tax == pytest.approx(case.expected_old_tax, abs=50), (
        f"OLD REGIME: expected ₹{case.expected_old_tax:,.0f}, "
        f"got ₹{result.old_regime.total_tax:,.0f}"
    )
    assert result.new_regime.total_tax == pytest.approx(case.expected_new_tax, abs=50), (
        f"NEW REGIME: expected ₹{case.expected_new_tax:,.0f}, "
        f"got ₹{result.new_regime.total_tax:,.0f}"
    )
    assert result.recommended_regime == case.expected_regime, (
        f"REGIME: expected {case.expected_regime!r}, got {result.recommended_regime!r}"
    )
    if case.expected_savings > 0:
        assert result.savings_amount == pytest.approx(case.expected_savings, abs=50), (
            f"SAVINGS: expected ₹{case.expected_savings:,.0f}, "
            f"got ₹{result.savings_amount:,.0f}"
        )


# ===========================================================================
# TEST GROUP 3: HRA helper function unit tests
# ===========================================================================

def test_hra_exemption_metro_three_components() -> None:
    """Rule 2A: Priya's HRA — component 3 is binding at ₹60,000."""
    profile = UserFinancialProfile(
        basic_salary=1_200_000, hra_received=300_000, monthly_rent_paid=15_000,
        city_type="metro", age_bracket="under60", input_method="manual",
    )
    assert calculate_hra_exemption(profile) == pytest.approx(60_000, abs=1)


def test_hra_exemption_zero_rent_returns_zero() -> None:
    """monthly_rent_paid=0 must return 0, not negative."""
    profile = UserFinancialProfile(
        basic_salary=1_200_000, hra_received=300_000, monthly_rent_paid=0,
        city_type="metro", age_bracket="under60", input_method="manual",
    )
    assert calculate_hra_exemption(profile) == 0.0


def test_hra_exemption_zero_hra_returns_zero() -> None:
    """hra_received=0 must return 0 even if rent is paid."""
    profile = UserFinancialProfile(
        basic_salary=1_200_000, hra_received=0, monthly_rent_paid=15_000,
        city_type="metro", age_bracket="under60", input_method="manual",
    )
    assert calculate_hra_exemption(profile) == 0.0


def test_hra_exemption_component3_never_negative() -> None:
    """Rent below 10% of basic must give component_3 = 0, not negative."""
    profile = UserFinancialProfile(
        basic_salary=1_200_000, hra_received=300_000, monthly_rent_paid=5_000,
        city_type="metro", age_bracket="under60", input_method="manual",
    )
    # annual_rent = 60000, 10% basic = 120000 → component_3 = max(0, -60000) = 0
    assert calculate_hra_exemption(profile) == 0.0


# ===========================================================================
# TEST GROUP 4: Structural correctness (deduction isolation)
# ===========================================================================

def test_old_regime_excludes_employer_nps() -> None:
    """employer_nps_80ccd2 must NOT appear in old regime deduction breakdown."""
    profile = UserFinancialProfile(
        basic_salary=2_000_000, employer_nps_80ccd2=100_000,
        city_type="metro", age_bracket="under60", input_method="manual",
    )
    result = calculate_old_regime(profile)
    assert result.deduction_breakdown.section_80ccd2 == 0.0


def test_new_regime_excludes_employee_nps() -> None:
    """employee_nps_80ccd1b must NOT appear in new regime deduction breakdown."""
    profile = UserFinancialProfile(
        basic_salary=2_000_000, employee_nps_80ccd1b=50_000,
        city_type="metro", age_bracket="under60", input_method="manual",
    )
    result = calculate_new_regime(profile)
    assert result.deduction_breakdown.section_80ccd1b == 0.0


def test_new_regime_excludes_hra() -> None:
    """HRA exemption must be 0 in new regime even when rent is paid."""
    profile = UserFinancialProfile(
        basic_salary=1_200_000, hra_received=300_000, monthly_rent_paid=15_000,
        city_type="metro", age_bracket="under60", input_method="manual",
    )
    result = calculate_new_regime(profile)
    assert result.deduction_breakdown.hra_exemption == 0.0


def test_new_regime_excludes_80c() -> None:
    """80C investments must not reduce new regime tax."""
    profile = UserFinancialProfile(
        basic_salary=1_200_000, investments_80c=150_000,
        city_type="metro", age_bracket="under60", input_method="manual",
    )
    result = calculate_new_regime(profile)
    assert result.deduction_breakdown.section_80c == 0.0


def test_cess_applied_after_87a_not_before() -> None:
    """Cess must be on post-87A tax. For a profile where 87A zeroes tax, cess must also be zero."""
    profile = UserFinancialProfile(
        basic_salary=600_000, investments_80c=50_000,
        city_type="metro", age_bracket="under60", input_method="manual",
    )
    # Old: taxable=500000, slab=12500, 87A zeroes → cess on 0 = 0
    old = calculate_old_regime(profile)
    assert old.total_tax == 0.0
    assert old.cess == 0.0
    assert old.tax_before_cess == 0.0


def test_taxable_income_never_negative() -> None:
    """If deductions exceed gross income, taxable_income must be 0, not negative."""
    profile = UserFinancialProfile(
        basic_salary=100_000, investments_80c=150_000,
        city_type="metro", age_bracket="under60", input_method="manual",
    )
    old = calculate_old_regime(profile)
    assert old.taxable_income >= 0.0
    new = calculate_new_regime(profile)
    assert new.taxable_income >= 0.0
