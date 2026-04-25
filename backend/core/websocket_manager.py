import json
from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # Stocăm conexiunile active: { "role": [websocket1, websocket2] }
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, role: str):
        await websocket.accept()
        if role not in self.active_connections:
            self.active_connections[role] = []
        self.active_connections[role].append(websocket)
        print(f"[WS] Noua conexiune acceptata. Rol: {role}")

    def disconnect(self, websocket: WebSocket, role: str):
        if role in self.active_connections and websocket in self.active_connections[role]:
            self.active_connections[role].remove(websocket)
            print(f"[WS] Conexiune inchisa. Rol: {role}")

    async def broadcast_to_role(self, role: str, message: dict):
        if role in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[role]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Eroare trimitere WS catre {role}: {e}")
                    dead_connections.append(connection)
            
            for dead in dead_connections:
                self.disconnect(dead, role)

manager = ConnectionManager()
