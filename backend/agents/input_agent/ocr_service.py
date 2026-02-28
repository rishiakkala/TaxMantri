"""
ocr_service.py — Form 16 OCR extraction engine.

Pure function module — no FastAPI dependencies.
Entry point: extract_form16(file_path: str) -> OCRResult

All OCR logic lives here. The upload route only does I/O
(file save, Redis store, temp cleanup). This separation enables
unit testing without an HTTP context.

TODO: validate FIELD_PATTERNS regex against real Form 16 PDFs from
      Greytip, Keka, Darwinbox before demo. Patterns cover the most
      common HR system label variants but may need tuning.

NOTE: pytesseract / pdf2image / PIL are imported LAZILY inside
      extract_form16() to avoid startup failure if the Tesseract
      binary is missing from the deployment environment.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Confidence thresholds
# ---------------------------------------------------------------------------

HIGH_CONFIDENCE = 0.90    # Full regex match on known label + numeric pattern → green
MEDIUM_CONFIDENCE = 0.70  # Fuzzy/fallback label match → yellow  (reserved for future tuning)
NO_MATCH_CONFIDENCE = 0.0 # No regex match at all → red, value = None

# green > 0.85, yellow 0.60–0.85, red < 0.60
_THRESHOLD_GREEN = 0.85
_THRESHOLD_YELLOW = 0.60

# ---------------------------------------------------------------------------
# Tesseract config
# ---------------------------------------------------------------------------

OCR_CONFIG = "--oem 3 --psm 6"

# ---------------------------------------------------------------------------
# Field groupings
# ---------------------------------------------------------------------------

# TODO: validate regex patterns against real Form 16 PDFs from Greytip, Keka, Darwinbox before demo

# Profile-mappable fields — directly extractable from Form 16 and stored in
# extracted_fields AND profile_fields (if non-None).
# These map 1:1 to UserFinancialProfile fields.
PROFILE_FIELDS = [
    "basic_salary",          # Form 16 Part B line 1(d) — gross salary per sec 17(1)
    "professional_tax",       # Form 16 Part B line 4(c)
    "investments_80c",        # Form 16 Part B line 10(d) deductible amount
    "health_insurance_self",  # Form 16 Part B line 10(g)
    "employee_nps_80ccd1b",   # Form 16 Part B line 10(e)
    "employer_nps_80ccd2",    # Form 16 Part B line 10(f)
    "home_loan_interest",     # Form 16 Part B line 7(a) — abs() applied on negative
    "savings_interest_80tta", # Form 16 Part B line 10(l)
]

# Reference-only fields — extracted from Form 16 and shown to the user for
# cross-validation, but NOT stored in UserFinancialProfile.
#
# gross_salary_17_1  : Form 16 Part B line 1(d) — sum of all salary components.
#                      Cannot be split into basic/HRA/LTA without the payslip.
# hra_exempt_10_13a  : Form 16 Part B line 2(e) — employer-declared HRA exemption.
#                      Used to cross-validate the Rule 2A amount after user fills
#                      basic_salary + hra_received + monthly_rent_paid.
# lta_exempt_10_5    : Form 16 Part B line 2(a) — employer-declared LTA exemption.
# gross_total_income : Form 16 Part B line 9 — display/reconciliation only.
# tds_deducted       : Form 16 Part A total — display/reconciliation only.
REFERENCE_FIELDS = [
    "gross_salary_17_1",
    "hra_exempt_10_13a",
    "lta_exempt_10_5",
    "gross_total_income",
    "tds_deducted",
]

# Non-extractable fields — Form 16 does NOT contain these values at all.
# The confirm route requires the user to supply all of them via edited_fields.
# Returned in OCRResult.missing_profile_fields so the frontend can render
# the correct input fields in the confirmation step.
NON_EXTRACTABLE_FIELDS = [
    "hra_received",           # Only exempt portion shown (line 2e), not amount received
    "lta",                    # Only exempt portion shown (line 2a), not amount received
    "special_allowance",      # Collapsed into gross salary line 1(d)
    "other_allowances",       # Collapsed into gross salary line 1(d)
    "monthly_rent_paid",      # Personal information — not in any tax document
    "city_type",              # Personal information — not in any tax document
    "age_bracket",            # Personal information — not in any tax document
    "parent_senior_citizen",  # Personal information — not in any tax document
]

# ---------------------------------------------------------------------------
# Two-column deduction fields — require LAST-number extraction
# ---------------------------------------------------------------------------
# Form 16 Chapter VI-A table has two columns per row:
#   | Description          | Gross Amount | Deductible Amount |
# e.g. row (d): "Total deduction u/s 80C  Rs. NIL  Rs. 1,30,000"
# e.g. row (e): "80CCD (1B)               Rs. 1,30,000  Rs. 50,000"
#
# Standard .search(text).group(1) picks the FIRST number (gross amount).
# For fields in this set, _extract_all_fields scans the matched line and
# takes the LAST number instead (deductible amount = the one we want).
_TAIL_NUMBER_FIELDS: frozenset = frozenset({
    "investments_80c",        # row (d): total deductible u/s 80C+80CCC+80CCD(1)
    "employee_nps_80ccd1b",   # row (e): deductible u/s 80CCD(1B)
    "employer_nps_80ccd2",    # row (f2): deductible u/s 80CCD(2)
    "health_insurance_self",  # row (f): deductible u/s 80D
    "savings_interest_80tta", # row with 80TTA/80TTB
})


# ---------------------------------------------------------------------------
# Regex patterns — all fields
# ---------------------------------------------------------------------------

FIELD_PATTERNS: dict[str, re.Pattern] = {
    # ------------------------------------------------------------------ #
    # Profile-mappable — direct 1:1 match to UserFinancialProfile fields  #
    # ------------------------------------------------------------------ #

    # Form 16 Part B line 1(d): "Salary as per provisions contained in sec. 17(1)"
    # User wants the gross salary value used directly as basic salary.
    # Pattern scans up to 150 chars (crosses newlines) since pdfplumber often
    # splits the label and Rs. amount onto separate lines.
    "basic_salary": re.compile(
        r"(?:"
        r"Salary\s+as\s+per\s+provisions\s+contained\s+in\s+sec(?:tion)?\.?\s*17\s*\(?1\)?"
        r"|Gross\s+Salary"
        r"|Total\s+(?:Gross\s+)?Earnings"
        r"|Total\s+Salary"
        r")[\s\S]{0,150}?Rs\.?\s*([\d,]+(?:\.\d+)?)",
        re.IGNORECASE,
    ),

    # Form 16 Part B line 4(c): "Tax on employment under section 16(iii)"
    # Also present as: "Professional Tax", "Prof. Tax", "Profession Tax"
    "professional_tax": re.compile(
        r"(?:"
        r"Tax\s+on\s+[Ee]mployment"
        r"|Professional\s+Tax"
        r"|Profession\s+Tax"
        r"|Prof\.?\s*Tax"
        r"|Entertainment\s+allowance\s+and\s+[Tt]ax\s+on\s+[Ee]mployment"
        r")[\s\S]{0,120}?Rs\.?\s*([\d,]+(?:\.\d+)?)",
        re.IGNORECASE,
    ),
    # Form 16 Part B line 10(d): "Total deduction under section 80C, 80CCC and 80CCD(1)"
    # Also: "Gross amount" or "Deductible amount" under 80C section heading
    "investments_80c": re.compile(
        r"(?:"
        r"Total\s+deduction\s+under\s+section\s+80C"
        r"|(?:Gross|Deductible)\s+amount[^\n]{0,30}80C"
        r"|80C[^\n]{0,30}(?:Gross|Deductible|Total)\s+amount"
        r"|Deduction\s+in\s+respect\s+of\s+life\s+insurance"
        r"|Section\s+80C"
        r"|80\s*C\b"
        r")[^\n]{0,80}?([\d,]+(?:\.\d+)?)",
        re.IGNORECASE,
    ),
    # Form 16 Part B line 10(g): "Deduction in respect of health insurance premia under section 80D"
    # Also: "Medical Insurance Premia u/s 80D", "Mediclaim", "80D"
    "health_insurance_self": re.compile(
        r"(?:"
        r"health\s+insurance\s+premi"
        r"|Medical\s+Insurance\s+Premi"
        r"|Mediclaim"
        r"|80\s*D\b"
        r"|Deduction[^\n]{0,30}80D"
        r")[^\n]{0,80}?([\d,]+(?:\.\d+)?)",
        re.IGNORECASE,
    ),
    # Form 16 Part B line 10(e): section 80CCD(1B) — employee NPS contribution
    "employee_nps_80ccd1b": re.compile(
        r"(?:"
        r"80\s*CCD\s*[\(\[]?\s*1B\s*[\)\]]?"
        r"|notified\s+pension\s+scheme"
        r"|NPS\s+Employee"
        r"|Employee[\s'\'s]{0,5}(?:NPS|contribution)[^\n]{0,30}80CCD"
        r"|Amount\s+deductible\s+under\s+section\s+80CCD\s*\(?1B\)?"
        r")[^\n]{0,80}?([\d,]+(?:\.\d+)?)",
        re.IGNORECASE,
    ),
    # Form 16 Part B line 10(f): employer NPS contribution u/s 80CCD(2)
    "employer_nps_80ccd2": re.compile(
        r"(?:"
        r"80\s*CCD\s*[\(\[]?\s*2\s*[\)\]]?"
        r"|contribution\s+by\s+Employer\s+to\s+pension"
        r"|Employer[\s'\'s]{0,5}contribution[^\n]{0,40}pension"
        r"|NPS\s+Employer"
        r"|Employer[\s'\'s]{0,5}NPS"
        r")[^\n]{0,80}?([\d,]+(?:\.\d+)?)",
        re.IGNORECASE,
    ),
    # Form 16 Part B line 7(a): "Income (or admissible loss) from house property"
    # Also: "Interest on Housing Loan", "Section 24(b)", "Loss from House Property"
    # Value may be negative (loss shown in brackets). Strip sign; caller takes abs().
    "home_loan_interest": re.compile(
        r"(?:"
        r"Income[^\n]{0,30}from\s+house\s+property"
        r"|Loss[^\n]{0,30}house\s+property"
        r"|Interest\s+on\s+(?:Housing|Home)\s+Loan"
        r"|Section\s+24\s*\(?b\)?"
        r"|24\s*\(?b\)?"
        r"|Home\s+Loan\s+Interest"
        r")[^\n]{0,80}?(-?[\d,]+(?:\.\d+)?)",
        re.IGNORECASE,
    ),
    # Form 16 Part B line 10(l): section 80TTA / 80TTB — savings account interest
    "savings_interest_80tta": re.compile(
        r"(?:"
        r"80TT[AB]\b"
        r"|interest\s+on\s+deposits\s+in\s+savings"
        r"|Savings\s+(?:Account\s+)?[Ii]nterest"
        r"|Deduction[^\n]{0,30}80TT"
        r")[^\n]{0,80}?([\d,]+(?:\.\d+)?)",
        re.IGNORECASE,
    ),

    # ------------------------------------------------------------------ #
    # Reference-only — Form 16 totals used for display / cross-validation #
    # NOT mapped to UserFinancialProfile fields                            #
    # ------------------------------------------------------------------ #

    # Form 16 Part B line 1(d): combined gross salary = basic + HRA + LTA + special allowance.
    # Matches "Salary as per provisions contained in section 17(1)" row total,
    # OR the "Total" label on the same line as the 17(1) amount.
    "gross_salary_17_1": re.compile(
        r"(?:Salary\s+as\s+per\s+provisions\s+contained\s+in\s+section\s+17\s*\(1\)|"
        r"17\s*\(1\))\s*.*?([\d,]+(?:\.\d+)?)",
        re.IGNORECASE,
    ),
    # Form 16 Part B line 2(e): employer-declared HRA exemption under 10(13A).
    # This is the EXEMPT portion, NOT the HRA received from employer.
    # Used to cross-validate Rule 2A computation once user fills basic/rent/city.
    "hra_exempt_10_13a": re.compile(
        r"(?:House\s+rent\s+allowance\s+under\s+section\s+10\s*\(13A\)|"
        r"10\s*\(13A\))\s*.*?([\d,]+(?:\.\d+)?)",
        re.IGNORECASE,
    ),
    # Form 16 Part B line 2(a): employer-declared LTA exemption under 10(5).
    # This is the EXEMPT portion, NOT the LTA received from employer.
    "lta_exempt_10_5": re.compile(
        r"(?:Travel\s+concession\s+or\s+assistance\s+under\s+section\s+10\s*\(5\)|"
        r"10\s*\(5\))\s*.*?([\d,]+(?:\.\d+)?)",
        re.IGNORECASE,
    ),
    # Form 16 Part B line 9: "Gross total income (6+8)"
    "gross_total_income": re.compile(
        r"Gross\s+[Tt]otal\s+[Ii]ncome\s*.*?([\d,]+(?:\.\d+)?)",
        re.IGNORECASE,
    ),
    # Form 16 Part A total TDS column
    "tds_deducted": re.compile(
        r"(?:Total\s+.*?Tax\s+[Dd]educted|TDS\s+[Dd]educted|"
        r"Net\s+tax\s+payable)\s*.*?([\d,]+(?:\.\d+)?)",
        re.IGNORECASE,
    ),

    # ------------------------------------------------------------------ #
    # Internal — not in PROFILE_FIELDS or REFERENCE_FIELDS                #
    # ------------------------------------------------------------------ #

    # Assessment year — used only by _check_ay_warning(), prefixed with _
    "_assessment_year": re.compile(
        r"(?:Assessment\s+Year|AY)\s*[:\-]?\s*(\d{4}-\d{2,4})",
        re.IGNORECASE,
    ),
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _parse_inr_amount(raw: str) -> float:
    """
    Parse Indian rupee amounts to float.

    Handles Indian comma grouping ('1,20,000' = one lakh twenty thousand)
    as well as Western formatting ('1,200,000') and plain integers ('120000').
    Simply strips all commas before float conversion — safe for all formats.

    Args:
        raw: Raw numeric string captured by regex (e.g. '1,20,000')

    Returns:
        float value (e.g. 120000.0)
    """
    return float(raw.replace(",", "").strip())


def _extract_after_part_b(text: str) -> str:
    """
    Return OCR text starting from the Part B section header.

    Form 16 Part A contains employer TAN/PAN and quarterly TDS breakdowns.
    Extracting Part A values accidentally gives wrong salary data. This
    function finds the Part B boundary and returns only the relevant portion.

    If no Part B marker is found, returns full text for best-effort extraction
    (some Form 16 formats skip the explicit Part B header).

    Args:
        text: Full concatenated OCR text from all pages

    Returns:
        Text from Part B onwards (or full text if no marker found)
    """
    pattern = re.compile(
        r"(?:Part\s*[-\u2013]?\s*B|Salary\s+Statement|Schedule\s+1)",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if match:
        return text[match.start():]
    # No Part B marker — process full text (best-effort)
    logger.debug(
        "Part B marker not found in OCR text — processing full document (best-effort)"
    )
    return text


def _build_confidence(raw_value: Optional[str]) -> str:
    """
    Map regex extraction result to a confidence level string.

    Confidence heuristic rationale: Form 16 is a structured, printed document.
    OCR character accuracy on printed text at 300 DPI is very high (>95%).
    The main source of uncertainty is whether the regex label pattern matched,
    not OCR character errors. A binary heuristic is therefore more predictable
    and easier to test than per-word pytesseract confidence scoring.

    HIGH_CONFIDENCE (0.90) > _THRESHOLD_GREEN (0.85) → 'green'
    NO_MATCH (0.0) < _THRESHOLD_YELLOW (0.60) → 'red'

    Args:
        raw_value: Raw string from regex group(1), or None if no match

    Returns:
        'green' if match found, 'red' if no match
    """
    if raw_value is None:
        return "red"
    # HIGH_CONFIDENCE = 0.90 is above the green threshold (0.85)
    return "green"


def _check_ay_warning(text: str) -> list[dict]:
    """
    Extract and validate the assessment year from OCR text.

    Returns a list with one WRONG_AY warning dict if the AY does not match
    AY 2025-26, or an empty list if the AY is correct or not found.

    Handles multiple formats:
    - '2025-26' → AY2025-26 → OK
    - '2025-2026' → AY2025-26 → OK
    - 'AY 2025-26' → AY2025-26 → OK
    - '2024-25' → AY2024-25 → WRONG_AY warning
    - 'FY 2024-25' → fiscal year → AY2025-26 → OK
    - 'FY 2023-24' → fiscal year → AY2024-25 → WRONG_AY warning

    Args:
        text: OCR text (full or Part B section)

    Returns:
        List of warning dicts (empty if correct AY or AY not found)
    """
    warnings: list[dict] = []
    match = FIELD_PATTERNS["_assessment_year"].search(text)
    if not match:
        return warnings

    raw_ay = match.group(1).strip()  # e.g. '2025-26' or '2024-25'

    # Parse start year and end year
    parts = raw_ay.split("-")
    start_year = int(parts[0])
    end_part = parts[1]
    # Handle '26' → 2026 and '2026' → 2026
    if len(end_part) == 4:
        end_year = int(end_part)
    else:
        # 2-digit suffix: prefix with century from start_year
        century = (start_year // 100) * 100
        end_year = century + int(end_part)

    # Detect FY vs AY from context (30 chars before the match)
    context_start = max(0, match.start() - 30)
    context_text = text[context_start:match.start()].upper()
    is_fiscal_year = ("F.Y" in context_text or "FY" in context_text) and "AY" not in context_text

    if is_fiscal_year:
        # FY 2024-25 → AY 2025-26
        ay_start = start_year + 1
        ay_end = end_year + 1
    else:
        ay_start = start_year
        ay_end = end_year

    # Valid AY is 2025-26 only
    if not (ay_start == 2025 and ay_end == 2026):
        display = f"AY{ay_start}-{str(ay_end)[-2:]}"
        warnings.append({
            "code": "WRONG_AY",
            "message": (
                f"Form 16 appears to be for {display}. "
                "Please verify you have uploaded the correct year's Form 16."
            ),
        })

    return warnings


def _extract_all_fields(
    text: str,
) -> tuple[dict, dict, dict, list[str], list[dict]]:
    """
    Run all FIELD_PATTERNS against Part B text and categorise results.

    Args:
        text: OCR text already sliced to Part B section

    Returns:
        Tuple of:
        - extracted_fields_raw: {field_name: {"value": float|None, "confidence": str}}
            for all PROFILE_FIELDS (directly mappable to UserFinancialProfile)
        - profile_fields_raw: {field_name: float} for non-None profile fields only
            (used as merge base in confirm route)
        - reference_fields_raw: {field_name: float|None} for REFERENCE_FIELDS
            (Form 16 totals — display / cross-validation only, not stored in profile)
        - non_extractable: list of UserFinancialProfile field names that cannot be
            read from Form 16 and must be collected from the user in the confirm step.
            Constant — same regardless of OCR quality.
        - ay_warnings: list of warning dicts from _check_ay_warning()
    """
    extracted_fields_raw: dict = {}
    profile_fields_raw: dict = {}
    reference_fields_raw: dict = {}

    for field_name, pattern in FIELD_PATTERNS.items():
        if field_name == "_assessment_year":
            continue  # handled separately via _check_ay_warning

        match = pattern.search(text)
        if match:
            if field_name in _TAIL_NUMBER_FIELDS:
                # -------------------------------------------------------- #
                # Two-column deduction row: Gross Amount | Deductible Amount
                #
                # pdfplumber often splits Form 16 table rows across lines:
                #   line 1: "(a) Deduction in respect of life insurance Rs."
                #   line 2: "1,00,000"         ← gross amount
                #   line 3: "contributions ... under section 80C"
                #   line 4: (next row continues)
                #
                # Fix: scan a 300-char window (≈3-4 lines) after the label
                # match. Anchor exclusively on "Rs." prefix so we only pick
                # up currency values, not section numbers like "80", "1B".
                # Taking the LAST Rs. amount = Deductible Amount column.
                # -------------------------------------------------------- #
                window = text[match.start(): match.start() + 300]
                # Stop window at the next deduction row letter to avoid
                # bleeding into the following row (e.g., stop before "\n(b)")
                next_row = re.search(r"\n\s*\([b-z]\)", window)
                if next_row:
                    window = window[: next_row.start()]
                # Pull only Rs.-prefixed amounts (filters out "80", "1B" etc.)
                rs_amounts = re.findall(
                    r"Rs\.?\s*([\d,]+(?:\.\d+)?)", window, re.IGNORECASE
                )
                raw = rs_amounts[-1] if rs_amounts else None
            else:
                raw = match.group(1)

            if raw is None:
                value = None
                confidence_str = "red"
            else:
                try:
                    value: Optional[float] = _parse_inr_amount(raw)
                except (ValueError, AttributeError):
                    # Parse failure (malformed number) → treat as not found
                    value = None
                    confidence_str = "red"
                else:
                    # home_loan_interest is declared as a loss (negative) in Form 16
                    # line 7(a). Store absolute value — UserFinancialProfile field is ≥ 0.
                    if field_name == "home_loan_interest" and value is not None:
                        value = abs(value)
                    confidence_str = _build_confidence(raw)
                    # basic_salary uses gross salary from sec 17(1) directly
                    # (user's explicit preference — shown as green).
        else:
            value = None
            confidence_str = "red"

        field_result = {"value": value, "confidence": confidence_str}

        if field_name in PROFILE_FIELDS:
            extracted_fields_raw[field_name] = field_result
            if value is not None:
                profile_fields_raw[field_name] = value
        elif field_name in REFERENCE_FIELDS:
            # Reference fields: just the plain value (or None) — not in extracted_fields
            reference_fields_raw[field_name] = value

    ay_warnings = _check_ay_warning(text)
    return (
        extracted_fields_raw,
        profile_fields_raw,
        reference_fields_raw,
        NON_EXTRACTABLE_FIELDS,   # constant list — same for every Form 16
        ay_warnings,
    )


# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------

_PDFPLUMBER_MIN_CHARS = 200  # Below this threshold → treat as scanned → use Tesseract


def _extract_text_pdfplumber(file_path: str) -> str:
    """
    Extract text directly from a text-based PDF using pdfplumber.

    Most Indian Form 16 PDFs generated by HR payroll software (Keka,
    Darwinbox, Greytip, Zoho Payroll, SAP) are text-based (selectable text).
    pdfplumber preserves layout, has no quality loss, and runs in milliseconds.

    Returns concatenated text from first 4 pages (Part B is always in this range).
    Returns empty string if file is not a PDF or on any error.
    """
    import pdfplumber

    try:
        full_text_parts: list[str] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages[:4]:  # Part B is always within first 4 pages
                text = page.extract_text(x_tolerance=3, y_tolerance=3)
                if text:
                    full_text_parts.append(text)
        combined = "\n".join(full_text_parts)
        logger.debug(
            "_extract_text_pdfplumber: extracted %d chars from %s",
            len(combined),
            file_path,
        )
        return combined
    except Exception as exc:
        logger.warning(
            "_extract_text_pdfplumber failed for %s: %s", file_path, exc
        )
        return ""


def _extract_text_tesseract(file_path: str) -> str:
    """
    Extract text via Tesseract OCR — fallback for scanned/image-based PDFs and images.

    Converts PDF pages to PIL Images via pdf2image (poppler), then runs
    pytesseract on each page. CPU-bound and slow (~2–5 s per page at 300 DPI).

    Only called when pdfplumber returns < _PDFPLUMBER_MIN_CHARS, meaning the
    PDF has no embedded text (scanned document).
    """
    from pathlib import Path

    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image

    # Rely on system PATH for pytesseract (assumes it's installed via brew/apt)
    # pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    path = Path(file_path)

    if path.suffix.lower() == ".pdf":
        try:
            images = convert_from_path(
                file_path,
                # poppler_path=r"C:\Program Files\poppler-25.12.0\Library\bin",
                dpi=300,          # Tesseract recommended minimum for high accuracy
                first_page=1,
                last_page=4,
            )
        except Exception as exc:
            logger.error("pdf2image failed for %s: %s", file_path, exc)
            return ""
    else:
        # JPEG or PNG — single image file
        images = [Image.open(file_path)]

    full_text = "\n".join(
        pytesseract.image_to_string(img, config=OCR_CONFIG)
        for img in images
    )
    logger.debug(
        "_extract_text_tesseract: extracted %d chars from %s",
        len(full_text),
        file_path,
    )
    return full_text


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def extract_form16(file_path: str) -> "OCRResult":
    """
    Extract Form 16 Part B fields from a validated temp file (PDF or image).

    Extraction Strategy
    -------------------
    Step 1 — pdfplumber (text-based PDFs): tries to extract embedded text
    directly. Fast (< 100 ms), lossless, and accurate for digital Form 16s
    produced by HR payroll software (Keka, Darwinbox, Greytip, Zoho, SAP).

    Step 2 — Tesseract OCR (scanned PDFs / images): fallback when pdfplumber
    extracts < 200 characters, indicating an image-only / scanned document.
    Slow (~2-5 s/page), approximate, but the only option for physical copies.

    Synchronous, CPU-bound. Blocks the event loop when called from an async
    FastAPI route. Acceptable for the current single-user dev model.
    Production fix: ``await asyncio.to_thread(extract_form16, file_path)``.

    Args:
        file_path: Absolute path to validated temp file (.pdf, .jpg, or .png).
                   File must already exist; MIME validation done by caller.

    Returns:
        OCRResult with extracted_fields, profile_fields, reference_fields,
        missing_profile_fields, summary, and warnings.
    """
    from backend.agents.input_agent.schemas import (
        FieldResult,
        OCRResult,
        OCRSummary,
        OCRWarning,
    )
    from pathlib import Path

    path = Path(file_path)
    extraction_method = "pdfplumber"

    # ------------------------------------------------------------------ #
    # Step 1: Try pdfplumber — fast, lossless, works for digital PDFs     #
    # ------------------------------------------------------------------ #
    if path.suffix.lower() == ".pdf":
        full_text = _extract_text_pdfplumber(file_path)
    else:
        full_text = ""  # Images go straight to Tesseract below

    # ------------------------------------------------------------------ #
    # Step 2: Fallback to Tesseract for scanned PDFs and image files      #
    # ------------------------------------------------------------------ #
    if len(full_text.strip()) < _PDFPLUMBER_MIN_CHARS:
        logger.info(
            "pdfplumber yielded only %d chars — falling back to Tesseract OCR",
            len(full_text.strip()),
        )
        full_text = _extract_text_tesseract(file_path)
        extraction_method = "tesseract"

    logger.info(
        "extract_form16: method=%s total_chars=%d file=%s",
        extraction_method,
        len(full_text),
        path.name,
    )

    # ------------------------------------------------------------------ #
    # Step 3: Slice to Part B section — prevents Part A TDS contamination #
    # ------------------------------------------------------------------ #
    part_b_text = _extract_after_part_b(full_text)

    # ------------------------------------------------------------------ #
    # Step 4: Run all FIELD_PATTERNS against the Part B text              #
    # ------------------------------------------------------------------ #
    extracted_raw, profile_raw, reference_raw, missing_fields, ay_warnings = (
        _extract_all_fields(part_b_text)
    )

    # ------------------------------------------------------------------ #
    # Step 5: Build typed FieldResult objects                             #
    # ------------------------------------------------------------------ #
    extracted_fields: dict[str, FieldResult] = {
        k: FieldResult(value=v["value"], confidence=v["confidence"])
        for k, v in extracted_raw.items()
    }

    # ------------------------------------------------------------------ #
    # Step 6: Compute summary statistics                                  #
    # ------------------------------------------------------------------ #
    green_count  = sum(1 for v in extracted_fields.values() if v.confidence == "green")
    yellow_count = sum(1 for v in extracted_fields.values() if v.confidence == "yellow")
    red_count    = sum(1 for v in extracted_fields.values() if v.confidence == "red")

    summary = OCRSummary(
        field_count=len(extracted_fields),
        green_count=green_count,
        yellow_count=yellow_count,
        red_count=red_count,
    )

    warnings = [OCRWarning(**w) for w in ay_warnings]

    logger.info(
        "extract_form16 complete file=%s method=%s green=%d yellow=%d red=%d "
        "missing_fields=%d warnings=%d",
        path.name,
        extraction_method,
        green_count,
        yellow_count,
        red_count,
        len(missing_fields),
        len(warnings),
    )

    return OCRResult(
        extracted_fields=extracted_fields,
        profile_fields=profile_raw,
        reference_fields=reference_raw,
        missing_profile_fields=missing_fields,
        summary=summary,
        warnings=warnings,
    )

