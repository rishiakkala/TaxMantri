import pytest
from fastapi.testclient import TestClient
from backend.agents.matcher_agent.routes.tax_insights import router
from unittest.mock import patch

client = TestClient(router)

@pytest.mark.asyncio
async def test_generate_tax_insights_success():
    with patch('backend.agents.matcher_agent.services.llm_service.generate_tax_insights', return_value={"insights": "Tax insights"}):
        response = client.post("/generate-tax-insights", json={"question": "What are my deductions?", "financial_data": {}})
        assert response.status_code == 200
        assert response.json() == {"insights": "Tax insights"}

@pytest.mark.asyncio
async def test_generate_tax_insights_error():
    with patch('backend.agents.matcher_agent.services.llm_service.generate_tax_insights', side_effect=Exception("Insight generation error")):
        response = client.post("/generate-tax-insights", json={"question": "What are my deductions?", "financial_data": {}})
        assert response.status_code == 500
        assert response.json() == {"detail": "Error generating tax insights: Insight generation error"}