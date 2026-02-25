"""
InputAgent HTTP routes — POST /api/profile, GET /api/profile/{profile_id},
                         POST /api/upload, PUT /api/profile/confirm

No JWT authentication in v1 (hackathon decision — deferred to v2).
PII protection: PAN hashed with SHA-256 before any storage or logging.
"""
from __future__ import annotations

import hashlib
import json
import logging
import magic
import os
import tempfile
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.input_agent.schemas import (
    ConfirmRequest,
    ErrorBody,
    ErrorDetail,
    ErrorResponse,
    UserFinancialProfile,
)
from backend.agents.input_agent.validator import validate_business_rules, validate_hra_consistency
from backend.database import get_db
from backend.store import get_profile, save_profile

router = APIRouter(prefix="/api", tags=["input_agent"])
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Upload constants
# ---------------------------------------------------------------------------

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIMES = {"application/pdf", "image/jpeg", "image/png"}
MIME_EXTENSIONS = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}
OCR_SESSION_TTL = 1800  # 30 minutes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash_pan_if_present(profile_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Replace plaintext PAN with its SHA-256 hash before storage (INPUT-08).

    The UserFinancialProfile schema does not currently include a 'pan' field,
    but this guard future-proofs against the field being added without a
    corresponding hashing step.

    Args:
        profile_dict: model_dump() output from UserFinancialProfile.

    Returns:
        A copy of profile_dict with 'pan' replaced by its SHA-256 hex digest
        if the key is present and non-empty. Unchanged if no 'pan' key exists.
    """
    if "pan" in profile_dict and profile_dict["pan"]:
        plaintext = str(profile_dict["pan"])
        profile_dict = dict(profile_dict)          # shallow copy — never mutate original
        profile_dict["pan"] = hashlib.sha256(plaintext.encode()).hexdigest()
    return profile_dict


def _make_validation_error_response(violations_json: str) -> JSONResponse:
    """
    Parse the JSON-encoded violations list from validate_business_rules() and
    return a standard 422 ErrorResponse.
    """
    try:
        violations: list[dict[str, Any]] = json.loads(violations_json)
    except (json.JSONDecodeError, ValueError):
        # Fallback if the ValueError message is plain text (e.g., from model_validator)
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

@router.post("/profile")
async def create_profile(
    profile: UserFinancialProfile,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Validate and persist a UserFinancialProfile.

    Returns:
        200: {profile_id, session_id, status: "created", validation_errors: []}
        422: Standard error envelope listing all business-rule violations.

    Note: UserFinancialProfile.profile_id has default_factory=uuid4, so it is
    generated automatically if not provided by the caller.
    """
    # Step 1: Business-rule validation (INPUT-02)
    try:
        validate_business_rules(profile)
    except ValueError as e:
        return _make_validation_error_response(str(e))

    # Step 2: PAN hashing (INPUT-08) — operates on the dict before storage
    profile_dict = profile.model_dump()
    profile_dict = _hash_pan_if_present(profile_dict)
    # Reconstruct so any PAN hash is in the persisted object
    profile = UserFinancialProfile.model_validate(profile_dict)

    # Step 3: Generate session_id server-side
    session_id = str(uuid.uuid4())

    # Step 4: Persist via store facade (INPUT-03)
    # save_profile() already accepts session_id kwarg
    profile_id = await save_profile(db, profile, session_id=session_id)

    # PII-safe log: only profile_id, session_id, input_method — no salary/PAN/name
    logger.info(
        "Profile created profile_id=%s session_id=%s input_method=%s",
        profile_id,
        session_id,
        profile.input_method.value,
    )

    return JSONResponse(
        status_code=200,
        content={
            "profile_id": profile_id,
            "session_id": session_id,
            "status": "created",
            "validation_errors": [],
        },
    )


