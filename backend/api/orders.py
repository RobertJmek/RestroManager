
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from sqlmodel import Session
from db.session import get_session
from core.security import get_current_guest
from models.user import TokenData
from models.order import Order
from models.order_item import OrderItem
from core.websocket_manager import manager
from core.ai import run_ai_kds_optimizer, run_ai_safety_agent

router = APIRouter(prefix="/orders", tags=["Orders"])

# --- Schemas for input validation (H1 fix) ---

MAX_NOTES_LENGTH = 500

class OrderItemPayload(BaseModel):
    """Un singur produs din comandă."""
    menu_item_id: Optional[int] = Field(default=None, ge=1)
    name: str = Field(min_length=1, max_length=200)
    quantity: int = Field(ge=1, le=99)
    prep_time: int = Field(ge=0, le=120)

class OrderCreatePayload(BaseModel):
    """Payload-ul complet trimis de clientul Guest."""
    items: List[OrderItemPayload] = Field(min_length=1, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=MAX_NOTES_LENGTH)
    table_number: Optional[int] = Field(default=None, ge=1)  # suprascris din JWT
    total: Optional[float] = Field(default=None, ge=0.0)

    @field_validator("notes")
    @classmethod
    def sanitize_notes(cls, v: Optional[str]) -> Optional[str]:
        """Elimină caracterele de control (L5 fix included)."""
        if v is None:
            return v
        import re
        # Strip control characters except newline and tab
        sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", v)
        return sanitized[:MAX_NOTES_LENGTH]

# --- Endpoint ---

@router.post("")
async def create_order(
    order: OrderCreatePayload,
    guest: TokenData = Depends(get_current_guest),
    session: Session = Depends(get_session)
):
    """
    Apelat de Client (Guest). 
    table_id este extras automat din JWT-ul scanat la masă.
    """
    # Folosim table_id din token pentru securitate
    table_id = guest.table_id
    if table_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token-ul Guest nu conține un table_id valid"
        )

    # 1. Rulăm agenții AI
    safety_priority = run_ai_safety_agent(order.notes or "")
    cooking_advice = run_ai_kds_optimizer([item.model_dump() for item in order.items])

    # 2. Persistăm comanda în baza de date
    db_order = Order(
        table_id=table_id,
        total_price=order.total or 0.0,
        special_requests=order.notes,
    )
    session.add(db_order)
    session.flush()  # obținem db_order.id fără commit

    for item in order.items:
        db_item = OrderItem(
            order_id=db_order.id,
            menu_item_id=item.menu_item_id or 0,
            quantity=item.quantity,
            special_instructions=None,
        )
        session.add(db_item)

    session.commit()

    # Suprascriem table_number cu valoarea de încredere din JWT
    sanitized_order = order.model_dump()
    sanitized_order["table_number"] = table_id

    payload = {
        "event": "NEW_ORDER",
        "ai_metadata": {
            "urgency": safety_priority,
            "cooking_strategy": cooking_advice
        },
        "data": sanitized_order
    }
    
    # 3. Notificăm Bucătăria (KDS) în timp real
    await manager.broadcast_to_role("chef", payload)
    
    # 4. Notificăm și Chelnerul că s-a ocupat o masă 
    await manager.broadcast_to_role("waiter", {
        "event": "TABLE_OCCUPIED",
        "table": table_id
    })

    return {"status": "Processed by AI and sent to KDS", "ai_safety": safety_priority, "table_id": table_id, "order_id": db_order.id}
