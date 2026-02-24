"""
input_agent.py — InputAgent LangGraph node.

Responsibility: Capture + Validate + Structure

The InputAgent is the entry point of the TaxMantri pipeline. It decides:
  1. For "manual" input: calls validate_profile_tool → structure_profile_tool
  2. For "ocr" input: calls ocr_extract_tool → merges with user edits → validate → structure

On success, writes `profile` and `profile_dict` to state and routes to MatcherAgent.
On failure, writes `input_errors` and sets `should_stop = True`, ending the graph.

LLM usage: Uses Mistral to intelligently decide on data merging strategy and
generate meaningful error messages — NOT for tax computation.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mistralai import ChatMistralAI

from backend.graph.state import TaxMantriState

logger = logging.getLogger(__name__)

# System prompt for InputAgent's LLM decision-making
INPUT_AGENT_SYSTEM = """You are the InputAgent for TaxMantri, an Indian tax filing assistant.
Your job is to validate, clean, and structure taxpayer financial data.

When given financial data, you must:
1. Call validate_profile_tool to check for errors
2. If valid, call structure_profile_tool to finalize the structured profile
3. If invalid, report exactly which fields failed and why

You are precise, never guess or fill in missing required fields. 
Required fields: basic_salary, city_type, age_bracket, input_method.
"""


async def input_agent_node(state: TaxMantriState) -> dict:
    """
    InputAgent node — validates and structures the incoming financial profile.

    Reads:
      state["raw_input"]    — raw dict from the API request
      state["input_method"] — "manual" | "ocr"
      state["file_path"]    — temp file path for OCR (None for manual)

    Writes:
      state["profile"]         — UserFinancialProfile instance
      state["profile_dict"]    — profile as dict for downstream tools
      state["input_errors"]    — list of validation errors (empty if success)
      state["input_confidence"]— 1.0 if valid, 0.0 if not
      state["should_stop"]     — True if validation failed
      state["current_agent"]   — "input"
    """
    from backend.graph.tools.profile_tools import validate_profile_tool, structure_profile_tool
    from backend.graph.tools.ocr_tools import ocr_extract_tool
    from backend.agents.input_agent.schemas import UserFinancialProfile
    from backend.graph.graph import get_mistral_client, get_llm

    logger.info("InputAgent starting input_method=%s", state.get("input_method", "manual"))

    raw_input: dict = state.get("raw_input", {})
    input_method: str = state.get("input_method", "manual")
    file_path: str | None = state.get("file_path")

    # -------------------------------------------------------------------------
    # Step 1: OCR path — extract fields from Form 16, then merge with raw_input
    # -------------------------------------------------------------------------
    if input_method == "ocr" and file_path:
        logger.info("InputAgent running OCR on %s", file_path)
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

        # Merge OCR profile_fields with any user-provided overrides in raw_input
        ocr_fields = ocr_result.get("profile_fields", {})
        merged = {**ocr_fields, **raw_input, "input_method": "ocr"}
    else:
        # Manual input — use raw_input directly
        merged = {**raw_input, "input_method": input_method or "manual"}

    # -------------------------------------------------------------------------
    # Step 2: Validate the merged data
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
    # Step 3: Structure the validated profile
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

    # Reconstruct the actual Pydantic object for downstream use
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
