import pytest
from fastapi.testclient import TestClient
from backend.agents.input_agent.routes.tax_data_input import router
from unittest.mock import patch

client = TestClient(router)

@pytest.mark.asyncio
async def test_upload_tax_documents_success():
    with patch('backend.agents.input_agent.services.ocr_service.process_ocr', return_value={"Income": 10000, "Tax Paid": 1000}):
        response = client.post("/upload-tax-documents", files={"files": ("test.pdf", b"test content")}, data={"user_id": "user123"})
        assert response.status_code == 200
        assert response.json() == {"user_id": "user123", "ocr_results": {"Income": 10000, "Tax Paid": 1000}}

@pytest.mark.asyncio
async def test_upload_tax_documents_no_files():
    response = client.post("/upload-tax-documents", data={"user_id": "user123"})
    assert response.status_code == 400
    assert response.json() == {"detail": "No files uploaded."}

@pytest.mark.asyncio
async def test_upload_tax_documents_ocr_error():
    with patch('backend.agents.input_agent.services.ocr_service.process_ocr', side_effect=Exception("OCR error")):
        response = client.post("/upload-tax-documents", files={"files": ("test.pdf", b"test content")}, data={"user_id": "user123"})
        assert response.status_code == 500
        assert response.json() == {"detail": "Error processing OCR: OCR error"}

@pytest.mark.asyncio
async def test_submit_tax_data_success():
    with patch('backend.models.database.save_tax_data', return_value={"status": "success"}):
        response = client.post("/submit-tax-data", json={"financial_data": {}, "ocr_results": {}}, data={"user_id": "user123"})
        assert response.status_code == 200
        assert response.json() == {"status": "success"}

@pytest.mark.asyncio
async def test_submit_tax_data_error():
    with patch('backend.models.database.save_tax_data', side_effect=Exception("Save error")):
        response = client.post("/submit-tax-data", json={"financial_data": {}, "ocr_results": {}}, data={"user_id": "user123"})
        assert response.status_code == 500
        assert response.json() == {"detail": "Error saving tax data: Save error"}