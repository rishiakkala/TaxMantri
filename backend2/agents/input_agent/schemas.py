"""
schemas.py — InputAgent Pydantic v2 data contracts.

Defines:
  - CityType, AgeBracket, InputMethod enums
  - UserFinancialProfile  (the central data contract — all agents consume this)
  - ErrorDetail, ErrorBody, ErrorResponse  (cross-cutting error envelope)

LOCKED FIELD NAMES (from 01-CONTEXT.md — do not rename):
  - monthly_rent_paid      (monthly value; tax engine multiplies ×12 for HRA Rule 2A)
  - health_insurance_self  (not 'health_insurance_80d')
  - health_insurance_parents
  - employer_nps_80ccd2    (allowed in both regimes, capped at 10% of basic)
  - employee_nps_80ccd1b   (old regime only, cap ₹50K)
  - savings_interest_80tta

PHASE 2 ADDITION:
  - parent_senior_citizen  (bool, default False) — determines 80D parent cap
"""
import uuid
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CityType(str, Enum):
    metro = "metro"
    non_metro = "non_metro"


class AgeBracket(str, Enum):
    under60 = "under60"
    sixty_79 = "60_79"
    eighty_plus = "80plus"


class InputMethod(str, Enum):
    ocr = "ocr"
    manual = "manual"


# ---------------------------------------------------------------------------
# UserFinancialProfile — central data contract
# ---------------------------------------------------------------------------

class UserFinancialProfile(BaseModel):
    """
    Complete financial profile for a salaried Indian taxpayer filing ITR-1 (AY 2025-26).
    
    All monetary fields are in INR (Indian Rupees).
    All salary/income fields are ANNUAL unless stated otherwise.
    monthly_rent_paid is MONTHLY — backend multiplies ×12 for HRA Rule 2A.
    
    extra='forbid' ensures unknown fields from client requests cause a 422 error.
    """
    model_config = ConfigDict(extra="forbid")

    # --- Identity ---
    # Generated server-side if not provided; client may supply for idempotent upserts
    profile_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="UUID identifying this profile. Auto-generated if omitted.",
    )

    # --- Required annual income fields ---
    basic_salary: float = Field(
        ..., ge=0,
        description="Annual basic salary in INR (gross, before deductions).",
    )

    # --- Optional salary components (default 0 so tests can omit unused fields) ---
    hra_received: Optional[float] = Field(
        default=0, ge=0,
        description="Annual HRA component received from employer (CTC component, not HRA exemption).",
    )
    other_allowances: Optional[float] = Field(
        default=0, ge=0,
        description="Annual other allowances combined if not itemised separately.",
    )
    professional_tax: Optional[float] = Field(
        default=0, ge=0, le=2400,
        description="Annual professional tax deducted by employer. Statutory max ₹2,400/year.",
    )
    lta: Optional[float] = Field(
        default=0, ge=0,
        description="Leave Travel Allowance — annual.",
    )
    special_allowance: Optional[float] = Field(
        default=0, ge=0,
        description="Special/performance allowance — annual.",
    )

    # --- HRA calculation inputs ---
    monthly_rent_paid: Optional[float] = Field(
        default=0, ge=0,
        description=(
            "Monthly rent paid by taxpayer. "
            "Backend multiplies ×12 to get annual rent for HRA Rule 2A calculation. "
            "Set 0 if not paying rent."
        ),
    )
    city_type: CityType = Field(
        ...,
        description="Determines HRA metro percentage: metro=50% of basic, non_metro=40% of basic.",
    )

    # --- Other income (annual) ---
    other_income: Optional[float] = Field(
        default=0, ge=0,
        description="Income from other sources (interest, FD, freelance, etc.) — annual.",
    )

    # --- Chapter VI-A deductions (annual, all optional, default 0) ---
    investments_80c: Optional[float] = Field(
        default=0, ge=0,
        description=(
            "Total Section 80C investments: ELSS, PPF, LIC, EPF employee contribution, "
            "NSC, home loan principal repayment, tuition fees, etc. "
            "Tax engine caps at ₹1,50,000 internally."
        ),
    )
    ppf_contribution: Optional[float] = Field(
        default=0, ge=0,
        description="PPF contribution — informational breakdown of investments_80c.",
    )
    home_loan_principal: Optional[float] = Field(
        default=0, ge=0,
        description="Home loan principal repayment — informational breakdown of investments_80c.",
    )
    health_insurance_self: Optional[float] = Field(
        default=0, ge=0,
        description=(
            "Section 80D — health insurance premium for self, spouse, and children. "
            "Under 60: capped at ₹25,000. 60+: capped at ₹50,000."
        ),
    )
    health_insurance_parents: Optional[float] = Field(
        default=0, ge=0,
        description=(
            "Section 80D — health insurance premium for parents. "
            "If parents under 60: cap ₹25,000. If parents 60+: cap ₹50,000."
        ),
    )
    employee_nps_80ccd1b: Optional[float] = Field(
        default=0, ge=0,
        description=(
            "Employee voluntary NPS contribution under Section 80CCD(1B). "
            "Additional deduction of up to ₹50,000 — old regime ONLY. "
            "NOT allowed in new regime (tax engine ignores it for new regime)."
        ),
    )
    employer_nps_80ccd2: Optional[float] = Field(
        default=0, ge=0,
        description=(
            "Employer NPS contribution under Section 80CCD(2). "
            "Allowed in BOTH regimes. Capped at 10% of basic_salary. "
            "Tax engine applies min(employer_nps_80ccd2, 0.10 * basic_salary)."
        ),
    )
    home_loan_interest: Optional[float] = Field(
        default=0, ge=0,
        description=(
            "Section 24(b) — home loan interest for self-occupied property. "
            "Old regime cap: ₹2,00,000. NOT allowed in new regime."
        ),
    )
    savings_interest_80tta: Optional[float] = Field(
        default=0, ge=0,
        description=(
            "Section 80TTA (under 60) / 80TTB (80+) — interest from savings accounts. "
            "Under 60: 80TTA cap ₹10,000 (savings account only). "
            "80+: 80TTB cap ₹50,000 (savings + FD interest)."
        ),
    )

    # --- Profile metadata ---
    age_bracket: AgeBracket = Field(
        ...,
        description="Taxpayer age bracket — determines 80D limits, 87A eligibility, and senior citizen slabs.",
    )
    input_method: InputMethod = Field(
        ...,
        description="How this profile was created: 'ocr' (from Form 16) or 'manual' (wizard).",
    )

    # --- Phase 2: parent age for 80D parent cap ---
    parent_senior_citizen: bool = Field(
        default=False,
        description=(
            "True if one or both parents are senior citizens (60+). "
            "False → 80D parent cap ₹25,000. True → cap ₹50,000."
        ),
    )

    # --- Cross-field validation ---
    @model_validator(mode="after")
    def validate_hra_not_exceeds_basic(self) -> "UserFinancialProfile":
        """HRA component from employer cannot exceed basic salary."""
        hra = self.hra_received or 0
        if hra > self.basic_salary:
            raise ValueError(
                f"hra_received (₹{hra:,.0f}) cannot exceed "
                f"basic_salary (₹{self.basic_salary:,.0f})"
            )
        return self


