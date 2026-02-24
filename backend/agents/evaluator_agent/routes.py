"""
EvaluatorAgent HTTP routes — POST /api/calculate,
                              GET /api/itr1-mapping/{profile_id},
                              GET /api/export/{profile_id}

No JWT authentication in v1 (hackathon decision — deferred to v2).
Accepts EITHER a full UserFinancialProfile inline OR a profile_id reference.
Calls compare_regimes() (pure Python, zero LLM) and stores TaxResult.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.evaluator_agent.itr1_mapper import build_itr1_mapping
from backend.agents.evaluator_agent.pdf_generator import generate_tax_report
from backend.agents.evaluator_agent.tax_engine import compare_regimes
from backend.agents.input_agent.schemas import (
    ErrorBody,
    ErrorDetail,
    ErrorResponse,
    UserFinancialProfile,
)
from backend.agents.input_agent.validator import validate_business_rules
from backend.database import get_db
from backend.store import get_profile, get_result, save_profile, save_result

router = APIRouter(prefix="/api", tags=["evaluator_agent"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_validation_error_response(violations_json: str) -> JSONResponse:
    """Parse JSON-encoded violations and return standard 422 error envelope."""
    try:
        violations: list[dict] = json.loads(violations_json)
    except (json.JSONDecodeError, ValueError):
        violations = [{"field": None, "issue": violations_json}]
    details = [ErrorDetail(field=v.get("field"), issue=v["issue"]) for v in violations]
    body = ErrorResponse(
        error=ErrorBody(
            code="VALIDATION_ERROR",
            message="Profile validation failed",
            details=details,
        )
    )
    return JSONResponse(status_code=422, content=body.model_dump())


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/calculate")
async def calculate_tax(
    request_body: dict,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Calculate tax for a financial profile.

    Accepts two request shapes:
      - Shape A: Full UserFinancialProfile JSON body (inline calculation)
      - Shape B: {"profile_id": "uuid"} — look up stored profile, then calculate

    Returns: Full TaxResult JSON — old_regime, new_regime, recommended_regime,
             savings_amount, rationale, old_regime_suggestions, new_regime_suggestions.
    """
    keys = set(request_body.keys())

    if keys == {"profile_id"}:
        # ----------------------------------------------------------------
        # Shape B — look up stored profile by profile_id
        # ----------------------------------------------------------------
        profile_id = request_body["profile_id"]
        profile = await get_profile(db, profile_id)
        if profile is None:
            raise HTTPException(
                status_code=404,
                detail=f"Profile '{profile_id}' not found",
            )
        logger.info("Calculating tax for stored profile_id=%s", profile_id)

    else:
        # ----------------------------------------------------------------
        # Shape A — inline UserFinancialProfile body
        # ----------------------------------------------------------------
        try:
            profile = UserFinancialProfile.model_validate(request_body)
        except Exception as exc:
            # Let FastAPI's global RequestValidationError handler format Pydantic errors
            raise exc

        # Business-rule validation (INPUT-02)
        try:
            validate_business_rules(profile)
        except ValueError as exc:
            return _make_validation_error_response(str(exc))

        # Persist profile so /api/itr1-mapping and /api/export can look it up (Gap 3 fix)
        profile_id = profile.profile_id
        await save_profile(db, profile)
        logger.info("Calculating tax for inline profile profile_id=%s", profile_id)

    # ---- Run the deterministic tax engine (pure Python, zero LLM) ----------
    result = compare_regimes(profile)

    # Set profile_id on result (TaxResult.profile_id is Optional — attach it now)
    result = result.model_copy(update={"profile_id": profile_id})

    # ---- Persist TaxResult to PostgreSQL via store facade (EVAL-06) --------
    await save_result(db, result)

    # PII-safe log — only profile_id, regime, savings (no salary / PAN / name)
    logger.info(
        "Tax calculated profile_id=%s recommended=%s savings=%s",
        profile_id,
        result.recommended_regime,
        result.savings_amount,
    )

    return JSONResponse(status_code=200, content=result.model_dump())


# ---------------------------------------------------------------------------
# GET /api/itr1-mapping/{profile_id}  (Phase 7 — EVAL-07)
# ---------------------------------------------------------------------------

@router.get("/itr1-mapping/{profile_id}")
async def get_itr1_mapping(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Return structured ITR-1 Sahaj field mapping for a calculated TaxResult.

    Maps TaxResult + UserFinancialProfile to ITR-1 schedule positions for both
    old and new regimes. Each entry includes: itr1_field, schedule, value,
    source_field, regime, and note (Rule 2A breakdown for HRA; null otherwise).
    Zero-value fields are omitted.

    Returns:
        200: JSON array of ITR1FieldMap entries
        404: Standard error if profile not found or TaxResult not yet calculated
    """
    profile = await get_profile(db, profile_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"Profile '{profile_id}' not found",
        )

    tax_result = await get_result(db, profile_id)
    if tax_result is None:
        raise HTTPException(
            status_code=404,
            detail="No tax calculation found for this profile. Call POST /api/calculate first.",
        )

    mapping = build_itr1_mapping(profile, tax_result)

    logger.info(
        "ITR1 mapping returned profile_id=%s entries=%d",
        profile_id,
        len(mapping),
    )

    return JSONResponse(
        status_code=200,
        content=[entry.model_dump() for entry in mapping],
    )


# ---------------------------------------------------------------------------
# GET /api/export/{profile_id}  (Phase 7 — OUT-01)
# ---------------------------------------------------------------------------

@router.get("/export/{profile_id}")
async def export_pdf(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Generate and download a formatted TaxMantri PDF report for CA review.

    The PDF is generated fresh on every request (no disk caching).
    Contains: header, rationale, savings callout, regime comparison table,
    deduction breakdown, optimization suggestions, ITR-1 mapping, disclaimer.

    Returns:
        200: StreamingResponse with application/pdf and Content-Disposition: attachment
        404: Standard error if profile not found or TaxResult not yet calculated
    """
    profile = await get_profile(db, profile_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"Profile '{profile_id}' not found",
        )

    tax_result = await get_result(db, profile_id)
    if tax_result is None:
        raise HTTPException(
            status_code=404,
            detail="No tax calculation found for this profile. Call POST /api/calculate first.",
        )

    buffer = generate_tax_report(profile, tax_result)
    filename = f"taxmantri_AY2025-26_{profile_id}.pdf"

    logger.info(
        "PDF exported profile_id=%s filename=%s",
        profile_id,
        filename,
    )

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