@router.get("/profile/{profile_id}")
async def get_profile_by_id(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Retrieve a stored UserFinancialProfile by profile_id.

    Returns:
        200: The stored profile as JSON
        404: Standard error envelope if profile not found
    """
    profile = await get_profile(db, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found")

    logger.info("Profile retrieved profile_id=%s", profile_id)
    return JSONResponse(status_code=200, content=profile.model_dump())


# ---------------------------------------------------------------------------
# POST /api/upload  (Phase 6 — INPUT-05)
# ---------------------------------------------------------------------------

@router.post("/upload")
async def upload_form16(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
) -> JSONResponse:
    """
    Upload a Form 16 PDF or image. Synchronous OCR extraction returns
    per-field confidence indicators (green/yellow/red) and stores the
    result in Redis for 30 minutes for subsequent /api/profile/confirm.

    Returns:
        200: {session_id, extracted_fields, summary, warnings}
        422: FILE_TOO_LARGE or INVALID_MIME_TYPE (no disk write on error)

    NOTE: pytesseract.image_to_string() is synchronous CPU-bound and blocks
    the event loop. Acceptable for hackathon; production fix: asyncio.to_thread().
    """
    # Step 1: Read all bytes first — never write to disk before validating
    contents = await file.read()

    # Step 2: Size check BEFORE any disk write
    if len(contents) > MAX_UPLOAD_SIZE:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "FILE_TOO_LARGE",
                    "message": "File size exceeds maximum allowed 10 MB",
                    "details": [],
                }
            },
        )

    # Step 3: MIME detection from content bytes (NOT file.content_type — spoofable)
    detected_mime = magic.from_buffer(contents[:2048], mime=True)
    if detected_mime not in ALLOWED_MIMES:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "INVALID_MIME_TYPE",
                    "message": (
                        f"Unsupported file type '{detected_mime}'. "
                        "Allowed: PDF, JPEG, PNG"
                    ),
                    "details": [],
                }
            },
        )

    # Step 4: Write validated content to temp file with UUID name
    suffix = MIME_EXTENSIONS[detected_mime]
    temp_path = os.path.join(
        tempfile.gettempdir(),
        f"taxmantri_{uuid.uuid4().hex}{suffix}",
    )
    with open(temp_path, "wb") as fh:
        fh.write(contents)

    # Step 5: Register cleanup BEFORE OCR (BackgroundTask runs AFTER response)
    # Pass the STRING path — NOT the UploadFile object (may be closed by then)
    background_tasks.add_task(os.unlink, temp_path)

    # Step 6: Run OCR — synchronous, acceptable for hackathon
    from backend.agents.input_agent.ocr_service import extract_form16  # lazy import
    result = extract_form16(temp_path)

    # Step 7: Generate session_id and store OCR result in Redis
    session_id = str(uuid.uuid4())
    redis = request.app.state.redis
    await redis.setex(
        f"ocr:{session_id}",
        OCR_SESSION_TTL,
        result.model_dump_json(),
    )

    logger.info(
        "Form16 uploaded session_id=%s green=%d yellow=%d red=%d",
        session_id,
        result.summary.green_count,
        result.summary.yellow_count,
        result.summary.red_count,
    )

    # Step 8: Return response.
    #
    # reference_fields — Form 16 totals shown to the user so they understand what
    #   was read from their document. Key field: hra_exempt_10_13a lets the frontend
    #   display "Form 16 says your HRA exemption was ₹X — please enter your salary
    #   breakdown below so we can verify this."
    #
    # missing_profile_fields — constant list of fields Form 16 cannot provide.
    #   Frontend renders these as required inputs in the confirmation step so the
    #   user knows exactly what to fill in before calling PUT /api/profile/confirm.
    return JSONResponse(
        status_code=200,
        content={
            "session_id": session_id,
            "extracted_fields": {
                k: v.model_dump() for k, v in result.extracted_fields.items()
            },
            "reference_fields": result.reference_fields,
            "missing_profile_fields": result.missing_profile_fields,
            "summary": result.summary.model_dump(),
            "warnings": [w.model_dump() for w in result.warnings],
        },
    )


# ---------------------------------------------------------------------------
# PUT /api/profile/confirm  (Phase 6 — INPUT-07)
# ---------------------------------------------------------------------------

@router.put("/profile/confirm")
async def confirm_profile(
    body: ConfirmRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Merge OCR-extracted fields with user edits, validate, and store
    as a finalized UserFinancialProfile in PostgreSQL.

    Returns:
        200: {"profile_id": "...", "status": "confirmed"}
        404: SESSION_NOT_FOUND (JSONResponse — bypasses global http_exception_handler)
        422: VALIDATION_ERROR with field-level details
    """
    redis = request.app.state.redis

    # Step 1: Fetch OCR base from Redis
    # Key: ocr:{session_id}, written by POST /api/upload with TTL 1800s
    raw = await redis.get(f"ocr:{body.session_id}")
    if raw is None:
        # CRITICAL: Use JSONResponse directly — NOT raise HTTPException(404).
        # The Phase 1 http_exception_handler maps ALL 404 HTTPExceptions to
        # code "NOT_FOUND". We need the locked code "SESSION_NOT_FOUND".
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "SESSION_NOT_FOUND",
                    "message": (
                        "OCR session expired or not found. "
                        "Please re-upload your Form 16."
                    ),
                    "details": [],
                }
            },
        )

    # Step 2: Parse Redis data
    # profile_fields: non-None profile-mappable fields extracted by OCR
    # reference_fields: Form 16 totals used for cross-validation (not stored in profile)
    ocr_data = json.loads(raw)
    base_fields: dict = ocr_data.get("profile_fields", {})
    reference_fields: dict = ocr_data.get("reference_fields", {})

    # Step 3: User edits override OCR field by field
    # User may supply any UserFinancialProfile field including non-extractable ones
    # (monthly_rent_paid, city_type, age_bracket, parent_senior_citizen, etc.)
    merged: dict = {**base_fields, **body.edited_fields}

    # Step 4: Force input_method = "ocr" — required field, must set before Pydantic parse
    merged["input_method"] = "ocr"

    # Step 5: Pydantic structural validation
    try:
        profile = UserFinancialProfile(**merged)
    except ValidationError as exc:
        details = [
            {
                "field": ".".join(str(loc) for loc in err["loc"]),
                "issue": err["msg"],
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Profile validation failed",
                    "details": details,
                }
            },
        )

    # Step 6: Business-rule validation (same validator as POST /api/profile)
    # validate_business_rules raises ValueError(json.dumps(violations_list))
    try:
        validate_business_rules(profile)
    except ValueError as exc:
        try:
            violations = json.loads(str(exc))
        except (json.JSONDecodeError, TypeError):
            violations = [{"field": "unknown", "issue": str(exc)}]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Profile validation failed",
                    "details": violations,
                }
            },
        )

    # Step 7: HRA consistency check — OCR profiles only (INPUT-09).
    # Compares Rule 2A exemption computed from user-entered basic/hra/rent against the
    # employer-declared exemption in Form 16 line 2(e). Returns warnings (not errors)
    # so the user can proceed even if there is a small discrepancy.
    hra_declared: float | None = reference_fields.get("hra_exempt_10_13a")
    hra_warnings = validate_hra_consistency(profile, hra_declared)

    # Step 8: Store finalized profile in PostgreSQL via store facade
    profile_id = await save_profile(db, profile, session_id=body.session_id)

    logger.info(
        "OCR profile confirmed profile_id=%s session_id=%s hra_warnings=%d",
        profile_id,
        body.session_id,
        len(hra_warnings),
    )

    # Step 9: Return response — include HRA warnings so the frontend can surface them.
    # Even with warnings the profile is confirmed and the client should proceed to
    # POST /api/calculate. The user may choose to re-edit their inputs if the
    # mismatch is significant.
    return JSONResponse(
        status_code=200,
        content={
            "profile_id": profile_id,
            "status": "confirmed",
            "warnings": hra_warnings,
        },
    )


