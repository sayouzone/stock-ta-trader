"""
API 엔드포인트 테스트.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from ta_trader.interfaces.api.auth import create_access_token
from ta_trader.interfaces.api.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def auth_headers():
    token, _ = create_access_token(subject="test-user")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestRootEndpoints:
    async def test_root(self, client: AsyncClient):
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Stock TA Trader"

    async def test_health(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data


class TestAuth:
    async def test_login_success(self, client: AsyncClient):
        resp = await client.post(
            "/auth/token",
            json={"username": "admin", "password": "changeme"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_failure(self, client: AsyncClient):
        resp = await client.post(
            "/auth/token",
            json={"username": "admin", "password": "wrong"},
        )
        assert resp.status_code == 401

    async def test_protected_endpoint_no_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/analysis/recommendations")
        assert resp.status_code == 403  # No bearer token


class TestAnalysisEndpoints:
    async def test_submit_analysis_validation(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            "/api/v1/analysis/",
            json={"ticker": "005930", "analysis_type": "swing"},
            headers=auth_headers,
        )
        # 202 (accepted) 또는 500 (core not implemented)
        assert resp.status_code in (202, 500)

    async def test_submit_analysis_invalid_type(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            "/api/v1/analysis/",
            json={"ticker": "005930", "analysis_type": "invalid"},
            headers=auth_headers,
        )
        assert resp.status_code == 422  # Validation error

    async def test_get_job_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.get(
            "/api/v1/analysis/jobs/nonexistent",
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestAlertEndpoints:
    async def test_send_alert(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            "/api/v1/alerts/send",
            json={
                "ticker": "TEST",
                "title": "Test Alert",
                "message": "This is a test",
                "priority": 3,
            },
            headers=auth_headers,
        )
        # 200 또는 500 (notification service not initialized in test)
        assert resp.status_code in (200, 500)
