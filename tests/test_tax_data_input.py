import pytest
from fastapi.testclient import TestClient
from backend.agents.input_agent.routes.tax_data_input import router

client = TestClient(router)

@pytest.mark.parametrize("files, user_id, expected_status", [
    ([('test.pdf', b'content')], 'user123', 200),
    ([], 'user123', 400),
])
def test_upload_tax_documents(files, user_id, expected_status):
    response = client.post("/upload-tax-documents", files=files, data={'user_id': user_id})
    assert response.status_code == expected_status

@pytest.mark.parametrize("tax_data, user_id, expected_status", [
    ({'financial_data': {}, 'ocr_results': {}}, 'user123', 200),
    ({'financial_data': {}, 'ocr_results': None}, 'user123', 422),
])
def test_submit_tax_data(tax_data, user_id, expected_status):
    response = client.post("/submit-tax-data", json=tax_data, data={'user_id': user_id})
    assert response.status_code == expected_status