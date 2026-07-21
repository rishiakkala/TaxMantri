import pytest
from fastapi.testclient import TestClient
from backend.agents.matcher_agent.routes.tax_insights import router

client = TestClient(router)

@pytest.mark.parametrize("question, financial_data, expected_status", [
    ("What are the tax benefits?", {}, 200),
    ("", {}, 422),
])
def test_generate_tax_insights(question, financial_data, expected_status):
    response = client.post("/generate-tax-insights", json={'question': question, 'financial_data': financial_data})
    assert response.status_code == expected_status