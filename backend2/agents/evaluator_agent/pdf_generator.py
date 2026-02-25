"""
pdf_generator.py — TaxMantri PDF report generator.

Builds a fully formatted PDF tax summary report using reportlab PLATYPUS.
Output is a BytesIO buffer (no temp file on disk).

Entry point:
    generate_tax_report(profile, result) -> BytesIO

CRITICAL: buffer.seek(0) is called after doc.build(story) — mandatory because
reportlab leaves the buffer position at the end after writing. Skipping seek(0)
produces a 0-byte PDF response.

PDF sections in CONTEXT.md order:
  1. Header (TaxMantri, AY2025-26, date, input method)
  2. Rationale paragraph
  3. Savings callout box (green highlighted)
  4. Regime comparison table (old vs new, recommended highlighted)
  5. Deduction breakdown table
  6. Optimization suggestions
  7. ITR-1 field mapping table (recommended regime section first)
  8. Disclaimer footer (8pt)

Color palette:
  - #D5F5E3  GREEN_LIGHT  Recommended regime column/header, savings callout, ITR-1 section header
  - #F2F2F2  GREY_LIGHT   Non-recommended column/header
  - No red anywhere — positive framing only. Prints clearly in greyscale.
"""
from __future__ import annotations

import datetime
import logging
from io import BytesIO

from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from backend.agents.evaluator_agent.itr1_mapper import build_itr1_mapping
from backend.agents.evaluator_agent.schemas import TaxResult
from backend.agents.input_agent.schemas import UserFinancialProfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Colour constants
# ---------------------------------------------------------------------------

GREEN_LIGHT = HexColor("#D5F5E3")   # Recommended regime highlight
GREY_LIGHT  = HexColor("#F2F2F2")   # Non-recommended headers / alternating rows

# ---------------------------------------------------------------------------
# Private section builders
# ---------------------------------------------------------------------------

def _build_comparison_table(result: TaxResult) -> Table:
    """
    Build the regime comparison table with 3 columns: label | Old | New.

    Recommended regime column header gets GREEN_LIGHT background + bold font.
    Non-recommended column header gets GREY_LIGHT. Row 0 contains only the
    \"RECOMMENDED ✓\" text in the recommended column (other cells empty).
    """
    rec = result.recommended_regime       # "old" or "new"
    rec_col = 1 if rec == "old" else 2    # col 0 = label, 1 = old, 2 = new

    label_row = ["", "", ""]
    label_row[rec_col] = "RECOMMENDED ✓"

    old = result.old_regime
    new = result.new_regime

    data = [
        label_row,
        ["", "Old Regime", "New Regime"],
        ["Gross Income",
         f"₹{old.gross_income:,.0f}",
         f"₹{new.gross_income:,.0f}"],
        ["Total Deductions",
         f"₹{old.total_deductions:,.0f}",
         f"₹{new.total_deductions:,.0f}"],
        ["Taxable Income",
         f"₹{old.taxable_income:,.0f}",
         f"₹{new.taxable_income:,.0f}"],
        ["Tax Before Cess",
         f"₹{old.tax_before_cess:,.0f}",
         f"₹{new.tax_before_cess:,.0f}"],
        ["Cess (4%)",
         f"₹{old.cess:,.0f}",
         f"₹{new.cess:,.0f}"],
        ["Total Tax Payable",
         f"₹{old.total_tax:,.0f}",
         f"₹{new.total_tax:,.0f}"],
    ]

    other_col = 3 - rec_col  # the non-recommended data column

    style_cmds = [
        # Recommended column: first two rows get green + bold
        ("BACKGROUND", (rec_col, 0), (rec_col, 1), GREEN_LIGHT),
        ("FONTNAME", (rec_col, 0), (rec_col, 1), "Helvetica-Bold"),
        # Non-recommended column header: grey
        ("BACKGROUND", (other_col, 1), (other_col, 1), GREY_LIGHT),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.5, black),
        # Number columns right-aligned, label column left-aligned
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        # Padding
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (0, -1), 6),
        # Bold total row
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]

    t = Table(data, colWidths=[80 * mm, 45 * mm, 45 * mm])
    t.setStyle(TableStyle(style_cmds))
    return t


