import pytest
from pydantic_core._pydantic_core import ValidationError

from models.user import User, UserRole
from models.order import Order, OrderStatus
from models.order_item import OrderItem

def test_user_validation():
    # Valid User
    user = User.model_validate({"email": "test@test.com", "phone": "1234567", "name": "Test", "hashed_password": "pw"})
    assert user.role == UserRole.customer
    assert user.is_active is True

    # Invalid phone (too short)
    with pytest.raises(ValidationError):
        User.model_validate({"email": "test@test.com", "phone": "12345", "name": "Test", "hashed_password": "pw"})
    
    # Invalid email
    with pytest.raises(ValidationError):
        User.model_validate({"email": "notanemail", "phone": "12345678", "name": "Test", "hashed_password": "pw"})

def test_order_validation():
    order = Order.model_validate({"table_id": 1, "total_price": 15.5})
    assert order.status == OrderStatus.pending
    
    # Negative price
    with pytest.raises(ValidationError):
        Order.model_validate({"table_id": 1, "total_price": -5.0})

def test_order_item_validation():
    item = OrderItem.model_validate({"order_id": 1, "menu_item_id": 1, "quantity": 2})
    assert item.quantity == 2
    
    # Zero or negative quantity
    with pytest.raises(ValidationError):
        OrderItem.model_validate({"order_id": 1, "menu_item_id": 1, "quantity": 0})
        
    # Invalid order_id
    with pytest.raises(ValidationError):
        OrderItem.model_validate({"order_id": 0, "menu_item_id": 1, "quantity": 1})
