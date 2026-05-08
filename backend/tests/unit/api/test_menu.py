import pytest
from unittest.mock import MagicMock
from models.user import User, UserRole
from models.category import Category
from models.menu_item import MenuItem
from main import app
from core.security import get_current_user

@pytest.fixture
def auth_client(client):
    def override_get_current_user():
        return User(id=1, email="admin@test.com", name="Admin", role=UserRole.manager, hashed_password="pw", phone="12345678")
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)

def test_get_categories(client, mock_db_session):
    mock_db_session.exec.return_value.all.return_value = [
        Category(id=1, name="Drinks", description="Cold drinks")
    ]
    response = client.get("/api/categories/")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Drinks"

def test_create_category(auth_client, mock_db_session):
    mock_db_session.exec.return_value.first.return_value = None
    
    def mock_refresh(obj):
        obj.id = 1
    mock_db_session.refresh.side_effect = mock_refresh
    
    response = auth_client.post("/api/categories/", json={"name": "Food", "description": "Hot food"})
    assert response.status_code == 201
    assert response.json()["name"] == "Food"

def test_create_category_unauthorized(client):
    # Nu folosim auth_client
    response = client.post("/api/categories/", json={"name": "Food"})
    assert response.status_code == 401

def test_get_menu(client, mock_db_session):
    mock_db_session.exec.return_value.all.return_value = [
        (MenuItem(id=1, name="Burger", price=10.0, category_id=1, is_available=True), "Food")
    ]
    response = client.get("/api/menu/")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Burger"
    assert response.json()[0]["category"] == "Food"

def test_create_menu_item(auth_client, mock_db_session):
    # category check
    mock_db_session.get.return_value = Category(id=1, name="Food")
    # existing item check
    mock_db_session.exec.return_value.first.return_value = None
    
    def mock_refresh(obj):
        obj.id = 1
    mock_db_session.refresh.side_effect = mock_refresh
    
    response = auth_client.post("/api/menu/", json={
        "name": "Pizza",
        "category_id": 1,
        "price": 12.5,
        "description": "Cheese pizza"
    })
    
    assert response.status_code == 201
    assert response.json()["name"] == "Pizza"
    assert response.json()["category"] == "Food"

def test_delete_category_with_items(auth_client, mock_db_session):
    mock_db_session.get.return_value = Category(id=1, name="Food")
    # Simulate COUNT query returning 1 item in this category
    mock_db_session.exec.return_value.one.return_value = 1
    mock_db_session.exec.return_value.all.return_value = [MenuItem(id=1, name="Burger", price=10.0, category_id=1)]
    
    response = auth_client.delete("/api/categories/1")
    assert response.status_code == 400
    assert "Nu se poate șterge categoria" in response.json()["detail"]
