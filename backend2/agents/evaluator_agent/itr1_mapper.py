"""
itr1_mapper.py — Deterministic ITR-1 Sahaj field mapping engine.

Pure function module — no I/O, no database calls, no side effects.
Exports:
  - build_itr1_mapping(profile, result) -> list[ITR1FieldMap]  [public]
  - _build_hra_note(profile, hra_exemption) -> str              [exported for PDF generator]

Called by:
  - GET /api/itr1-mapping/{profile_id} route (JSON response)
  - generate_tax_report() in pdf_generator.py (ITR-1 section of PDF)

Both consumers import build_itr1_mapping from here — zero duplication of mapping logic.

ITR-1 Schedules covered:
  - Schedule S        — Salary income details (both regimes)
  - Schedule VI-A     — Chapter VI-A deductions (old regime only)
  - Part B-TI         — Computation of Total Income (both regimes)
  - Part B-TTI        — Tax computation (both regimes)

Zero-value fields are omitted from the output list.
HRA entry (old regime, if non-zero) includes a Rule 2A note string.
"""
from __future__ import annotations

import logging

from backend.agents.evaluator_agent.schemas import ITR1FieldMap, TaxResult
from backend.agents.input_agent.schemas import UserFinancialProfile

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _add_if_nonzero(
    entries: list[ITR1FieldMap],
    itr1_field: str,
    schedule: str,
    value: float | None,
    source_field: str,
    regime: str,
) -> None:
    """
    Append an ITR1FieldMap entry to entries only if value is non-zero and non-None.

    Args:
        entries: Accumulator list. Modified in-place.
        itr1_field: Human-readable ITR-1 schedule field label.
        schedule: Schedule group (e.g. \"Schedule S\", \"Part B-TI\").
        value: The computed financial value. Zero or None → skip.
        source_field: Dotted path describing where the value came from
            (e.g. \"old_regime.deduction_breakdown.section_80c\").
        regime: \"old\" or \"new\".
    """
    if value and value != 0:
        entries.append(
            ITR1FieldMap(
                itr1_field=itr1_field,
                schedule=schedule,
                value=value,
                source_field=source_field,
                regime=regime,
                note=None,
            )
        )


