"""
input_agent.py — InputAgent LangGraph node.

Responsibility: Capture + Validate + Structure

The InputAgent is the entry point of the TaxMantri pipeline. It decides:
  Mode A (profile_id in state): Load pre-confirmed profile from DB — no re-validation.
  Mode B (manual/ocr raw_input): validate_profile_tool → structure_profile_tool
  Mode C (ocr file_path): ocr_extract_tool → merge → validate → structure

On success, writes `profile` and `profile_dict` to state and routes to MatcherAgent.
On failure, writes `input_errors` and sets `should_stop = True`, ending the graph.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from backend.graph.state import TaxMantriState

logger = logging.getLogger(__name__)


async def input_agent_node(state: TaxMantriState) -> dict:
    """
    InputAgent node — loads or validates/structures the incoming financial profile.

    Mode A — profile_id present: load stored confirmed profile from DB.
    Mode B — manual input: validate + structure from raw_input.
    Mode C — ocr input: extract → merge → validate → structure.
    """
    from backend.agents.input_agent.schemas import UserFinancialProfile
    from backend.graph.tools.profile_tools import validate_profile_tool, structure_profile_tool
    from backend.graph.tools.ocr_tools import ocr_extract_tool

    input_method: str = state.get("input_method", "manual")
    file_path: str | None = state.get("file_path")
    profile_id: str | None = state.get("profile_id")

    # -------------------------------------------------------------------------
    # Mode A: Load a pre-confirmed profile from DB by profile_id (skip re-validation)
    # This is the standard path when called from POST /api/calculate with profile_id.
    # -------------------------------------------------------------------------
    if profile_id:
        logger.info("InputAgent Mode A — loading stored profile_id=%s", profile_id)
        try:
            from backend.database import AsyncSessionLocal
            from backend.store import get_profile

            async with AsyncSessionLocal() as db:
                profile_obj = await get_profile(db, profile_id)

            if profile_obj is None:
                error_msg = f"Profile '{profile_id}' not found in database."
                logger.error(error_msg)
                return {
                    "input_errors": [error_msg],
                    "input_confidence": 0.0,
                    "should_stop": True,
                    "current_agent": "input",
                }

            profile_dict = profile_obj.model_dump()
            logger.info(
                "InputAgent Mode A success profile_id=%s basic_salary=%.0f",
                profile_obj.profile_id,
                profile_obj.basic_salary,
            )
            return {
                "profile": profile_obj,
                "profile_dict": profile_dict,
                "input_errors": [],
                "input_confidence": 1.0,
                "should_stop": False,
                "current_agent": "input",
            }

        except Exception as exc:
            error_msg = f"Failed to load profile from database: {exc}"
            logger.error(error_msg)
            return {
                "input_errors": [error_msg],
                "input_confidence": 0.0,
                "should_stop": True,
                "current_agent": "input",
            }

    # -------------------------------------------------------------------------
    # Mode C: OCR path — extract from Form 16 PDF, then merge with raw_input
    # -------------------------------------------------------------------------
    raw_input: dict = state.get("raw_input", {})

    if input_method == "ocr" and file_path:
        logger.info("InputAgent Mode C — OCR extraction from %s", file_path)
        ocr_result = ocr_extract_tool.invoke({"file_path": file_path})

        if not ocr_result.get("success"):
            error_msg = f"OCR extraction failed: {ocr_result.get('error', 'Unknown error')}"
            logger.error(error_msg)
            return {
                "input_errors": [error_msg],
                "input_confidence": 0.0,
                "should_stop": True,
                "current_agent": "input",
            }

        ocr_fields = ocr_result.get("profile_fields", {})
        merged = {**ocr_fields, **raw_input, "input_method": "ocr"}
    else:
        # -------------------------------------------------------------------------
        # Mode B: Manual input — use raw_input directly
        # -------------------------------------------------------------------------
        logger.info("InputAgent Mode B — manual input validation")
        merged = {**raw_input, "input_method": input_method or "manual"}

    # -------------------------------------------------------------------------
    # Validate the merged data
    # -------------------------------------------------------------------------
    logger.info("InputAgent validating profile data")
    validation_result = validate_profile_tool.invoke({"profile_data": merged})

    if not validation_result.get("is_valid"):
        errors = validation_result.get("errors", ["Validation failed"])
        logger.warning("InputAgent validation failed: %s", errors)
        return {
            "input_errors": errors,
            "input_confidence": 0.0,
            "should_stop": True,
            "current_agent": "input",
        }

    # -------------------------------------------------------------------------
    # Structure the validated profile
    # -------------------------------------------------------------------------
    structure_result = structure_profile_tool.invoke({"profile_data": validation_result["profile"]})

    if not structure_result.get("success"):
        error_msg = structure_result.get("error", "Failed to structure profile")
        return {
            "input_errors": [error_msg],
            "input_confidence": 0.0,
            "should_stop": True,
            "current_agent": "input",
        }

    profile_dict = structure_result["profile"]
    profile_obj = UserFinancialProfile.model_validate(profile_dict)

    logger.info(
        "InputAgent success profile_id=%s basic_salary=%.0f",
        profile_obj.profile_id,
        profile_obj.basic_salary,
    )

    return {
        "profile": profile_obj,
        "profile_dict": profile_dict,
        "input_errors": [],
        "input_confidence": 1.0,
        "should_stop": False,
        "current_agent": "input",
    }


def route_after_input(state: TaxMantriState) -> str:
    """
    Routing function after InputAgent.
    Returns "error" if should_stop is True, else "matcher".
    """
    if state.get("should_stop"):
        return "error"
    return "matcher"
