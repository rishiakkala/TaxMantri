import pytest
from fastapi.testclient import TestClient
from backend.auth.routes.user_profile import router

client = TestClient(router)

@pytest.mark.parametrize("user_id, expected_status", [
    ("user123", 200),
    ("invalid_user", 404),
])
def test_get_user_profile(user_id, expected_status):
    response = client.get(f"/user-profile/{user_id}")
    assert response.status_code == expected_status

@pytest.mark.parametrize("profile_update, user_id, expected_status", [
    ({'personal_details': {}, 'financial_details': {}}, 'user123', 200),
    ({'personal_details': None, 'financial_details': {}}, 'user123', 422),
])
def test_update_user_profile(profile_update, user_id, expected_status):
    response = client.put(f"/user-profile/{user_id}", json=profile_update)
    assert response.status_code == expected_status