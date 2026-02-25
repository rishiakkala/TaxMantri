"""
InputAgent business-rule validator — AY 2025-26

Validates UserFinancialProfile against business rules AFTER Pydantic structural
validation has already passed. Collects all violations in a single pass and
raises ValueError with a JSON-encoded list of {field, issue} dicts so the
Phase 1 exception handler (or route) can build the standard error envelope.

Rules enforced (INPUT-02):
  1. investments_80c        <= 1,50,000
  2. health_insurance_self  age-dependent cap (under60: 25,000 / 60_79|80plus: 50,000)
  3. health_insurance_parents cap (parent_senior_citizen=False: 25,000 / True: 50,000)
  4. home_loan_interest      <= 2,00,000
  5. employee_nps_80ccd1b   <= 50,000
  6. employer_nps_80ccd2    <= 10% of basic_salary
  7. other_income           <= 50,00,000 (ITR-1 eligibility — above requires ITR-2)

Note: HRA <= basic_salary is already enforced by @model_validator in schemas.py.
Do NOT re-enforce here to avoid duplicating error messages.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from backend.agents.input_agent.schemas import AgeBracket, UserFinancialProfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cap constants — redeclared here (not imported from tax_engine) to keep
# validator.py self-contained and avoid circular import chains.
# ---------------------------------------------------------------------------
_CAP_80C                   = 150_000
_CAP_80D_SELF_UNDER60      = 25_000
_CAP_80D_SELF_SENIOR       = 50_000          # age_bracket in (60_79, 80plus)
_CAP_80D_PARENTS_NON_SENIOR = 25_000         # parent_senior_citizen = False
_CAP_80D_PARENTS_SENIOR    = 50_000          # parent_senior_citizen = True
_CAP_24B                   = 200_000
_CAP_80CCD1B               = 50_000
_CAP_80CCD2_PCT            = 0.10            # 10% of basic_salary
_ITR1_OTHER_INCOME_MAX     = 5_000_000       # ITR-1 cap: other_income > 50L → ITR-2


def validate_business_rules(profile: UserFinancialProfile) -> None:
    """
    Validate profile against all INPUT-02 business rules.

    Collects every violation before raising, so callers receive all errors in
    one response rather than discovering them one at a time.

    Args:
        profile: A structurally-valid UserFinancialProfile (Pydantic already ran).

    Raises:
        ValueError: If any business rule is violated. The message is a JSON string
            containing a list of {"field": str, "issue": str} dicts, parsed by the
            route into the standard error envelope.
    """
    violations: list[dict[str, Any]] = []

    # ---- 1. Section 80C cap ------------------------------------------------
    investments_80c = profile.investments_80c or 0.0
    if investments_80c > _CAP_80C:
        violations.append({
            "field": "investments_80c",
            "issue": (
                f"Value ₹{investments_80c:,.0f} exceeds the Section 80C maximum of "
                f"₹{_CAP_80C:,.0f}. Only ₹1,50,000 is deductible."
            ),
        })

    # ---- 2. Section 80D — self/family, age-dependent -----------------------
    health_self = profile.health_insurance_self or 0.0
    self_cap = (
        _CAP_80D_SELF_SENIOR
        if profile.age_bracket in (AgeBracket.sixty_79, AgeBracket.eighty_plus)
        else _CAP_80D_SELF_UNDER60
    )
    if health_self > self_cap:
        violations.append({
            "field": "health_insurance_self",
            "issue": (
                f"Value ₹{health_self:,.0f} exceeds the Section 80D self/family cap of "
                f"₹{self_cap:,.0f} for age bracket '{profile.age_bracket.value}'."
            ),
        })

    # ---- 3. Section 80D — parents, senior-citizen flag ---------------------
    health_parents = profile.health_insurance_parents or 0.0
    parent_cap = (
        _CAP_80D_PARENTS_SENIOR
        if profile.parent_senior_citizen
        else _CAP_80D_PARENTS_NON_SENIOR
    )
    if health_parents > parent_cap:
        violations.append({
            "field": "health_insurance_parents",
            "issue": (
                f"Value ₹{health_parents:,.0f} exceeds the Section 80D parents cap of "
                f"₹{parent_cap:,.0f} "
                f"({'senior citizen' if profile.parent_senior_citizen else 'non-senior'} parents)."
            ),
        })

    # ---- 4. Section 24(b) home loan interest cap ---------------------------
    home_loan_interest = profile.home_loan_interest or 0.0
    if home_loan_interest > _CAP_24B:
        violations.append({
            "field": "home_loan_interest",
            "issue": (
                f"Value ₹{home_loan_interest:,.0f} exceeds the Section 24(b) cap of "
                f"₹{_CAP_24B:,.0f}. Only ₹2,00,000 is deductible for a self-occupied property."
            ),
        })

    # ---- 5. Section 80CCD(1B) employee NPS cap -----------------------------
    employee_nps = profile.employee_nps_80ccd1b or 0.0
    if employee_nps > _CAP_80CCD1B:
        violations.append({
            "field": "employee_nps_80ccd1b",
            "issue": (
                f"Value ₹{employee_nps:,.0f} exceeds the Section 80CCD(1B) cap of "
                f"₹{_CAP_80CCD1B:,.0f}."
            ),
        })

    # ---- 6. Section 80CCD(2) employer NPS cap — 10% of basic_salary --------
    employer_nps = profile.employer_nps_80ccd2 or 0.0
    employer_nps_cap = _CAP_80CCD2_PCT * profile.basic_salary
    if employer_nps > employer_nps_cap:
        violations.append({
            "field": "employer_nps_80ccd2",
            "issue": (
                f"Value ₹{employer_nps:,.0f} exceeds the Section 80CCD(2) cap of "
                f"10% of basic salary = ₹{employer_nps_cap:,.0f}."
            ),
        })

    # ---- 7. ITR-1 eligibility — other_income > 50L requires ITR-2 ----------
    other_income = profile.other_income or 0.0
    if other_income > _ITR1_OTHER_INCOME_MAX:
        violations.append({
            "field": "other_income",
            "issue": (
                f"Other income ₹{other_income:,.0f} exceeds ₹50,00,000. "
                "Taxpayers with other income above ₹50 lakh must file ITR-2, not ITR-1. "
                "TaxMantri only supports ITR-1 (Sahaj) filers."
            ),
        })

    if violations:
        # Log only profile_id and count — no salary values, PAN, or name (CLAUDE.md)
        logger.info(
            "Business-rule validation failed: %d violation(s) profile_id=%s",
            len(violations),
            profile.profile_id,
        )
        raise ValueError(json.dumps(violations))


def validate_hra_consistency(
    profile: UserFinancialProfile,
    hra_declared: float | None,
) -> list[str]:
    """
    Compare the HRA exemption computed via Rule 2A against the employer-declared
    HRA exemption from Form 16 line 2(e).

    Returns a list of warning strings (empty if consistent or if hra_declared is
    None / no HRA received). This is a soft check — warnings do not block the
    user from proceeding.

    Rule 2A exemption = minimum of:
      (a) HRA received from employer
      (b) Actual rent paid annually − 10% of basic salary
      (c) 50% of basic salary (metro) or 40% of basic salary (non-metro)
    """
    from backend.agents.input_agent.schemas import CityType

    warnings: list[str] = []

    if hra_declared is None:
        return warnings

    hra_received = profile.hra_received or 0.0
    if hra_received == 0:
        return warnings

    basic = profile.basic_salary
    annual_rent = (profile.monthly_rent_paid or 0.0) * 12
    metro_pct = 0.50 if profile.city_type == CityType.metro else 0.40

    rule_2a_exemption = min(
        hra_received,
        max(0.0, annual_rent - 0.10 * basic),
        metro_pct * basic,
    )

    if hra_declared > 0:
        relative_diff = abs(rule_2a_exemption - hra_declared) / hra_declared
    else:
        relative_diff = 1.0 if rule_2a_exemption > 0 else 0.0

    if relative_diff > 0.10:
        warnings.append(
            f"HRA exemption mismatch: Rule 2A computes ₹{rule_2a_exemption:,.0f} but "
            f"Form 16 declares ₹{hra_declared:,.0f}. "
            "Please verify your basic salary, monthly rent, and city type."
        )
        logger.info(
            "HRA consistency warning profile_id=%s rule2a=%.0f declared=%.0f",
            profile.profile_id,
            rule_2a_exemption,
            hra_declared,
        )

    return warnings
