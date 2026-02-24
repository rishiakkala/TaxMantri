"""
ocr_tools.py — LangChain tool wrapping the OCR service for Form 16 extraction.

Tools:
  ocr_extract_tool  — extracts financial fields from a Form 16 PDF/image
"""
from __future__ import annotations

import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def ocr_extract_tool(file_path: str) -> dict:
    """
    Extracts financial fields from a Form 16 PDF or image using OCR.

    Uses pdfplumber for text-based PDFs and Tesseract for scanned images.
    Returns per-field confidence indicators: green (high), yellow (medium), red (failed).

    Args:
        file_path: Absolute path to the Form 16 PDF, JPEG, or PNG file.

    Returns:
        dict with keys:
          - success (bool): True if OCR completed (even if some fields are red)
          - extracted_fields (dict): {field_name: {value, confidence}} for all fields
          - profile_fields (dict): Subset with non-None values only (mergeable with profile)
          - reference_fields (dict): gross_total_income, tds_deducted (display only)
          - summary (dict): {field_count, green_count, yellow_count, red_count}
          - warnings (list[dict]): Non-fatal warnings (e.g., wrong assessment year)
          - error (str | None): Error message if OCR completely failed
    """
    from backend.agents.input_agent.ocr_service import extract_form16

    try:
        result = extract_form16(file_path)
        logger.info(
            "OCR complete green=%d yellow=%d red=%d",
            result.summary.green_count,
            result.summary.yellow_count,
            result.summary.red_count,
        )
        return {
            "success": True,
            "extracted_fields": {
                k: v.model_dump() for k, v in result.extracted_fields.items()
            },
            "profile_fields": result.profile_fields,
            "reference_fields": result.reference_fields,
            "summary": result.summary.model_dump(),
            "warnings": [w.model_dump() for w in result.warnings],
            "error": None,
        }
    except Exception as exc:
        logger.error("OCR extraction failed: %s", exc)
        return {
            "success": False,
            "extracted_fields": {},
            "profile_fields": {},
            "reference_fields": {},
            "summary": {"field_count": 0, "green_count": 0, "yellow_count": 0, "red_count": 0},
            "warnings": [],
            "error": str(exc),
        }
