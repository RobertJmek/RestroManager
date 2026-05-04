from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from sqlmodel import Session, select

from core.security import get_current_guest, require_role
from models.user import TokenData
from core.websocket_manager import manager
from core.ai import run_ai_kds_optimizer, run_ai_safety_agent
from db.session import get_session
from models.order import Order, OrderStatus
from models.order_item import OrderItem
from models.menu_item import MenuItem
from models.table import Table, TableStatus

router = APIRouter(prefix="/orders", tags=["Orders"])

# --- Schemas ---

MAX_NOTES_LENGTH = 500


class OrderItemPayload(BaseModel):
    """Un singur produs din comandă."""
    name: str = Field(min_length=1, max_length=200)
    quantity: int = Field(ge=1, le=99)
    prep_time: int = Field(ge=0, le=120)


class OrderCreatePayload(BaseModel):
    """Payload-ul complet trimis de clientul Guest."""
    items: List[OrderItemPayload] = Field(min_length=1, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=MAX_NOTES_LENGTH)
    table_number: Optional[int] = Field(default=None, ge=1)
    total: Optional[float] = Field(default=None, ge=0.0)

    @field_validator("notes")
    @classmethod
    def sanitize_notes(cls, v: Optional[str]) -> Optional[str]:
        """Elimină caracterele de control."""
        if v is None:
            return v
        import re
        sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", v)
        return sanitized[:MAX_NOTES_LENGTH]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


# --- Endpoints ---

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
    table_number = guest.table_id
    if table_number is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token-ul Guest nu conține un table_id valid"
        )

    # Căutăm masa în DB după număr pentru a obține id-ul real
    table = session.exec(select(Table).where(Table.number == table_number)).first()
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Masa {table_number} nu există în baza de date"
        )

    # 1. Rulăm agenții AI
    safety_priority = run_ai_safety_agent(order.notes or "")
    cooking_advice = run_ai_kds_optimizer([item.model_dump() for item in order.items])

    sanitized_order = order.model_dump()
    sanitized_order["table_number"] = table_number

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

    # 3. Notificăm Chelnerul că s-a ocupat o masă
    await manager.broadcast_to_role("waiter", {
        "event": "TABLE_OCCUPIED",
        "table": table_number,
        "message": f"Masă ocupată: #{table_number}"
    })

    # 4. Salvăm comanda în DB
    db_order = Order(
        table_id=table.id,
        total_price=order.total or 0.0,
        status=OrderStatus.pending,
        special_requests=order.notes,
    )
    session.add(db_order)
    session.commit()
    session.refresh(db_order)

    # 5. Salvăm produsele în OrderItem (lookup după nume)
    for item_payload in order.items:
        menu_item = session.exec(
            select(MenuItem).where(MenuItem.name == item_payload.name)
        ).first()
        if menu_item:
            order_item = OrderItem(
                order_id=db_order.id,
                menu_item_id=menu_item.id,
                quantity=item_payload.quantity,
                special_instructions=order.notes,
            )
            session.add(order_item)
    session.commit()

    # 6. Actualizăm statusul mesei în DB la 'occupied'
    table.status = TableStatus.occupied
    session.add(table)
    session.commit()

    return {
        "status": "Processed by AI and sent to KDS",
        "ai_safety": safety_priority,
        "table_id": table_number,
        "order_id": db_order.id
    }


@router.patch("/{order_id}/status", dependencies=[Depends(require_role(["Chef", "Manager"]))])
async def update_order_status(
    order_id: int,
    update: OrderStatusUpdate,
    session: Session = Depends(get_session)
):
    """
    Bucătarul sau Managerul actualizează statusul unei comenzi.
    Dacă status = 'ready', se trimite broadcast WS la Waiter.
    """
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comanda {order_id} nu există"
        )

    order.status = update.status
    session.add(order)
    session.commit()
    session.refresh(order)

    # Dacă comanda e gata, notificăm Chelnerul prin WS
    if update.status == OrderStatus.ready:
        table = session.get(Table, order.table_id)
        table_number = table.number if table else order.table_id
        await manager.broadcast_to_role("waiter", {
            "event": "FOOD_READY",
            "table": table_number,
            "message": f"Mâncarea pentru masa {table_number} este gata de servit!",
            "type": "success"
        })

    return {
        "status": "updated",
        "order_id": order_id,
        "new_status": update.status.value
    }
