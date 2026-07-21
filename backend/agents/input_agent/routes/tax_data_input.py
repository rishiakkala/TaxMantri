from fastapi import APIRouter, HTTPException, UploadFile, Form, Depends
from pydantic import BaseModel, Field
from typing import List
from backend.agents.input_agent.services.ocr_service import process_ocr
from backend.models.schemas import TaxDocumentSchema
from backend.models.database import save_tax_data

router = APIRouter()

class TaxDataInput(BaseModel):
    financial_data: dict = Field(..., description="User's financial data")
    ocr_results: dict = Field(..., description="OCR results for uploaded documents")

@router.post("/upload-tax-documents", response_model=TaxDocumentSchema)
async def upload_tax_documents(
    files: List[UploadFile],
    user_id: str = Form(...),
):
    """
    Endpoint to upload tax-related documents and process OCR.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    try:
        ocr_results = await process_ocr(files)
        return {"user_id": user_id, "ocr_results": ocr_results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing OCR: {str(e)}")

@router.post("/submit-tax-data", response_model=TaxDocumentSchema)
async def submit_tax_data(
    tax_data: TaxDataInput, user_id: str = Form(...),
):
    """
    Endpoint to submit financial data and reviewed OCR results.
    """
    try:
        saved_data = await save_tax_data(user_id, tax_data.dict())
        return saved_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving tax data: {str(e)}")