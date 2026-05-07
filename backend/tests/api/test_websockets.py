import pytest
from starlette.websockets import WebSocketDisconnect
from core.security import create_access_token

def test_websocket_auth_failure_invalid_token(client):
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/waiter?token=invalid_token"):
            pass
    assert exc.value.code == 4001

def test_websocket_auth_failure_wrong_role(client):
    token = create_access_token(data={"role": "Chef"})
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/waiter?token={token}"):
            pass
    assert exc.value.code == 4001

def test_websocket_success_and_send_message(client):
    token = create_access_token(data={"role": "Guest", "table_id": 5})
    
    # Conectăm Guest, ar trebui să accepte conexiunea
    with client.websocket_connect(f"/ws/guest?token={token}") as websocket:
        # Trimitem un mesaj
        websocket.send_json({"action": "CALL_WAITER"})
        
        # Conexiunea ar trebui să rămână deschisă (nu aruncă excepție)
        pass

def test_websocket_new_order_guest(client):
    token = create_access_token(data={"role": "Guest", "table_id": 3})
    
    with client.websocket_connect(f"/ws/guest?token={token}") as websocket:
        websocket.send_json({
            "action": "NEW_ORDER",
            "order_items": [{"id": 1}]
        })
