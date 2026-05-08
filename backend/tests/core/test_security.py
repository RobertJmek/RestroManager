import pytest
from datetime import timedelta
from fastapi import HTTPException
import jwt

from core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    get_current_guest,
    require_role
)
from core.config import settings
from models.user import User, UserRole

def test_password_hashing():
    password = "supersecretpassword"
    hashed = get_password_hash(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

def test_create_access_token():
    data = {"sub": "test@example.com", "role": "Waiter"}
    token = create_access_token(data, expires_delta=timedelta(minutes=15))
    
    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    
    assert decoded["sub"] == "test@example.com"
    assert decoded["role"] == "Waiter"
    assert "exp" in decoded

@pytest.mark.asyncio
async def test_get_current_user_valid_token(mock_db_session):
    # Setup mock user in DB
    mock_user = User(id=1, email="test@example.com", phone="1234567890", name="Test User", hashed_password="pw", role=UserRole.waiter)
    
    # Configure mock session to return the user
    mock_db_session.exec.return_value.first.return_value = mock_user
    
    # Create valid token
    token = create_access_token({"sub": "test@example.com", "role": "Waiter"})
    
    user = await get_current_user(token=token, session=mock_db_session)
    
    assert user.email == "test@example.com"
    assert user.role == UserRole.waiter

@pytest.mark.asyncio
async def test_get_current_user_invalid_token(mock_db_session):
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token="invalid.token.str", session=mock_db_session)
        
    assert exc_info.value.status_code == 401

@pytest.mark.asyncio
async def test_get_current_user_not_found(mock_db_session):
    # Configure mock session to return None
    mock_db_session.exec.return_value.first.return_value = None
    
    token = create_access_token({"sub": "unknown@example.com", "role": "Waiter"})
    
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token=token, session=mock_db_session)
        
    assert exc_info.value.status_code == 401

@pytest.mark.asyncio
async def test_get_current_guest_valid_token():
    token = create_access_token({"role": "Guest", "table_id": 5})
    
    token_data = await get_current_guest(token=token)
    assert token_data.role == "Guest"
    assert token_data.table_id == 5

@pytest.mark.asyncio
async def test_get_current_guest_invalid_role():
    token = create_access_token({"role": "Waiter", "table_id": 5})
    
    with pytest.raises(HTTPException) as exc_info:
        await get_current_guest(token=token)
        
    assert exc_info.value.status_code == 401

@pytest.mark.asyncio
async def test_require_role():
    role_checker = require_role(["Manager"])
    
    manager_user = User(id=1, email="admin@example.com", phone="1234567890", name="Manager", hashed_password="pw", role=UserRole.manager)
    waiter_user = User(id=2, email="waiter@example.com", phone="0987654321", name="Waiter", hashed_password="pw", role=UserRole.waiter)
    
    # Should pass
    result = role_checker(current_user=manager_user)
    assert result == manager_user
    
    # Should raise 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        role_checker(current_user=waiter_user)
        
    assert exc_info.value.status_code == 403
