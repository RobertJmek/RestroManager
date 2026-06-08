"""
Tests for the Manager Analytics (insights) AI agent endpoints.
Covers: Manager-only access, rejection of other roles / no token,
fallback response shape (no AI configured), and the clear endpoint.
"""

import pytest
from unittest.mock import patch
from main import app
from models.user import User, UserRole
from core.security import get_current_user


@pytest.fixture
def manager_client(client):
    """client (real SQLite session) + authenticated Manager."""
    def override_get_current_user():
        return User(id=1, email="manager@test.com", name="Mgr", role=UserRole.manager,
                    hashed_password="pw", phone="22233344")
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def waiter_client(client):
    def override_get_current_user():
        return User(id=2, email="waiter@test.com", name="Wtr", role=UserRole.waiter,
                    hashed_password="pw", phone="33344455")
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


class TestInsightsAuth:
    def test_chat_requires_token(self, client):
        resp = client.post("/api/insights/chat", json={"message": "Cum merg vânzările?"})
        assert resp.status_code == 401

    def test_chat_rejects_non_manager(self, waiter_client):
        resp = waiter_client.post("/api/insights/chat", json={"message": "Raport?"})
        assert resp.status_code == 403

    def test_clear_rejects_non_manager(self, waiter_client):
        resp = waiter_client.post("/api/insights/chat/clear", json={"session_id": "x"})
        assert resp.status_code == 403


class TestInsightsFallback:
    def test_chat_fallback_shape(self, manager_client):
        """Empty DB + no AI key → deterministic fallback over zeroed report."""
        with patch("core.ai.settings.DEEPSEEK_API_KEY", None):
            resp = manager_client.post(
                "/api/insights/chat",
                json={"message": "Rezumă perioada", "start_date": "2026-05-01", "end_date": "2026-05-07"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent"] == "fallback"
        assert "response_text" in data
        assert isinstance(data["insights"], list)
        assert data["session_id"]  # auto-generated when absent

    def test_chat_preserves_session_id(self, manager_client):
        with patch("core.ai.settings.DEEPSEEK_API_KEY", None):
            resp = manager_client.post(
                "/api/insights/chat",
                json={"message": "Salut", "session_id": "fixed-session"},
            )
        assert resp.status_code == 200
        assert resp.json()["session_id"] == "fixed-session"

    def test_clear_session(self, manager_client):
        resp = manager_client.post("/api/insights/chat/clear", json={"session_id": "abc"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "cleared"

    def test_chat_invalid_date_422(self, manager_client):
        with patch("core.ai.settings.DEEPSEEK_API_KEY", None):
            resp = manager_client.post(
                "/api/insights/chat",
                json={"message": "x", "start_date": "not-a-date"},
            )
        assert resp.status_code == 422