# ---------------------------------------------------------------------------
# GET /api/ocr-debug/{session_id}  — developer tool, NOT for production
# ---------------------------------------------------------------------------

@router.get("/ocr-debug")
async def ocr_debug_extract(
    file_path: str,
) -> JSONResponse:
    """
    Developer debug endpoint — extracts text from a local file path using
    pdfplumber and returns the raw text + per-field regex match results.

    Usage (curl):
        curl "http://localhost:8000/api/ocr-debug?file_path=C:/path/to/form16.pdf"

    Returns:
        200: {method, char_count, part_b_char_count, raw_text_preview,
              part_b_text_preview, field_matches}
    """
    import os
    from backend.agents.input_agent.ocr_service import (
        FIELD_PATTERNS,
        _PDFPLUMBER_MIN_CHARS,
        _extract_after_part_b,
        _extract_text_pdfplumber,
        _extract_text_tesseract,
    )

    if not os.path.exists(file_path):
        return JSONResponse(
            status_code=404,
            content={"error": f"File not found: {file_path}"},
        )

    # Try pdfplumber first, fall back to Tesseract
    full_text = _extract_text_pdfplumber(file_path)
    method = "pdfplumber"
    if len(full_text.strip()) < _PDFPLUMBER_MIN_CHARS:
        full_text = _extract_text_tesseract(file_path)
        method = "tesseract"

    part_b_text = _extract_after_part_b(full_text)

    # Run all patterns and show which matched
    field_matches: dict = {}
    for field, pattern in FIELD_PATTERNS.items():
        if field.startswith("_"):
            continue
        m = pattern.search(part_b_text)
        if m:
            field_matches[field] = {"matched": True, "captured": m.group(1)}
        else:
            # Also try on full text (in case Part B slicer failed)
            m2 = pattern.search(full_text)
            if m2:
                field_matches[field] = {
                    "matched": True,
                    "captured": m2.group(1),
                    "note": "matched in FULL text, not Part B — Part B slicer may be wrong",
                }
            else:
                field_matches[field] = {"matched": False, "captured": None}

    return JSONResponse(
        status_code=200,
        content={
            "method": method,
            "char_count": len(full_text),
            "part_b_char_count": len(part_b_text),
            # Previews — first 2000 chars so browser shows useful info
            "raw_text_preview": full_text[:2000],
            "part_b_text_preview": part_b_text[:2000],
            "field_matches": field_matches,
        },
    )
