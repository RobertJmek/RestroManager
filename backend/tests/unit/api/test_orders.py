import pytest
from models.user import User, UserRole, TokenData
from models.order import Order, OrderStatus
from models.table import Table, TableStatus
from models.menu_item import MenuItem
from main import app
from core.security import get_current_guest, get_current_user

@pytest.fixture
def guest_client(client):
    def override_get_current_guest():
        return TokenData(role="Guest", table_id=5)
    app.dependency_overrides[get_current_guest] = override_get_current_guest
    yield client
    app.dependency_overrides.pop(get_current_guest, None)

@pytest.fixture
def chef_client(client):
    def override_get_current_user():
        return User(id=3, email="chef@test.com", name="Chef", role=UserRole.chef, hashed_password="pw", phone="55566677")
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)

@pytest.fixture
def waiter_client(client):
    """Client authenticated as waiter using get_valid_user_or_guest"""
    from core.security import get_valid_user_or_guest
    def override_get_valid_user_or_guest():
        return TokenData(email="waiter@test.com", role="Waiter", user_id=2)
    app.dependency_overrides[get_valid_user_or_guest] = override_get_valid_user_or_guest
    yield client
    app.dependency_overrides.pop(get_valid_user_or_guest, None)

def test_create_order_as_guest(guest_client, mock_db_session):
    mock_db_session.exec.return_value.first.side_effect = [
        Table(id=1, number=5, status=TableStatus.free), # First find table
        None, # active_order lookup
        MenuItem(id=1, name="Pizza", price=10.0, category_id=1) # find menu item
    ]
    
    def mock_refresh(obj):
        obj.id = 1
    mock_db_session.refresh.side_effect = mock_refresh
    
    response = guest_client.post("/api/orders", json={
        "items": [
            {"menu_item_id": 1, "name": "Pizza", "quantity": 1, "prep_time": 10}
        ],
        "table_number": 5,
        "total": 10.0
    })
    
    assert response.status_code == 200
    assert response.json()["status"] == "Processed by AI and sent to KDS"
    assert response.json()["table_id"] == 5

def test_create_order_as_guest_invalid_table(guest_client, mock_db_session):
    mock_db_session.exec.return_value.first.return_value = None # table not found
    
    response = guest_client.post("/api/orders", json={
        "items": [
            {"menu_item_id": 1, "name": "Pizza", "quantity": 1, "prep_time": 10}
        ]
    })
    
    assert response.status_code == 404

def test_update_order_status_as_chef(chef_client, mock_db_session):
    mock_db_session.get.side_effect = [
        Order(id=1, table_id=1, status=OrderStatus.pending), # order
        Table(id=1, number=5) # table for WS broadcast
    ]
    
    def mock_refresh(obj):
        pass
    mock_db_session.refresh.side_effect = mock_refresh
    
    response = chef_client.patch("/api/orders/1/status", json={"status": "ready"})
    
    assert response.status_code == 200
    assert response.json()["new_status"] == "ready"

def test_update_order_status_not_found(chef_client, mock_db_session):
    mock_db_session.get.return_value = None
    response = chef_client.patch("/api/orders/99/status", json={"status": "ready"})
    assert response.status_code == 404

def test_create_order_as_waiter(waiter_client, mock_db_session):
    """Test that waiter can create order for any table by providing table_id"""
    mock_db_session.exec.return_value.first.side_effect = [
        Table(id=1, number=3, status=TableStatus.free), # Find table
        None, # No active order
        MenuItem(id=1, name="Burger", price=15.0, category_id=1) # Find menu item
    ]
    
    def mock_refresh(obj):
        if hasattr(obj, 'id'):
            obj.id = 1
    mock_db_session.refresh.side_effect = mock_refresh
    
    response = waiter_client.post("/api/orders", json={
        "items": [
            {"menu_item_id": 1, "quantity": 2, "special_instructions": "No onions"}
        ],
        "table_id": 3  # Waiter specifies table_id
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["table_id"] == 3
    assert data["status"] == "Processed by AI and sent to KDS"
    assert "items" in data

def test_create_order_as_waiter_missing_table_id(waiter_client, mock_db_session):
    """Test that waiter gets error when table_id is missing"""
    response = waiter_client.post("/api/orders", json={
        "items": [{"menu_item_id": 1, "quantity": 1}]
    })
    
    assert response.status_code == 400
    assert "table_id" in response.json()["detail"].lower() or "waiter" in response.json()["detail"].lower()

def test_create_order_as_waiter_auto_claims_table(waiter_client, mock_db_session):
    """Test that table is auto-assigned to waiter who creates the order"""
    table = Table(id=1, number=5, status=TableStatus.free, waiter_id=None)
    mock_db_session.exec.return_value.first.side_effect = [
        table,  # Find table (unclaimed)
        None,   # No active order
        MenuItem(id=1, name="Pasta", price=12.0, category_id=1)
    ]
    
    def mock_refresh(obj):
        if hasattr(obj, 'id'):
            obj.id = 1
    mock_db_session.refresh.side_effect = mock_refresh
    
    response = waiter_client.post("/api/orders", json={
        "items": [{"menu_item_id": 1, "quantity": 1}],
        "table_id": 5
    })
    
    assert response.status_code == 200
    # Verify table was assigned to waiter (user_id=2 from fixture)
    assert table.waiter_id == 2
    mock_db_session.add.assert_called()  # Table was saved
