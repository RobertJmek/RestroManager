from fastapi import WebSocket
from typing import Dict, List

class ConnectionManager:
    def __init__(self):
        # Gestionăm conexiunile pe roluri
        self.active_connections: Dict[str, List[WebSocket]] = {
            "chef": [],
            "waiter": [],
            "manager": []
        }

    async def connect(self, websocket: WebSocket, role: str):
        await websocket.accept()
        if role in self.active_connections:
            self.active_connections[role].append(websocket)

    def disconnect(self, websocket: WebSocket, role: str):
        if role in self.active_connections:
            self.active_connections[role].remove(websocket)

    async def broadcast_to_role(self, role: str, message: dict):
        """Trimite notificări doar către un anumit grup (ex: doar Bucătari)"""
        if role in self.active_connections:
            for connection in self.active_connections[role]:
                await connection.send_json(message)

manager = ConnectionManager()