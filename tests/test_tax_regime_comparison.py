import pytest
from fastapi.testclient import TestClient
from backend.agents.evaluator_agent.routes.tax_regime_comparison import router

client = TestClient(router)

@pytest.mark.parametrize("financial_data, expected_status", [
    ({}, 200),
    ({'income': 'invalid'}, 422),
])
def test_compare_tax_regimes(financial_data, expected_status):
    response = client.post("/compare-tax-regimes", json={'financial_data': financial_data})
    assert response.status_code == expected_status