from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.websocket_manager import manager

router = APIRouter()

@router.websocket("/ws/{role}")
async def websocket_endpoint(websocket: WebSocket, role: str):
    await manager.connect(websocket, role)
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