def _build_deduction_table(result: TaxResult) -> Table:
    """
    Build the deduction breakdown table showing all deduction types for both regimes.

    Old-regime-only fields show \"—\" in the new regime column.
    80CCD(2) employer NPS is available in both regimes.
    """
    old_bd = result.old_regime.deduction_breakdown
    new_bd = result.new_regime.deduction_breakdown

    def fmt(v: float) -> str:
        return f"₹{v:,.0f}" if v and v > 0 else "—"

    header = ["Deduction", "Old Regime", "New Regime"]
    rows = [
        ["Standard Deduction",        fmt(old_bd.standard_deduction),   fmt(new_bd.standard_deduction)],
        ["HRA Exemption u/s 10(13A)", fmt(old_bd.hra_exemption),        "—"],
        ["Professional Tax u/s 16",   fmt(old_bd.professional_tax),     "—"],
        ["80C (Investments)",          fmt(old_bd.section_80c),          "—"],
        ["80D (Health Insurance)",     fmt(old_bd.section_80d),          "—"],
        ["80CCD(1B) (Employee NPS)",   fmt(old_bd.section_80ccd1b),      "—"],
        ["80CCD(2) (Employer NPS)",    fmt(old_bd.section_80ccd2),       fmt(new_bd.section_80ccd2)],
        ["Section 24(b) (Home Loan)",  fmt(old_bd.section_24b),          "—"],
        ["80TTA/80TTB (Savings Int.)", fmt(old_bd.section_80tta_ttb),    "—"],
        ["Total Deductions",
         f"₹{result.old_regime.total_deductions:,.0f}",
         f"₹{result.new_regime.total_deductions:,.0f}"],
    ]

    data = [header] + rows

    style_cmds = [
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), GREY_LIGHT),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        # Total row bold
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.5, black),
        # Alignment
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        # Padding
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (0, -1), 6),
    ]

    t = Table(data, colWidths=[90 * mm, 40 * mm, 40 * mm])
    t.setStyle(TableStyle(style_cmds))
    return t


