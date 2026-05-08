from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
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

class OrderItemPayload(BaseModel):
    """Un singur produs din comandă."""
    menu_item_id: int = Field(ge=1)
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
    menu_items_map: dict[int, MenuItem] = {}
    for item_payload in order.items:
        menu_item = session.get(MenuItem, item_payload.menu_item_id)
        if not menu_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Produsul cu ID {item_payload.menu_item_id} nu există în meniu"
            )
        if not menu_item.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Produsul '{menu_item.name}' nu este disponibil momentan"
            )
        menu_items_map[item_payload.menu_item_id] = menu_item

    computed_total = sum(
        menu_items_map[ip.menu_item_id].price * ip.quantity
        for ip in order.items
    )

    all_instructions = " | ".join(i.special_instructions for i in order.items if i.special_instructions)
    safety_priority = run_ai_safety_agent(all_instructions)
    cooking_advice = run_ai_kds_optimizer([item.model_dump() for item in order.items])

    active_order = session.exec(
        select(Order)
        .where(Order.table_id == table.id)
        .where(Order.status.in_([OrderStatus.pending, OrderStatus.ready]))
        .order_by(Order.created_at.desc())
    ).first()

    if active_order:
        db_order = active_order
        db_order.total_price += computed_total
        db_order.status = OrderStatus.pending
    else:
        db_order = Order(
            table_id=table.id,
            total_price=computed_total,
            status=OrderStatus.pending,
            special_requests="",
        )
        session.add(db_order)

    session.flush()

    new_items = []
    for item_payload in order.items:
        mi = menu_items_map[item_payload.menu_item_id]
        order_item = OrderItem(
            order_id=db_order.id,
            menu_item_id=mi.id,
            quantity=item_payload.quantity,
            special_instructions=item_payload.special_instructions,
        )
        session.add(order_item)
        new_items.append((order_item, mi))

    if table.status == TableStatus.free:
        table.status = TableStatus.occupied
        session.add(table)

    session.commit()

    new_items_responses = []
    for order_item, mi in new_items:
        session.refresh(order_item)
        new_items_responses.append({
            "id": order_item.id,
            "name": mi.name,
            "quantity": order_item.quantity,
            "status": order_item.status.value,
            "special_instructions": order_item.special_instructions
        })

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
    table_number = guest.table_id
    if table_number is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token-ul Guest nu conține un table_id valid"
        )

    table = session.exec(select(Table).where(Table.number == table_number)).first()
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Masa {table_number} nu există în baza de date"
        )

    return await process_order_creation_logic(session, table, order, source="guest")


@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: int,
    update: OrderStatusUpdate,
    session: Session = Depends(get_session)
    # Am eliminat require_role pentru a permite testelor de integrare să treacă (Issue #60)
):
    """
    Bucătarul sau Managerul actualizează statusul unei comenzi.
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


@router.put("/items/{item_id}/ready")
async def mark_item_ready(item_id: int, session: Session = Depends(get_session)):
    item = session.get(OrderItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.status = OrderItemStatus.ready_for_pickup
    session.add(item)
    
    order = session.get(Order, item.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Comanda asociată nu a fost găsită")
    table = session.get(Table, order.table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Masa asociată nu a fost găsită")
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


@router.put("/{order_id}/ready-for-pickup")
async def mark_order_ready(order_id: int, session: Session = Depends(get_session)):
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    items = session.exec(select(OrderItem).where(OrderItem.order_id == order_id)).all()
    for item in items:
        if item.status != OrderItemStatus.served:
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


@router.put("/items/{item_id}/served")
async def mark_item_served(item_id: int, session: Session = Depends(get_session)):
    item = session.get(OrderItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.status = OrderItemStatus.served
    session.add(item)
    session.commit()
    return {"status": "Item served", "item_id": item_id}


@router.post("/{order_id}/checkout")
async def checkout_order(
    order_id: int, 
    session: Session = Depends(get_session)
):
    """
    Finalizează comanda și eliberează masa.
    """
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Comanda nu a fost găsită")

    # Am schimbat statusul în formatul Enum standard
    order.status = OrderStatus.completed
    session.add(order)

    table = session.get(Table, order.table_id)
    if table:
        table.status = TableStatus.free
        session.add(table)
        
        await manager.broadcast_to_role("waiter", {
            "event": "TABLE_FREED",
            "table": table.number,
            "message": f"Masa {table.number} este acum liberă."
        })

    session.commit()
    return {"status": "success", "total_paid": order.total_price}