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
    # Validate JWT BEFORE accepting the connection (M1 fix)
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

    # BUG FIX: use manager.connect() which handles locking correctly
    # (previously we called websocket.accept() twice and bypassed the lock)
    await manager.connect(websocket, normalized_role)
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
            # Guests must use the JWT-derived table_id (cannot be spoofed).
            # Staff roles must provide a valid positive table number.
            if data.get("action") == "CALL_WAITER":
                if normalized_role == "guest":
                    # For guests, only proceed if the JWT carries a valid table_id
                    if jwt_table_id is None:
                        continue
                    table = jwt_table_id
                else:
                    table = data.get("table")
                    # Staff cannot spoof table — must provide a valid positive integer (M2 fix)
                    if not isinstance(table, int) or table <= 0:
                        continue
                await manager.broadcast_to_role("waiter", {
                    "event": "URGENT_CALL",
                    "table": table,
                    "message": "⚠️ Solicitare asistență la masă!"
                })

    except WebSocketDisconnect:
        await manager.disconnect(websocket, normalized_role)
    except Exception:
        await manager.disconnect(websocket, normalized_role)