def _build_hra_note(profile: UserFinancialProfile, hra_exemption: float) -> str:
    """
    Build the Rule 2A min-of-3 breakdown string for CA verification.

    Rule 2A defines HRA exemption as the minimum of three components:
      c1: Actual HRA received from employer
      c2: metro_pct × basic salary (50% for metro cities, 40% for non-metro)
      c3: Rent paid × 12 − 10% × basic salary (excess of rent over 10% basic)

    Args:
        profile: UserFinancialProfile with city_type, hra_received,
                 monthly_rent_paid, basic_salary.
        hra_exemption: The final HRA exemption value applied by the tax engine.

    Returns:
        String like \"Rule 2A min(₹3,00,000, ₹6,00,000, ₹60,000) = ₹60,000\"
    """
    metro_pct = 0.50 if profile.city_type.value == "metro" else 0.40
    annual_rent = (profile.monthly_rent_paid or 0) * 12
    c1 = profile.hra_received or 0
    c2 = metro_pct * profile.basic_salary
    c3 = max(0.0, annual_rent - 0.10 * profile.basic_salary)

    return (
        f"Rule 2A min(₹{c1:,.0f}, ₹{c2:,.0f}, ₹{c3:,.0f}) = ₹{hra_exemption:,.0f}"
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_itr1_mapping(
    profile: UserFinancialProfile,
    result: TaxResult,
) -> list[ITR1FieldMap]:
    """
    Deterministic mapping from TaxResult + UserFinancialProfile to ITR-1 field list.

    Iterates both regimes in order: old first, then new. For each regime, emits
    entries for all four ITR-1 schedule groups. Zero-value fields are omitted.
    HRA exemption (old regime only) includes a Rule 2A note string.

    Args:
        profile: The UserFinancialProfile used for HRA note calculation.
        result: The TaxResult from compare_regimes().

    Returns:
        Ordered list of ITR1FieldMap entries (old regime entries first, then new).
    """
    entries: list[ITR1FieldMap] = []

    for regime, regime_result in [("old", result.old_regime), ("new", result.new_regime)]:
        bd = regime_result.deduction_breakdown
        pfx = f"{regime}_regime"

        # -----------------------------------------------------------------------
        # Schedule S — Salary income details
        # -----------------------------------------------------------------------

        _add_if_nonzero(
            entries,
            "Schedule S – Gross Salary",
            "Schedule S",
            regime_result.gross_income,
            f"{pfx}.gross_income",
            regime,
        )

        _add_if_nonzero(
            entries,
            "Schedule S – Standard Deduction u/s 16(ia)",
            "Schedule S",
            bd.standard_deduction,
            f"{pfx}.deduction_breakdown.standard_deduction",
            regime,
        )

        # HRA exemption — old regime only (new regime provides no HRA exemption)
        if regime == "old" and bd.hra_exemption > 0:
            note = _build_hra_note(profile, bd.hra_exemption)
            entries.append(
                ITR1FieldMap(
                    itr1_field="Schedule S – HRA Exemption u/s 10(13A)",
                    schedule="Schedule S",
                    value=bd.hra_exemption,
                    source_field="old_regime.deduction_breakdown.hra_exemption",
                    regime="old",
                    note=note,
                )
            )

        # Professional tax — old regime only
        if regime == "old":
            _add_if_nonzero(
                entries,
                "Schedule S – Deduction u/s 16(iii) – Professional Tax",
                "Schedule S",
                bd.professional_tax,
                "old_regime.deduction_breakdown.professional_tax",
                "old",
            )

        # Net salary (taxable income after all salary deductions)
        _add_if_nonzero(
            entries,
            "Schedule S – Net Salary (Income chargeable under Salaries)",
            "Schedule S",
            regime_result.taxable_income,
            f"{pfx}.taxable_income",
            regime,
        )

        # -----------------------------------------------------------------------
        # Schedule VI-A — Chapter VI-A deductions (old regime only)
        # 80CCD(2) employer NPS appears in both regimes
        # -----------------------------------------------------------------------

        if regime == "old":
            _add_if_nonzero(
                entries,
                "Schedule VI-A – 80C (Investments)",
                "Schedule VI-A",
                bd.section_80c,
                "old_regime.deduction_breakdown.section_80c",
                "old",
            )

            _add_if_nonzero(
                entries,
                "Schedule VI-A – 80D (Health Insurance)",
                "Schedule VI-A",
                bd.section_80d,
                "old_regime.deduction_breakdown.section_80d",
                "old",
            )

            _add_if_nonzero(
                entries,
                "Schedule VI-A – 80CCD(1B) (Employee NPS)",
                "Schedule VI-A",
                bd.section_80ccd1b,
                "old_regime.deduction_breakdown.section_80ccd1b",
                "old",
            )

            _add_if_nonzero(
                entries,
                "Schedule VI-A – Section 24(b) (Home Loan Interest)",
                "Schedule VI-A",
                bd.section_24b,
                "old_regime.deduction_breakdown.section_24b",
                "old",
            )

            _add_if_nonzero(
                entries,
                "Schedule VI-A – 80TTA/80TTB (Savings Interest)",
                "Schedule VI-A",
                bd.section_80tta_ttb,
                "old_regime.deduction_breakdown.section_80tta_ttb",
                "old",
            )

        # 80CCD(2) employer NPS — available in BOTH regimes
        _add_if_nonzero(
            entries,
            "Schedule VI-A – 80CCD(2) (Employer NPS)",
            "Schedule VI-A",
            bd.section_80ccd2,
            f"{pfx}.deduction_breakdown.section_80ccd2",
            regime,
        )

        # -----------------------------------------------------------------------
        # Part B-TI — Computation of Total Income
        # -----------------------------------------------------------------------

        _add_if_nonzero(
            entries,
            "Part B-TI – Gross Total Income",
            "Part B-TI",
            regime_result.gross_income,
            f"{pfx}.gross_income",
            regime,
        )

        _add_if_nonzero(
            entries,
            "Part B-TI – Deductions under Chapter VI-A",
            "Part B-TI",
            regime_result.total_deductions,
            f"{pfx}.total_deductions",
            regime,
        )

        _add_if_nonzero(
            entries,
            "Part B-TI – Total Income",
            "Part B-TI",
            regime_result.taxable_income,
            f"{pfx}.taxable_income",
            regime,
        )

        # -----------------------------------------------------------------------
        # Part B-TTI — Tax Computation
        # -----------------------------------------------------------------------

        _add_if_nonzero(
            entries,
            "Part B-TTI – Tax on Total Income",
            "Part B-TTI",
            regime_result.tax_before_cess,
            f"{pfx}.tax_before_cess",
            regime,
        )

        _add_if_nonzero(
            entries,
            "Part B-TTI – Health and Education Cess @ 4%",
            "Part B-TTI",
            regime_result.cess,
            f"{pfx}.cess",
            regime,
        )

        _add_if_nonzero(
            entries,
            "Part B-TTI – Total Tax Payable",
            "Part B-TTI",
            regime_result.total_tax,
            f"{pfx}.total_tax",
            regime,
        )

    logger.debug(
        "build_itr1_mapping completed: %d entries (old=%d, new=%d)",
        len(entries),
        sum(1 for e in entries if e.regime == "old"),
        sum(1 for e in entries if e.regime == "new"),
    )

    return entries
