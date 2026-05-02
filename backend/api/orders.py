from fastapi import APIRouter, Depends
from core.security import get_current_guest
from models.user import TokenData
from core.websocket_manager import manager
from core.ai import run_ai_kds_optimizer, run_ai_safety_agent

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("")
async def create_order(
    order: dict, 
    guest: TokenData = Depends(get_current_guest)
):
    """
    Apelat de Client (Guest). 
    table_id este extras automat din JWT-ul scanat la masă.
    """
    # Folosim table_id din token pentru securitate
    table_id = guest.table_id
    
    # 1. Rulăm agenții AI
    safety_priority = run_ai_safety_agent(order.get("notes", ""))
    cooking_advice = run_ai_kds_optimizer(order.get("items", []))
    
    # Suprascriem table_number cu valoarea de încredere din JWT
    sanitized_order = {**order, "table_number": table_id}

    payload = {
        "event": "NEW_ORDER",
        "ai_metadata": {
            "urgency": safety_priority,
            "cooking_strategy": cooking_advice
        },
        "data": sanitized_order
    }
    
    # 2. Notificăm Bucătăria (KDS) în timp real
    await manager.broadcast_to_role("chef", payload)
    
    # 3. Notificăm și Chelnerul că s-a ocupat o masă 
    await manager.broadcast_to_role("waiter", {
        "event": "TABLE_OCCUPIED",
        "table": table_id
    })

    return {"status": "Processed by AI and sent to KDS", "ai_safety": safety_priority, "table_id": table_id}
