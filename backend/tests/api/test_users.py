import pytest
from models.user import User, UserRole
from main import app
from core.security import get_current_user

@pytest.fixture
def auth_client(client):
    def override_get_current_user():
        return User(id=1, email="user@test.com", name="Test", role=UserRole.customer, hashed_password="pw", phone="1234567")
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)

def test_read_user_me(auth_client):
    response = auth_client.get("/api/users/me")
    assert response.status_code == 200
    assert response.json()["email"] == "user@test.com"

def test_update_user_me(auth_client, mock_db_session):
    def mock_refresh(obj):
        pass
    mock_db_session.refresh.side_effect = mock_refresh
    
    response = auth_client.put("/api/users/me", json={"name": "New Name", "phone": "+098765432"})
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["phone"] == "+098765432"

def test_update_user_me_forbidden_fields(auth_client, mock_db_session):
    def mock_refresh(obj):
        pass
    mock_db_session.refresh.side_effect = mock_refresh

    # Using the exact same enum value for Customer just to be safe, but passing it as string
    response = auth_client.put("/api/users/me", json={"role": "Manager", "is_active": False})
    assert response.status_code == 200
    # The role should still be the original one, because we ignore role updates in the endpoint logic
    assert response.json()["role"] == "Customer"
