import pytest
from core.security import get_password_hash

def test_register_success(client, mock_db_session):
    # Setup mock returns: first for email check (None), second for phone check (None)
    mock_db_session.exec.return_value.first.side_effect = [None, None]
    
    # Mock session.refresh to set an ID on the model
    def mock_refresh(obj):
        obj.id = 1
    mock_db_session.refresh.side_effect = mock_refresh
    
    response = client.post("/api/auth/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "phone": "+12345678",
        "password": "password123"
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"
    assert data["role"] == "Customer"
    assert "hashed_password" not in data

def test_register_duplicate_email(client, mock_db_session):
    # Mocking existing user with this email
    mock_db_session.exec.return_value.first.return_value = True
    
    response = client.post("/api/auth/register", json={
        "name": "Test",
        "email": "test@example.com",
        "phone": "+12345678",
        "password": "password123"
    })
    
    assert response.status_code == 400
    assert "Acest email este deja înregistrat" in response.json()["detail"]

def test_login_success(client, mock_db_session):
    from models.user import User, UserRole
    mock_user = User(
        id=1,
        email="test@example.com",
        name="Test",
        phone="12345678",
        role=UserRole.customer,
        hashed_password=get_password_hash("password123")
    )
    mock_db_session.exec.return_value.first.return_value = mock_user
    
    # OAuth2PasswordRequestForm expects form data, not json
    response = client.post("/api/auth/login", data={
        "username": "test@example.com",
        "password": "password123"
    })
    
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_invalid_password(client, mock_db_session):
    from models.user import User, UserRole
    mock_user = User(
        id=1,
        email="test@example.com",
        name="Test",
        phone="12345678",
        role=UserRole.customer,
        hashed_password=get_password_hash("password123")
    )
    mock_db_session.exec.return_value.first.return_value = mock_user
    
    response = client.post("/api/auth/login", data={
        "username": "test@example.com",
        "password": "wrongpassword"
    })
    
    assert response.status_code == 401
    assert "Email sau parolă incorectă" in response.json()["detail"]

def test_guest_login_success(client, mock_db_session):
    from models.table import Table
    mock_table = Table(id=1, number=5, status="Available")
    mock_db_session.exec.return_value.first.return_value = mock_table
    
    response = client.post("/api/auth/guest-login/5")
    
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_guest_login_invalid_table(client, mock_db_session):
    mock_db_session.exec.return_value.first.return_value = None
    
    response = client.post("/api/auth/guest-login/99")
    
    assert response.status_code == 400
    assert "Masa specificată nu este validă" in response.json()["detail"]
