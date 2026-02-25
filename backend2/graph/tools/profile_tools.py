"""
profile_tools.py — LangChain tools wrapping InputAgent validation and structuring.

Tools:
  validate_profile_tool   — runs business-rule validation on a raw dict
  structure_profile_tool  — converts raw dict into UserFinancialProfile
"""
from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def validate_profile_tool(profile_data: dict) -> dict:
    """
    Validates a raw financial profile dictionary against TaxMantri business rules.

    Runs Pydantic structural validation and business-rule checks (cross-field
    constraints like HRA not exceeding basic salary, 80C cap, etc.).

    Args:
        profile_data: Raw dict with financial fields (basic_salary, hra_received, etc.)

    Returns:
        dict with keys:
          - is_valid (bool): True if all validations pass
          - errors (list[str]): List of human-readable error messages (empty if valid)
          - profile (dict | None): The validated profile dict if valid, else None
    """
    from pydantic import ValidationError
    from backend.agents.input_agent.schemas import UserFinancialProfile
    from backend.agents.input_agent.validator import validate_business_rules

    errors: list[str] = []

    # Step 1: Pydantic structural validation
    try:
        profile = UserFinancialProfile(**profile_data)
    except ValidationError as exc:
        for err in exc.errors():
            field = ".".join(str(loc) for loc in err["loc"] if loc != "body")
            errors.append(f"{field}: {err['msg']}" if field else err["msg"])
        return {"is_valid": False, "errors": errors, "profile": None}

    # Step 2: Business-rule validation
    try:
        validate_business_rules(profile)
    except ValueError as exc:
        try:
            violations = json.loads(str(exc))
            for v in violations:
                field = v.get("field") or ""
                issue = v.get("issue", str(exc))
                errors.append(f"{field}: {issue}".strip(": "))
        except (json.JSONDecodeError, TypeError):
            errors.append(str(exc))
        return {"is_valid": False, "errors": errors, "profile": None}

    logger.info("Profile validation passed profile_id=%s", profile.profile_id)
    return {
        "is_valid": True,
        "errors": [],
        "profile": profile.model_dump(mode="json"),
    }


@tool
def structure_profile_tool(profile_data: dict) -> dict:
    """
    Converts a raw financial data dictionary into a structured UserFinancialProfile.

    Use this AFTER validate_profile_tool confirms the data is valid.
    Generates a profile_id automatically if not provided.

    Args:
        profile_data: Validated raw dict with all required financial fields.

    Returns:
        dict with keys:
          - success (bool)
          - profile (dict): Full UserFinancialProfile as dict
          - profile_id (str): The UUID for this profile
          - error (str | None): Error message if conversion failed
    """
    from backend.agents.input_agent.schemas import UserFinancialProfile

    try:
        profile = UserFinancialProfile(**profile_data)
        return {
            "success": True,
            "profile": profile.model_dump(mode="json"),
            "profile_id": profile.profile_id,
            "error": None,
        }
    except Exception as exc:
        logger.error("structure_profile_tool failed: %s", exc)
        return {
            "success": False,
            "profile": None,
            "profile_id": None,
            "error": str(exc),
        }
