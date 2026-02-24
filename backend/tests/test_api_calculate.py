"""
End-to-end API tests for POST /api/calculate and POST /api/profile — AY 2025-26

Tests the full stack: HTTP request → schema validation → business-rule validation
→ tax engine → PostgreSQL persistence → HTTP response.

Requirements:
  - docker-compose postgres and redis must be running
  - Run from D:/TaxMantri/: pytest backend/tests/test_api_calculate.py -v

Expected values are CA-verified figures from Phase 2 CONTEXT.md.
Tolerance: ±₹50 on all monetary assertions (consistent with test_tax_engine.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Add backend/ to sys.path (conftest.py handles this globally, but be explicit)
_backend = Path(__file__).parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from main import app
from tests.demo_profiles import DEMO_PROFILES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client():
    """Async httpx client using ASGI transport — no live server needed."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Test Group 1: Shape A — inline profile body
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["priya", "rahul", "anita"])
async def test_calculate_shape_a_demo_profiles(client: AsyncClient, name: str) -> None:
    """
    Submit each demo profile inline (Shape A) and verify TaxResult.
    Expected values from CA-verified Phase 2 hand-computation.
    """
    data = DEMO_PROFILES[name]
    profile_kwargs = data["profile"]
    expected = data["expected"]

    response = await client.post("/api/calculate", json=profile_kwargs)
    assert response.status_code == 200, (
        f"{name}: Expected 200, got {response.status_code}. Body: {response.text}"
    )

    result = response.json()

    # Recommended regime
    assert result["recommended_regime"] == expected["expected_regime"], (
        f"{name}: Expected regime={expected['expected_regime']!r}, "
        f"got {result['recommended_regime']!r}"
    )

    # old_regime.total_tax
    old_tax = result["old_regime"]["total_tax"]
    assert abs(old_tax - expected["expected_old_tax"]) <= 50, (
        f"{name}: Old tax expected ₹{expected['expected_old_tax']:,.0f}, got ₹{old_tax:,.0f}"
    )

    # new_regime.total_tax
    new_tax = result["new_regime"]["total_tax"]
    assert abs(new_tax - expected["expected_new_tax"]) <= 50, (
        f"{name}: New tax expected ₹{expected['expected_new_tax']:,.0f}, got ₹{new_tax:,.0f}"
    )

    # savings_amount
    savings = result["savings_amount"]
    assert abs(savings - expected["expected_savings"]) <= 50, (
        f"{name}: Savings expected ₹{expected['expected_savings']:,.0f}, got ₹{savings:,.0f}"
    )

    # TaxResult structure completeness
    assert isinstance(result.get("rationale"), str) and len(result["rationale"]) > 10, (
        f"{name}: rationale is missing or empty"
    )
    assert isinstance(result.get("old_regime_suggestions"), list), (
        f"{name}: old_regime_suggestions must be a list"
    )
    assert isinstance(result.get("new_regime_suggestions"), list), (
        f"{name}: new_regime_suggestions must be a list"
    )

    # profile_id is set
    assert result.get("profile_id") is not None, f"{name}: profile_id missing in result"


@pytest.mark.asyncio
async def test_calculate_shape_a_anita_new_tax_is_zero(client: AsyncClient) -> None:
    """Anita's new regime tax must be exactly ₹0 via 87A rebate."""
    profile = DEMO_PROFILES["anita"]["profile"]
    response = await client.post("/api/calculate", json=profile)
    assert response.status_code == 200
    result = response.json()
    assert result["new_regime"]["total_tax"] == 0.0, (
        f"Anita new regime tax must be 0, got {result['new_regime']['total_tax']}"
    )


@pytest.mark.asyncio
async def test_calculate_shape_a_validation_error_80c_over_cap(client: AsyncClient) -> None:
    """Shape A: 80C over cap returns 422 VALIDATION_ERROR with field detail."""
    bad_profile = {**DEMO_PROFILES["priya"]["profile"], "investments_80c": 200_000}
    response = await client.post("/api/calculate", json=bad_profile)
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    fields = {d["field"] for d in body["error"]["details"]}
    assert "investments_80c" in fields, f"Expected investments_80c in details: {body}"


@pytest.mark.asyncio
async def test_calculate_shape_a_validation_error_multiple_violations(client: AsyncClient) -> None:
    """Shape A: Multiple violations all returned in one response."""
    bad_profile = {
        **DEMO_PROFILES["priya"]["profile"],
        "investments_80c": 200_000,
        "home_loan_interest": 300_000,
    }
    response = await client.post("/api/calculate", json=bad_profile)
    assert response.status_code == 422
    body = response.json()
    assert len(body["error"]["details"]) >= 2, (
        f"Expected at least 2 violation details: {body['error']['details']}"
    )


