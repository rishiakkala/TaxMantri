import pytest
from fastapi.testclient import TestClient
from backend.auth.routes.user_profile import router
from unittest.mock import patch

client = TestClient(router)

@pytest.mark.asyncio
async def test_get_user_profile_success():
    with patch('backend.models.database.get_user_profile', return_value={"id": "user123", "personal_details": {}, "financial_details": {}}):
        response = client.get("/user-profile/user123")
        assert response.status_code == 200
        assert response.json() == {"id": "user123", "personal_details": {}, "financial_details": {}}

@pytest.mark.asyncio
async def test_get_user_profile_error():
    with patch('backend.models.database.get_user_profile', side_effect=Exception("Fetch error")):
        response = client.get("/user-profile/user123")
        assert response.status_code == 500
        assert response.json() == {"detail": "Error fetching user profile: Fetch error"}

@pytest.mark.asyncio
async def test_update_user_profile_success():
    with patch('backend.models.database.update_user_profile', return_value={"id": "user123", "personal_details": {}, "financial_details": {}}):
        response = client.put("/user-profile/user123", json={"personal_details": {}, "financial_details": {}})
        assert response.status_code == 200
        assert response.json() == {"id": "user123", "personal_details": {}, "financial_details": {}}

@pytest.mark.asyncio
async def test_update_user_profile_error():
    with patch('backend.models.database.update_user_profile', side_effect=Exception("Update error")):
        response = client.put("/user-profile/user123", json={"personal_details": {}, "financial_details": {}})
        assert response.status_code == 500
        assert response.json() == {"detail": "Error updating user profile: Update error"}