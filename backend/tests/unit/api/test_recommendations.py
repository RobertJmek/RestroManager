"""
Tests for AI Recommendation Agent API endpoints.
Covers: valid guest token access, invalid/absent token rejection,
and fallback behavior when AI is disabled/unconfigured.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app
from core.security import create_access_token
from db.session import get_session
from core.ai import clear_chat_session


# Helper to create a guest token
def create_guest_token(table_id: int = 1):
    token = create_access_token(
        data={"role": "Guest", "table_id": table_id}
    )
    return token


# Helper to create a staff token
def create_staff_token(email: str, role: str):
    token = create_access_token(
        data={"sub": email, "role": role, "user_id": 1, "name": "Test User"}
    )
    return token


@pytest.fixture
def client_with_db(session):
    """Test client with real database session."""
    app.dependency_overrides[get_session] = lambda: session
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestRecommendationsAuth:
    """Test authentication/authorization for recommendations endpoints."""

    def test_chat_valid_guest_token(self, client_with_db):
        """Valid guest token should access recommendations with fallback (no AI configured)."""
        token = create_guest_token(table_id=1)

        # Forțăm fallback-ul explicit ca testul să fie determinist indiferent dacă
        # mediul local are DEEPSEEK_API_KEY setat în .env.
        with patch("core.ai.settings.USE_AI_RECOMMENDATIONS", False):
            response = client_with_db.post(
                "/api/recommendations/chat",
                json={"message": "I want something spicy"},
                headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "response_text" in data
        assert "suggested_dishes" in data
        assert "session_id" in data
        # Should use fallback agent when AI not configured
        assert data["agent"] == "fallback"

    def test_chat_valid_waiter_token(self, client_with_db):
        """Valid staff token should also access recommendations."""
        token = create_staff_token("waiter@test.com", "Waiter")
        
        response = client_with_db.post(
            "/api/recommendations/chat",
            json={"message": "Recommend a dish"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "response_text" in data
        assert "suggested_dishes" in data

    def test_chat_no_token_401(self, client_with_db):
        """No Authorization header should return 401."""
        response = client_with_db.post(
            "/api/recommendations/chat",
            json={"message": "I want something"}
        )
        
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]

    def test_chat_invalid_token_401(self, client_with_db):
        """Invalid/malformed token should return 401."""
        response = client_with_db.post(
            "/api/recommendations/chat",
            json={"message": "I want something"},
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        
        assert response.status_code == 401
        assert "Invalid authentication" in response.json()["detail"]

    def test_chat_clear_no_token_401(self, client_with_db):
        """Clear chat endpoint also requires authentication."""
        response = client_with_db.post(
            "/api/recommendations/chat/clear",
            json={"session_id": "test-session-123"}
        )
        
        assert response.status_code == 401

    def test_chat_clear_valid_token(self, client_with_db):
        """Clear chat with valid token should work."""
        token = create_guest_token(table_id=1)
        
        response = client_with_db.post(
            "/api/recommendations/chat/clear",
            json={"session_id": "test-session-123"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "cleared"


class TestRecommendationsFallback:
    """Test fallback behavior when AI is disabled or unconfigured."""

    def test_chat_fallback_when_ai_disabled(self, client_with_db):
        """When USE_AI_RECOMMENDATIONS=False, should use fallback."""
        token = create_guest_token(table_id=1)
        
        with patch("core.ai.settings.USE_AI_RECOMMENDATIONS", False):
            response = client_with_db.post(
                "/api/recommendations/chat",
                json={"message": "I want vegan food"},
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["agent"] == "fallback"
            assert len(data["suggested_dishes"]) > 0

    def test_chat_fallback_when_no_api_key(self, client_with_db):
        """When DEEPSEEK_API_KEY is missing, should use fallback."""
        token = create_guest_token(table_id=1)
        
        with patch("core.ai.settings.DEEPSEEK_API_KEY", None):
            response = client_with_db.post(
                "/api/recommendations/chat",
                json={"message": "Something sweet"},
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["agent"] == "fallback"

    def test_chat_session_persistence(self, client_with_db):
        """Session ID should persist across requests."""
        token = create_guest_token(table_id=1)
        
        # First request - get session_id
        response1 = client_with_db.post(
            "/api/recommendations/chat",
            json={"message": "Hello"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response1.status_code == 200
        session_id = response1.json()["session_id"]
        
        # Second request with same session_id
        response2 = client_with_db.post(
            "/api/recommendations/chat",
            json={"message": "What about drinks?", "session_id": session_id},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id

    def test_chat_clear_removes_session(self, client_with_db):
        """Clear chat should remove session history."""
        token = create_guest_token(table_id=1)
        
        # Create a session
        response1 = client_with_db.post(
            "/api/recommendations/chat",
            json={"message": "Test message"},
            headers={"Authorization": f"Bearer {token}"}
        )
        session_id = response1.json()["session_id"]
        
        # Clear the session
        clear_response = client_with_db.post(
            "/api/recommendations/chat/clear",
            json={"session_id": session_id},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert clear_response.status_code == 200


class TestRecommendationsResponseFormat:
    """Test response format and content structure."""

    def test_chat_response_structure(self, client_with_db):
        """Response should have all required fields."""
        token = create_guest_token(table_id=1)
        
        response = client_with_db.post(
            "/api/recommendations/chat",
            json={"message": "Recommend something"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check all required fields
        assert "response_text" in data
        assert "suggested_dishes" in data
        assert "follow_up_question" in data
        assert "session_id" in data
        assert "agent" in data
        
        # Check suggested_dishes structure
        assert isinstance(data["suggested_dishes"], list)
        for dish in data["suggested_dishes"]:
            assert "item_id" in dish
            assert "name" in dish
            assert "reasoning" in dish
            assert "price" in dish