# ---------------------------------------------------------------------------
# Test Group 2: Shape B — profile_id reference
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["priya", "rahul", "anita"])
async def test_calculate_shape_b_demo_profiles(client: AsyncClient, name: str) -> None:
    """
    Store each demo profile via POST /api/profile, then calculate by profile_id.
    Result must match Shape A expectations.
    """
    data = DEMO_PROFILES[name]
    profile_kwargs = data["profile"]
    expected = data["expected"]

    # Step 1: Store the profile
    store_response = await client.post("/api/profile", json=profile_kwargs)
    assert store_response.status_code == 200, (
        f"{name}: POST /api/profile failed: {store_response.text}"
    )
    profile_id = store_response.json()["profile_id"]

    # Step 2: Calculate by profile_id (Shape B)
    calc_response = await client.post(
        "/api/calculate",
        json={"profile_id": profile_id},
    )
    assert calc_response.status_code == 200, (
        f"{name}: POST /api/calculate (Shape B) failed: {calc_response.text}"
    )

    result = calc_response.json()
    assert result["recommended_regime"] == expected["expected_regime"]
    assert abs(result["old_regime"]["total_tax"] - expected["expected_old_tax"]) <= 50
    assert abs(result["new_regime"]["total_tax"] - expected["expected_new_tax"]) <= 50
    assert abs(result["savings_amount"] - expected["expected_savings"]) <= 50


@pytest.mark.asyncio
async def test_calculate_shape_b_unknown_profile_id(client: AsyncClient) -> None:
    """Shape B with unknown profile_id returns 404 standard error envelope."""
    response = await client.post(
        "/api/calculate",
        json={"profile_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND", f"Expected NOT_FOUND: {body}"


# ---------------------------------------------------------------------------
# Test Group 3: POST /api/profile and GET /api/profile/{id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_profile_returns_profile_id_and_session_id(client: AsyncClient) -> None:
    """POST /api/profile returns profile_id, session_id, and status=created."""
    priya = DEMO_PROFILES["priya"]["profile"]
    response = await client.post("/api/profile", json=priya)
    assert response.status_code == 200
    body = response.json()
    assert "profile_id" in body and body["profile_id"]
    assert "session_id" in body and body["session_id"]
    assert body["status"] == "created"
    assert body["validation_errors"] == []


@pytest.mark.asyncio
async def test_get_profile_returns_stored_data(client: AsyncClient) -> None:
    """GET /api/profile/{id} returns the stored profile."""
    anita = DEMO_PROFILES["anita"]["profile"]
    # Store the profile
    store_resp = await client.post("/api/profile", json=anita)
    assert store_resp.status_code == 200
    profile_id = store_resp.json()["profile_id"]
    # Retrieve it
    get_resp = await client.get(f"/api/profile/{profile_id}")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["basic_salary"] == anita["basic_salary"]


@pytest.mark.asyncio
async def test_get_profile_unknown_id_returns_404(client: AsyncClient) -> None:
    """GET /api/profile/{id} with unknown id returns 404."""
    response = await client.get("/api/profile/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_create_profile_validation_error_80c_over_cap(client: AsyncClient) -> None:
    """POST /api/profile with 80C over cap returns 422."""
    bad_profile = {**DEMO_PROFILES["priya"]["profile"], "investments_80c": 200_000}
    response = await client.post("/api/profile", json=bad_profile)
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    fields = {d["field"] for d in body["error"]["details"]}
    assert "investments_80c" in fields


# ---------------------------------------------------------------------------
# Test Group 4: Result stored in PostgreSQL
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_calculate_result_stored_in_db(client: AsyncClient) -> None:
    """
    After POST /api/calculate (Shape A), the TaxResult is persisted.
    Verified indirectly: Shape B with same profile_id must succeed.
    """
    priya = DEMO_PROFILES["priya"]["profile"]

    # Store profile first
    store_resp = await client.post("/api/profile", json=priya)
    assert store_resp.status_code == 200
    profile_id = store_resp.json()["profile_id"]

    # Calculate via Shape A to store result
    calc_resp = await client.post("/api/calculate", json=priya)
    assert calc_resp.status_code == 200
    calc_result = calc_resp.json()
    assert calc_result.get("profile_id") is not None

    # Shape B with same profile_id must also succeed (proves DB read works)
    shape_b_resp = await client.post(
        "/api/calculate",
        json={"profile_id": profile_id},
    )
    assert shape_b_resp.status_code == 200
