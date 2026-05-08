import pytest
from unittest.mock import AsyncMock
from fastapi import WebSocket

from core.websocket_manager import ConnectionManager

@pytest.fixture
def ws_manager():
    return ConnectionManager()

@pytest.fixture
def mock_websocket():
    ws = AsyncMock(spec=WebSocket)
    return ws

@pytest.mark.asyncio
async def test_connect(ws_manager, mock_websocket):
    await ws_manager.connect(mock_websocket, "waiter")
    
    mock_websocket.accept.assert_awaited_once()
    assert "waiter" in ws_manager.active_connections
    assert mock_websocket in ws_manager.active_connections["waiter"]

@pytest.mark.asyncio
async def test_disconnect(ws_manager, mock_websocket):
    await ws_manager.connect(mock_websocket, "chef")
    assert mock_websocket in ws_manager.active_connections["chef"]
    
    await ws_manager.disconnect(mock_websocket, "chef")
    assert mock_websocket not in ws_manager.active_connections["chef"]

@pytest.mark.asyncio
async def test_broadcast_to_role(ws_manager, mock_websocket):
    ws2 = AsyncMock(spec=WebSocket)
    
    await ws_manager.connect(mock_websocket, "waiter")
    await ws_manager.connect(ws2, "waiter")
    
    message = {"type": "NEW_ORDER"}
    await ws_manager.broadcast_to_role("waiter", message)
    
    mock_websocket.send_json.assert_awaited_once_with(message)
    ws2.send_json.assert_awaited_once_with(message)

@pytest.mark.asyncio
async def test_broadcast_to_role_with_dead_connection(ws_manager, mock_websocket):
    # Setup mock to raise Exception when send_json is called
    mock_websocket.send_json.side_effect = Exception("Connection closed")
    
    await ws_manager.connect(mock_websocket, "waiter")
    
    await ws_manager.broadcast_to_role("waiter", {"type": "TEST"})
    
    # The dead connection should be removed
    assert mock_websocket not in ws_manager.active_connections["waiter"]