def _build_itr1_section(
    profile: UserFinancialProfile,
    result: TaxResult,
    styles: dict,
) -> list:
    """
    Build the ITR-1 field mapping section as a list of PLATYPUS flowables.

    Recommended regime section appears first. Each section has a header row
    with GREEN_LIGHT (recommended) or GREY_LIGHT (other). Note column shows
    Rule 2A breakdown for HRA; empty string for all other entries.
    """
    mapping = build_itr1_mapping(profile, result)

    old_entries = [e for e in mapping if e.regime == "old"]
    new_entries = [e for e in mapping if e.regime == "new"]

    rec = result.recommended_regime

    # Put recommended regime section first
    if rec == "old":
        sections = [("OLD REGIME", old_entries, GREEN_LIGHT), ("NEW REGIME", new_entries, GREY_LIGHT)]
    else:
        sections = [("NEW REGIME", new_entries, GREEN_LIGHT), ("OLD REGIME", old_entries, GREY_LIGHT)]

    flowables = []

    for section_label, entries, header_color in sections:
        header_row = ["ITR-1 Field", "Schedule", "Value", "Note"]
        data_rows = [
            [
                entry.itr1_field,
                entry.schedule,
                f"₹{entry.value:,.0f}",
                entry.note or "",
            ]
            for entry in entries
        ]
        table_data = [header_row] + data_rows

        col_widths = [80 * mm, 35 * mm, 30 * mm, 25 * mm]
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), header_color),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, black),
            ("ALIGN", (2, 0), (2, -1), "RIGHT"),
            ("ALIGN", (0, 0), (1, -1), "LEFT"),
            ("FONTSIZE", (3, 1), (3, -1), 7),  # note column smaller
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (0, -1), 4),
        ]

        section_heading = Paragraph(section_label, styles["Heading3"])
        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle(style_cmds))

        flowables.append(KeepTogether([section_heading, Spacer(1, 2 * mm), t]))
        flowables.append(Spacer(1, 4 * mm))

    return flowables


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_tax_report(
    profile: UserFinancialProfile,
    result: TaxResult,
) -> BytesIO:
    """
    Generate a complete formatted TaxMantri PDF report.

    Builds an A4 PLATYPUS document with 8 sections in CONTEXT.md order:
    header → rationale → savings callout → comparison table →
    deduction table → suggestions → ITR-1 mapping → disclaimer.

    CRITICAL: buffer.seek(0) is called after doc.build(story).
    reportlab leaves the buffer at end-of-write; seek(0) resets it
    so StreamingResponse can read from the start.

    Args:
        profile: UserFinancialProfile (needed for HRA note calculation).
        result: TaxResult from compare_regimes().

    Returns:
        BytesIO buffer at position 0, ready for StreamingResponse.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    story = []

    # -----------------------------------------------------------------------
    # 1. Header block
    # -----------------------------------------------------------------------

    title_style = ParagraphStyle(
        "report_title",
        parent=styles["Heading1"],
        fontSize=18,
        fontName="Helvetica-Bold",
    )
    story.append(Paragraph("TaxMantri — Tax Report", title_style))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("Assessment Year: AY2025-26", styles["Normal"]))
    story.append(
        Paragraph(
            f"Report generated: {datetime.date.today().strftime('%d %B %Y')}",
            styles["Normal"],
        )
    )
    input_method = (
        profile.input_method.value
        if hasattr(profile.input_method, "value")
        else str(profile.input_method)
    )
    story.append(
        Paragraph(f"Input method: {input_method.capitalize()}", styles["Normal"])
    )
    story.append(Spacer(1, 6 * mm))

    # -----------------------------------------------------------------------
    # 2. Rationale paragraph
    # -----------------------------------------------------------------------

    story.append(Paragraph(result.rationale, styles["Normal"]))
    story.append(Spacer(1, 4 * mm))

    # -----------------------------------------------------------------------
    # 3. Savings callout box — single-cell Table with GREEN_LIGHT background
    # -----------------------------------------------------------------------

    rec = result.recommended_regime       # "old" or "new"
    rec_label = "Old" if rec == "old" else "New"
    savings_text = (
        f"{rec_label} Regime saves you ₹{result.savings_amount:,.0f}"
    )

    callout_style = ParagraphStyle(
        "callout",
        parent=styles["Normal"],
        fontSize=14,
        fontName="Helvetica-Bold",
    )
    callout_table = Table(
        [[Paragraph(savings_text, callout_style)]],
        colWidths=[170 * mm],
    )
    callout_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), GREEN_LIGHT),
            ("BOX", (0, 0), (-1, -1), 1, black),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ])
    )
    story.append(callout_table)
    story.append(Spacer(1, 8 * mm))

    # -----------------------------------------------------------------------
    # 4. Regime comparison table
    # -----------------------------------------------------------------------

    comparison_heading = Paragraph("Regime Comparison", styles["Heading2"])
    comparison_table = _build_comparison_table(result)
    story.append(KeepTogether([comparison_heading, Spacer(1, 2 * mm), comparison_table]))
    story.append(Spacer(1, 6 * mm))

    # -----------------------------------------------------------------------
    # 5. Deduction breakdown table
    # -----------------------------------------------------------------------

    deduction_heading = Paragraph("Deduction Breakdown", styles["Heading2"])
    deduction_table = _build_deduction_table(result)
    story.append(KeepTogether([deduction_heading, Spacer(1, 2 * mm), deduction_table]))
    story.append(Spacer(1, 6 * mm))

    # -----------------------------------------------------------------------
    # 6. Optimization suggestions (only if non-empty)
    # -----------------------------------------------------------------------

    has_old_suggestions = bool(result.old_regime_suggestions)
    has_new_suggestions = bool(result.new_regime_suggestions)

    if has_old_suggestions or has_new_suggestions:
        story.append(Paragraph("Optimization Suggestions", styles["Heading2"]))
        story.append(Spacer(1, 2 * mm))

        if has_old_suggestions:
            story.append(Paragraph("Old Regime", styles["Heading3"]))
            for suggestion in result.old_regime_suggestions:
                story.append(Paragraph(f"• {suggestion}", styles["Normal"]))

        if has_new_suggestions:
            story.append(Paragraph("New Regime", styles["Heading3"]))
            for suggestion in result.new_regime_suggestions:
                story.append(Paragraph(f"• {suggestion}", styles["Normal"]))

        story.append(Spacer(1, 6 * mm))

    # -----------------------------------------------------------------------
    # 7. ITR-1 field mapping tables (recommended regime section first)
    # -----------------------------------------------------------------------

    story.append(Paragraph("ITR-1 Field Mapping", styles["Heading2"]))
    story.append(Spacer(1, 2 * mm))
    story.extend(_build_itr1_section(profile, result, styles))

    # -----------------------------------------------------------------------
    # 8. Disclaimer (8pt, end of last page)
    # -----------------------------------------------------------------------

    disclaimer_style = ParagraphStyle(
        "disclaimer",
        parent=styles["Normal"],
        fontSize=8,
        textColor=black,
    )
    story.append(Spacer(1, 10 * mm))
    story.append(
        Paragraph(
            "This report is generated by TaxMantri for reference purposes only. "
            "Please verify all figures with a Chartered Accountant before filing your ITR.",
            disclaimer_style,
        )
    )

    # -----------------------------------------------------------------------
    # Build document — CRITICAL: buffer.seek(0) after build
    # -----------------------------------------------------------------------

    doc.build(story)
    buffer.seek(0)  # MANDATORY: reset position before StreamingResponse reads

    logger.info(
        "PDF report generated profile_id=%s recommended=%s",
        result.profile_id,
        result.recommended_regime,
    )

    return buffer
