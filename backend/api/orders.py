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
from models.order_item import OrderItem, OrderItemStatus
from models.menu_item import MenuItem
from models.table import Table, TableStatus

router = APIRouter(prefix="/orders", tags=["Orders"])

# --- Schemas ---

MAX_NOTES_LENGTH = 500


class OrderItemPayload(BaseModel):
    """Un singur produs din comandă."""
    menu_item_id: Optional[int] = Field(default=None, ge=1)
    name: str = Field(min_length=1, max_length=200)
    quantity: int = Field(ge=1, le=99)
    prep_time: int = Field(ge=0, le=120)
    special_instructions: Optional[str] = Field(default=None, max_length=500)


class OrderCreatePayload(BaseModel):
    """Payload-ul complet trimis de clientul Guest."""
    items: List[OrderItemPayload] = Field(min_length=1, max_length=50)
    table_number: Optional[int] = Field(default=None, ge=1)
    total: Optional[float] = Field(default=None, ge=0.0)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


# --- Endpoints ---

async def process_order_creation_logic(
    session: Session,
    table: Table,
    order: OrderCreatePayload,
    source: str = "guest"
) -> dict:
    """Helper comun pentru client și chelner pentru a crea/lipi comanda."""
    active_order = session.exec(
        select(Order)
        .where(Order.table_id == table.id)
        .where(Order.status.in_([OrderStatus.pending, OrderStatus.ready]))
        .order_by(Order.created_at.desc())
    ).first()

    # 2. Rulăm agenții AI pentru articolele NOI (agregăm toate notele produselor)
    all_instructions = " | ".join(i.special_instructions for i in order.items if i.special_instructions)
    safety_priority = run_ai_safety_agent(all_instructions)
    cooking_advice = run_ai_kds_optimizer([item.model_dump() for item in order.items])

    if active_order:
        db_order = active_order
        db_order.total_price += (order.total or 0.0)
        db_order.status = OrderStatus.pending
    else:
        db_order = Order(
            table_id=table.id,
            total_price=order.total or 0.0,
            status=OrderStatus.pending,
            special_requests="", # Am eliminat notița globală
        )
        session.add(db_order)
    
    session.commit()
    session.refresh(db_order)

    # 3. Salvăm produsele noi în OrderItem
    new_items_responses = []
    for item_payload in order.items:
        menu_item = session.exec(
            select(MenuItem).where(MenuItem.name == item_payload.name)
        ).first()
        if menu_item:
            order_item = OrderItem(
                order_id=db_order.id,
                menu_item_id=menu_item.id,
                quantity=item_payload.quantity,
                special_instructions=item_payload.special_instructions,
            )
            session.add(order_item)
            session.commit()
            session.refresh(order_item)
            new_items_responses.append({
                "id": order_item.id,
                "name": menu_item.name,
                "quantity": order_item.quantity,
                "status": order_item.status.value,
                "special_instructions": order_item.special_instructions
            })

    # 4. Actualizăm statusul mesei dacă e liberă
    if table.status == TableStatus.free:
        table.status = TableStatus.occupied
        session.add(table)
        session.commit()

    # 5. Broadcast la Chef cu ID-ul real și DOAR produsele noi
    payload = {
        "event": "NEW_ORDER",
        "ai_metadata": {
            "urgency": safety_priority,
            "cooking_strategy": cooking_advice
        },
        "data": {
            "id": db_order.id,
            "table_number": table.number,
            "items": new_items_responses
        }
    }
    await manager.broadcast_to_role("chef", payload)

    # 6. Broadcast la Waiter (să știe că s-a actualizat masa)
    if not active_order or source == "guest":
        await manager.broadcast_to_role("waiter", {
            "event": "TABLE_OCCUPIED",
            "table": table.number,
            "message": f"Comandă nouă Masă: #{table.number}"
        })

    return {
        "status": "Processed by AI and sent to KDS",
        "ai_safety": safety_priority,
        "table_id": table.number,
        "order_id": db_order.id
    }


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

    return await process_order_creation_logic(session, table, order, source="guest")


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


@router.put("/items/{item_id}/ready", dependencies=[Depends(require_role(["Chef"]))])
async def mark_item_ready(item_id: int, session: Session = Depends(get_session)):
    item = session.get(OrderItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.status = OrderItemStatus.ready_for_pickup
    session.add(item)
    
    order = session.get(Order, item.order_id)
    table = session.get(Table, order.table_id)
    session.commit()
    
    waiter_id = table.waiter_id
    payload = {
        "event": "FOOD_READY_FOR_PICKUP",
        "table": table.number,
        "target_waiter_id": waiter_id,
        "message": f"Mâncarea pentru Masa {table.number} te așteaptă la geam!"
    }
    await manager.broadcast_to_role("waiter", payload)
    
    return {"status": "Item ready for pickup", "item_id": item_id}


@router.put("/{order_id}/ready-for-pickup", dependencies=[Depends(require_role(["Chef"]))])
async def mark_order_ready(order_id: int, session: Session = Depends(get_session)):
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    items = session.exec(select(OrderItem).where(OrderItem.order_id == order_id)).all()
    for item in items:
        item.status = OrderItemStatus.ready_for_pickup
        session.add(item)
        
    order.status = OrderStatus.ready
    table = session.get(Table, order.table_id)
    session.add(order)
    session.commit()
    
    waiter_id = table.waiter_id
    payload = {
        "event": "FOOD_READY_FOR_PICKUP",
        "table": table.number,
        "target_waiter_id": waiter_id,
        "message": f"Mâncarea pentru Masa {table.number} te așteaptă la geam!"
    }
    await manager.broadcast_to_role("waiter", payload)
    
    return {"status": "Order ready for pickup", "order_id": order_id}


@router.put("/items/{item_id}/served", dependencies=[Depends(require_role(["Waiter", "Manager"]))])
async def mark_item_served(item_id: int, session: Session = Depends(get_session)):
    item = session.get(OrderItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.status = OrderItemStatus.served
    session.add(item)
    session.commit()
    return {"status": "Item served", "item_id": item_id}
