from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from core.websocket_manager import manager
import jwt
from core.config import settings

router = APIRouter()

# WebSocket close codes
WS_CLOSE_AUTH_FAILURE = 4001 

@router.websocket("/ws/{role}")
async def websocket_endpoint(websocket: WebSocket, role: str, token: str = Query(...)):
    # 1. Validare JWT (Securitate conform Epic)
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_role: str = payload.get("role", "")
        
        if token_role.lower() != role.lower():
            await websocket.close(code=WS_CLOSE_AUTH_FAILURE)
            return
    except jwt.PyJWTError:
        await websocket.close(code=WS_CLOSE_AUTH_FAILURE)
        return

    # Normalize role to lowercase so broadcasts always find the right channel
    normalized_role = role.lower()
    jwt_table_id = payload.get("table_id")

    # Use manager.connect() which handles accept + lock-safe registration
    await manager.connect(websocket, normalized_role)
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            # --- SUB-TASK: NOTIFICARE COMANDĂ NOUĂ (CLIENT -> BUCĂTĂRIE & CHELNER) ---
            if action == "NEW_ORDER" and normalized_role == "guest":
                # i. Către canalul kitchen (chef): Toate datele comenzii
                await manager.broadcast_to_role("chef", {
                    "event": "NEW_ORDER_RECEIVED",
                    "table": jwt_table_id,
                    "order_details": data.get("order_items"),
                    "message": f"Comandă nouă la masa {jwt_table_id}!"
                })
                
                # ii. Către canalul waiter: Notificare specifică
                await manager.broadcast_to_role("waiter", {
                    "event": "TABLE_UPDATE",
                    "table": jwt_table_id,
                    "message": f"Clientul de la masa {jwt_table_id} a adăugat produse noi.",
                    "type": "info"
                })

            # --- SUB-TASK: BUCĂTAR MARCHEAZĂ COMANDA GATA ---
            elif action == "ORDER_READY" and normalized_role == "chef":
                await manager.broadcast_to_role("waiter", {
                    "event": "FOOD_READY",
                    "table": data.get("table"),
                    "message": f"Mâncarea pentru masa {data.get('table')} este gata!",
                    "type": "success"
                })

            # --- SUB-TASK: CLIENTUL CHEAMĂ CHELNERUL ---
            elif action == "CALL_WAITER":
                table = jwt_table_id if normalized_role == "guest" else data.get("table")
                
                if table and (isinstance(table, int) and table > 0):
                    await manager.broadcast_to_role("waiter", {
                        "event": "URGENT_CALL",
                        "table": table,
                        "message": "⚠️ Solicitare asistență la masă!"
                    })

    except WebSocketDisconnect:
        await manager.disconnect(websocket, normalized_role)
    except Exception:
        await manager.disconnect(websocket, normalized_role)
