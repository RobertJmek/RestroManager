import pytest
import datetime
from models.user import User, UserRole
from main import app
from core.security import get_current_user

@pytest.fixture
def manager_client(client):
    def override_get_current_user():
        return User(id=1, email="admin@test.com", name="Admin", role=UserRole.manager, hashed_password="pw", phone="22233344")
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)

def test_get_range_report(manager_client, mock_db_session):
    mock_db_session.exec.return_value.one.side_effect = [
        100.0, # total revenue
        5      # total orders
    ]
    
    # exec is called twice more for .all() queries
    # First: top items
    # Second: revenue by day
    # We must mock them specifically or return side effects
    
    class MockResult:
        def __init__(self, data):
            self.data = data
        def all(self):
            return self.data
            
    mock_db_session.exec.side_effect = [
        # for total_revenue (needs .one())
        type('MockQuery', (), {'one': lambda self: 100.0})(),
        # for total_orders (needs .one())
        type('MockQuery', (), {'one': lambda self: 5})(),
        # for top_items
        MockResult([("Burger", 10)]),
        # for revenue_by_day
        MockResult([(datetime.date(2026, 5, 7), 100.0)])
    ]
    
    response = manager_client.get("/api/reports/range?start_date=2026-05-01&end_date=2026-05-31")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_revenue"] == 100.0
    assert data["total_orders"] == 5
    assert data["top_items"][0]["name"] == "Burger"
    assert data["revenue_by_day"][0]["revenue"] == 100.0

def test_get_range_report_invalid_date(manager_client):
    response = manager_client.get("/api/reports/range?start_date=invalid-date")
    assert response.status_code == 422
