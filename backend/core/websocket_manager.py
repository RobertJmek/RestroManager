import asyncio
import json
from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # Stocăm conexiunile active: { "role": [websocket1, websocket2] }
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def register(self, websocket: WebSocket, role: str):
        async with self._lock:
            if role not in self.active_connections:
                self.active_connections[role] = []
            self.active_connections[role].append(websocket)
        print(f"[WS] Noua conexiune acceptata. Rol: {role}")

    async def connect(self, websocket: WebSocket, role: str):
        await websocket.accept()
        await self.register(websocket, role)

    async def disconnect(self, websocket: WebSocket, role: str):
        async with self._lock:
            if role in self.active_connections and websocket in self.active_connections[role]:
                self.active_connections[role].remove(websocket)
                print(f"[WS] Conexiune inchisa. Rol: {role}")

    async def broadcast_to_role(self, role: str, message: dict):
        # BUG FIX: nu tine lock-ul in timp ce face await send_json
        # (await in asyncio.Lock = deadlock daca acelasi task apeleaza din nou broadcast)
        async with self._lock:
            connections = list(self.active_connections.get(role, []))

        dead_connections = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Eroare trimitere WS catre {role}: {e}")
                dead_connections.append(connection)

        if dead_connections:
            async with self._lock:
                for dead in dead_connections:
                    if dead in self.active_connections.get(role, []):
                        self.active_connections[role].remove(dead)
                        print(f"[WS] Conexiune eliminata (dead). Rol: {role}")

manager = ConnectionManager()
