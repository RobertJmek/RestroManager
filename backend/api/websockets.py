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

    # Normalize role to lowercase so broadcasts always find the right channel
    normalized_role = role.lower()
    # JWT-derived table_id for guest connections (cannot be spoofed via payload)
    jwt_table_id = payload.get("table_id")

    if normalized_role not in manager.active_connections:
        manager.active_connections[normalized_role] = []
    manager.active_connections[normalized_role].append(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            
            # ACȚIUNE: Bucătarul marchează comanda ca gata
            # Only chef connections are allowed to send ORDER_READY
            if data.get("action") == "ORDER_READY" and normalized_role == "chef":
                await manager.broadcast_to_role("waiter", {
                    "event": "FOOD_READY",
                    "table": data.get("table"),
                    "message": f"Mâncarea pentru masa {data.get('table')} este gata de servit!",
                    "type": "success"
                })
                
            # ACȚIUNE: Clientul cheamă chelnerul
            # Use the JWT-derived table_id to prevent guests spoofing another table
            if data.get("action") == "CALL_WAITER":
                table = jwt_table_id if jwt_table_id is not None else data.get("table")
                await manager.broadcast_to_role("waiter", {
                    "event": "URGENT_CALL",
                    "table": table,
                    "message": "⚠️ Solicitare asistență la masă!"
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, normalized_role)
