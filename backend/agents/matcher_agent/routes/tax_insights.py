from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from backend.agents.matcher_agent.services.llm_service import generate_tax_insights
from backend.models.schemas import TaxInsightSchema

router = APIRouter()

class TaxInsightRequest(BaseModel):
    question: str = Field(..., description="User's question about tax insights")
    financial_data: dict = Field(..., description="User's financial data")

@router.post("/generate-tax-insights", response_model=TaxInsightSchema)
async def generate_tax_insights_endpoint(request: TaxInsightRequest):
    """
    Endpoint to generate contextual tax insights using LLMs.
    """
    try:
        insights = await generate_tax_insights(request.question, request.financial_data)
        return insights
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating tax insights: {str(e)}")