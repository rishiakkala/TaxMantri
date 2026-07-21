import pytest
from fastapi.testclient import TestClient
from backend.agents.evaluator_agent.routes.tax_regime_comparison import router
from unittest.mock import patch

client = TestClient(router)

@pytest.mark.asyncio
async def test_compare_tax_regimes_success():
    with patch('backend.agents.evaluator_agent.services.tax_calculator.calculate_tax_regimes', return_value={"old_regime": {}, "new_regime": {}}):
        response = client.post("/compare-tax-regimes", json={"financial_data": {}})
        assert response.status_code == 200
        assert response.json() == {"old_regime": {}, "new_regime": {}}

@pytest.mark.asyncio
async def test_compare_tax_regimes_error():
    with patch('backend.agents.evaluator_agent.services.tax_calculator.calculate_tax_regimes', side_effect=Exception("Calculation error")):
        response = client.post("/compare-tax-regimes", json={"financial_data": {}})
        assert response.status_code == 500
        assert response.json() == {"detail": "Error calculating tax regimes: Calculation error"}