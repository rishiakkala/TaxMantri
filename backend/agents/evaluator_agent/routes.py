"""
EvaluatorAgent HTTP routes — POST /api/calculate,
                              GET /api/itr1-mapping/{profile_id},
                              GET /api/export/{profile_id}

POST /api/calculate now runs the full LangGraph agentic pipeline:
  InputAgent → MatcherAgent → EvaluatorAgent (Mistral LLM grounded rationale + citations)

Accepts EITHER a full UserFinancialProfile inline OR a profile_id reference.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.evaluator_agent.itr1_mapper import build_itr1_mapping
from backend.agents.evaluator_agent.pdf_generator import generate_tax_report
from backend.agents.evaluator_agent.tax_engine import compare_regimes
from backend.agents.evaluator_agent.schemas import TaxResult
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


async def _run_agentic_pipeline(
    request: Request,
    profile: UserFinancialProfile,
    profile_id: str,
    use_profile_id: bool = False,
) -> TaxResult:
    """
    Run the LangGraph agentic pipeline (InputAgent → MatcherAgent → EvaluatorAgent).

    Falls back to direct compare_regimes() if the graph is unavailable.
    use_profile_id=True means InputAgent will load the profile from DB (Mode A),
    skipping re-validation — used when profile is already confirmed and stored.
    """
    tax_graph = getattr(getattr(request, "app", None), "state", None)
    tax_graph = getattr(tax_graph, "tax_graph", None) if tax_graph else None

    if tax_graph is None:
        logger.warning("tax_graph not available — falling back to direct tax engine")
        result = compare_regimes(profile)
        return result.model_copy(update={"profile_id": profile_id})

    initial_state = {
        "profile_id": profile_id if use_profile_id else None,
        "raw_input": profile.model_dump(),
        "input_method": profile.input_method.value,
        "file_path": None,
        "input_errors": [],
        "errors": [],
    }

    logger.info("Invoking LangGraph pipeline for profile_id=%s", profile_id)
    try:
        final_state = await tax_graph.ainvoke(initial_state)
    except Exception as exc:
        logger.error("LangGraph pipeline failed: %s — falling back to direct engine", exc)
        result = compare_regimes(profile)
        return result.model_copy(update={"profile_id": profile_id})

    # Check for pipeline errors
    if final_state.get("should_stop"):
        errors = final_state.get("input_errors", ["Pipeline error"])
        raise ValueError(json.dumps([{"field": None, "issue": e} for e in errors]))

    # Extract tax_result from graph state
    tax_result_dict = final_state.get("tax_result")
    if not tax_result_dict:
        logger.error("EvaluatorAgent produced no tax_result — falling back")
        result = compare_regimes(profile)
        return result.model_copy(update={"profile_id": profile_id})

    # Inject agentic fields from graph state into the result dict
    tax_result_dict["profile_id"] = profile_id
    tax_result_dict["citations"] = final_state.get("citations", [])
    tax_result_dict["law_context"] = final_state.get("law_context", "")

    return TaxResult.model_validate(tax_result_dict)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/calculate")
async def calculate_tax(
    request: Request,
    request_body: dict,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Calculate tax using the full LangGraph agentic pipeline.

    Pipeline: InputAgent (load/validate) → MatcherAgent (RAG + Mistral law context)
              → EvaluatorAgent (deterministic calc + Mistral rationale with IT Act citations)

    Accepts two request shapes:
      - Shape A: Full UserFinancialProfile JSON body (inline calculation)
      - Shape B: {"profile_id": "uuid"} — look up stored profile, run through pipeline
    """
    keys = set(request_body.keys())

    if keys == {"profile_id"}:
        # ----------------------------------------------------------------
        # Shape B — load stored confirmed profile, pass profile_id to graph
        # ----------------------------------------------------------------
        profile_id = request_body["profile_id"]
        profile = await get_profile(db, profile_id)
        if profile is None:
            raise HTTPException(
                status_code=404,
                detail=f"Profile '{profile_id}' not found",
            )
        logger.info("Running agentic pipeline for stored profile_id=%s", profile_id)
        use_profile_id = True

    else:
        # ----------------------------------------------------------------
        # Shape A — inline UserFinancialProfile body
        # ----------------------------------------------------------------
        try:
            profile = UserFinancialProfile.model_validate(request_body)
        except Exception as exc:
            raise exc

        try:
            validate_business_rules(profile)
        except ValueError as exc:
            return _make_validation_error_response(str(exc))

        profile_id = profile.profile_id
        await save_profile(db, profile)
        logger.info("Running agentic pipeline for inline profile_id=%s", profile_id)
        use_profile_id = False

    # ---- Run the agentic pipeline -------------------------------------------
    try:
        result = await _run_agentic_pipeline(request, profile, profile_id, use_profile_id)
    except ValueError as exc:
        return _make_validation_error_response(str(exc))

    # ---- Persist TaxResult to PostgreSQL ------------------------------------
    await save_result(db, result)

    logger.info(
        "Tax calculated profile_id=%s recommended=%s savings=%s citations=%d",
        profile_id,
        result.recommended_regime,
        result.savings_amount,
        len(result.citations),
    )

    return JSONResponse(status_code=200, content=result.model_dump())


# ---------------------------------------------------------------------------
# GET /api/itr1-mapping/{profile_id}
# ---------------------------------------------------------------------------

@router.get("/itr1-mapping/{profile_id}")
async def get_itr1_mapping(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Return structured ITR-1 Sahaj field mapping for a calculated TaxResult."""
    profile = await get_profile(db, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found")

    tax_result = await get_result(db, profile_id)
    if tax_result is None:
        raise HTTPException(
            status_code=404,
            detail="No tax calculation found for this profile. Call POST /api/calculate first.",
        )

    mapping = build_itr1_mapping(profile, tax_result)
    logger.info("ITR1 mapping returned profile_id=%s entries=%d", profile_id, len(mapping))
    return JSONResponse(status_code=200, content=[entry.model_dump() for entry in mapping])


# ---------------------------------------------------------------------------
# GET /api/export/{profile_id}
# ---------------------------------------------------------------------------

@router.get("/export/{profile_id}")
async def export_pdf(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Generate and download a formatted TaxMantri PDF report."""
    profile = await get_profile(db, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found")

    tax_result = await get_result(db, profile_id)
    if tax_result is None:
        raise HTTPException(
            status_code=404,
            detail="No tax calculation found for this profile. Call POST /api/calculate first.",
        )

    buffer = generate_tax_report(profile, tax_result)
    filename = f"taxmantri_AY2025-26_{profile_id}.pdf"
    logger.info("PDF exported profile_id=%s filename=%s", profile_id, filename)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
