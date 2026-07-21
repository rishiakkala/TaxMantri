from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from backend.agents.evaluator_agent.services.tax_calculator import calculate_tax_regimes
from backend.models.schemas import TaxComparisonSchema

router = APIRouter()

class TaxInput(BaseModel):
    financial_data: dict = Field(..., description="User's financial data")

@router.post("/compare-tax-regimes", response_model=TaxComparisonSchema)
async def compare_tax_regimes(tax_input: TaxInput):
    """
    Endpoint to calculate and compare tax summaries for old and new regimes.
    """
    try:
        comparison_results = await calculate_tax_regimes(tax_input.dict())
        return comparison_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating tax regimes: {str(e)}")