# ---------------------------------------------------------------------------
# Error response models — used by main.py exception handlers (cross-cutting)
# ---------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    """Single field-level validation or business-rule error."""
    model_config = ConfigDict(extra="forbid")

    field: Optional[str] = None   # Dot-notation field path, e.g. "investments_80c"
    issue: str                     # Human-readable description of the problem


class ErrorBody(BaseModel):
    """Error envelope body."""
    model_config = ConfigDict(extra="forbid")

    code: str                                      # VALIDATION_ERROR, NOT_FOUND, etc.
    message: str                                   # High-level error description
    details: List[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """
    Standard error response format for all TaxMantri endpoints.
    
    Structure: {"error": {"code": "...", "message": "...", "details": [...]}}
    """
    model_config = ConfigDict(extra="forbid")

    error: ErrorBody


# ---------------------------------------------------------------------------
# Phase 6: OCR schemas — FieldResult, OCRSummary, OCRWarning, OCRResult, ConfirmRequest
# ---------------------------------------------------------------------------

class FieldResult(BaseModel):
    """Per-field OCR extraction result. value is None if regex found no match."""
    value: Optional[float] = None
    confidence: Literal["green", "yellow", "red"]


class OCRSummary(BaseModel):
    """Summary counts of confidence levels across all extracted fields."""
    field_count: int
    green_count: int
    yellow_count: int
    red_count: int


class OCRWarning(BaseModel):
    """Non-fatal warning from OCR extraction (e.g. wrong assessment year)."""
    code: str
    message: str


class OCRResult(BaseModel):
    """
    Return value from extract_form16() and the /api/upload response.

    extracted_fields: all profile-mappable fields OCR attempted (not reference-only
        or non-extractable fields like monthly_rent_paid / city_type)
    profile_fields: subset of extracted_fields with non-None values only
        (used by confirm route as merge base with user edits)
    reference_fields: gross_total_income, tds_deducted — display only,
        NOT stored in UserFinancialProfile
    missing_profile_fields: UserFinancialProfile fields that cannot be read from
        Form 16 (e.g. monthly_rent_paid, city_type, age_bracket) — the frontend
        renders input fields for these in the confirmation step.
    """
    extracted_fields: dict[str, FieldResult]
    profile_fields: dict[str, float]
    reference_fields: dict[str, Optional[float]]
    missing_profile_fields: List[str] = Field(default_factory=list)
    summary: OCRSummary
    warnings: List[OCRWarning]


class ConfirmRequest(BaseModel):
    """
    Request body for PUT /api/profile/confirm.
    edited_fields can contain any UserFinancialProfile field — including
    non-extractable fields (monthly_rent_paid, city_type, age_bracket, etc.)
    that OCR cannot produce from Form 16.
    """
    model_config = ConfigDict(extra="forbid")

    session_id: str
    edited_fields: dict = {}


__all__ = [
    "CityType",
    "AgeBracket",
    "InputMethod",
    "UserFinancialProfile",
    "ErrorDetail",
    "ErrorBody",
    "ErrorResponse",
    # Phase 6 OCR schemas
    "FieldResult",
    "OCRSummary",
    "OCRWarning",
    "OCRResult",
    "ConfirmRequest",
]
