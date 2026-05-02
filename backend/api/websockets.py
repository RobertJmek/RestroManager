from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from core.websocket_manager import manager
import jwt
from core.config import settings

router = APIRouter()

# WebSocket close codes (4000-4999 are application-defined)
WS_CLOSE_AUTH_FAILURE = 4001  # Unauthorized: missing, invalid, or mismatched token

@router.websocket("/ws/{role}")
async def websocket_endpoint(websocket: WebSocket, role: str, token: str = Query(...)):
    """
    Endpoint WebSocket cu autentificare JWT.
    Token-ul trebuie trimis ca parametru de query: ws://.../ws/{role}?token=<jwt>

    Rolul din JWT este title-cased (ex: "Chef"), iar calea WS este lowercase (ex: "chef").
    Comparația se face case-insensitive pentru a suporta această convenție.
    """
    await websocket.accept()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_role: str = payload.get("role", "")
        # JWT roles are title-cased ("Chef"), WS paths are lowercase ("chef")
        if token_role.lower() != role.lower():
            await websocket.close(code=WS_CLOSE_AUTH_FAILURE)
            return
    except jwt.PyJWTError:
        await websocket.close(code=WS_CLOSE_AUTH_FAILURE)
        return

    # Înregistrăm conexiunea fără a o accepta din nou
    if role not in manager.active_connections:
        manager.active_connections[role] = []
    manager.active_connections[role].append(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            
            # ACȚIUNE: Bucătarul marchează comanda ca gata 
            if data.get("action") == "ORDER_READY":
                await manager.broadcast_to_role("waiter", {
                    "event": "FOOD_READY",
                    "table": data.get("table"),
                    "message": f"Mâncarea pentru masa {data.get('table')} este gata de servit!",
                    "type": "success"
                })
                
            # ACȚIUNE: Clientul cheamă chelnerul 
            if data.get("action") == "CALL_WAITER":
                await manager.broadcast_to_role("waiter", {
                    "event": "URGENT_CALL",
                    "table": data.get("table"),
                    "message": "⚠️ Solicitare asistență la masă!"
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, role)
