import pytest
from models.user import User, UserRole
from models.table import Table, TableStatus
from models.order import Order, OrderStatus
from models.menu_item import MenuItem
from main import app
from core.security import get_current_user

@pytest.fixture
def waiter_client(client):
    def override_get_current_user():
        return User(id=2, email="waiter@test.com", name="Waiter", role=UserRole.waiter, hashed_password="pw", phone="11122233")
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)

@pytest.fixture
def manager_client(client):
    def override_get_current_user():
        return User(id=1, email="admin@test.com", name="Admin", role=UserRole.manager, hashed_password="pw", phone="22233344")
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)

@pytest.fixture
def chef_client(client):
    def override_get_current_user():
        return User(id=3, email="chef@test.com", name="Chef", role=UserRole.chef, hashed_password="pw", phone="55566677")
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)

def test_get_waiter_tables(waiter_client, mock_db_session):
    mock_db_session.exec.return_value.all.return_value = [
        (Table(id=1, number=5, capacity=4, status=TableStatus.free), None)
    ]
    response = waiter_client.get("/api/waiter/tables")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["number"] == 5

def test_get_waiter_tables_unauthorized(client):
    response = client.get("/api/waiter/tables")
    assert response.status_code == 401

def test_update_table_status(waiter_client, mock_db_session):
    mock_table = Table(id=1, number=5, capacity=4, status=TableStatus.free)
    mock_db_session.get.side_effect = [mock_table, None] # table, user
    
    def mock_refresh(obj):
        pass
    mock_db_session.refresh.side_effect = mock_refresh
    
    response = waiter_client.patch("/api/waiter/tables/1/status", json={"status": "occupied"})
    assert response.status_code == 200
    assert response.json()["status"] == "occupied"

def test_get_manager_stats(manager_client, mock_db_session):
    mock_db_session.exec.return_value.all.side_effect = [
        [Order(id=1, table_id=1, total_price=10.5), Order(id=2, table_id=2, total_price=5.0)],
        [MenuItem(id=1, name="Burger", price=10.0, category_id=1)]
    ]
    
    response = manager_client.get("/api/manager/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_revenue"] == 15.5
    assert data["total_orders"] == 2
    assert data["menu_items_count"] == 1

def test_get_chef_orders(chef_client, mock_db_session):
    mock_db_session.exec.return_value.all.side_effect = [
        [Order(id=1, table_id=1, status=OrderStatus.pending, total_price=0.0)], # orders
        [], # order items (empty for simplicity)
    ]
    mock_db_session.get.return_value = Table(id=1, number=5, status=TableStatus.occupied)
    
    response = chef_client.get("/api/chef/active-orders")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
