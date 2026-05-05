from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional
from pydantic import BaseModel

from core.security import require_role
from db.session import get_session
from core.websocket_manager import manager
from models.table import Table, TableStatus
from models.order import Order, OrderStatus
from models.order_item import OrderItem
from models.menu_item import MenuItem
from models.user import User
from api.orders import OrderCreatePayload, process_order_creation_logic

router = APIRouter(tags=["Dashboards RBAC"])


# ─── Schemas ───────────────────────────────────────────────────────────────────

class TableRead(BaseModel):
    id: int
    number: int
    capacity: int
    status: str
    location: Optional[str] = None
    waiter_id: Optional[int] = None
    waiter_name: Optional[str] = None


class TableStatusUpdate(BaseModel):
    status: TableStatus

class BillRequest(BaseModel):
    payment_method: str


class ChefOrderItemRead(BaseModel):
    id: int
    name: str
    quantity: int
    status: str
    special_instructions: Optional[str] = None


class AiMetadata(BaseModel):
    urgency: str
    cooking_strategy: str


class ChefOrderRead(BaseModel):
    id: int
    table_number: int
    items: List[ChefOrderItemRead]
    notes: str
    ai_metadata: AiMetadata


class WaiterOrderItemRead(BaseModel):
    id: int
    name: str
    quantity: int
    status: str
    special_instructions: Optional[str] = None

class WaiterOrderRead(BaseModel):
    id: int
    status: str
    total_price: float
    items: List[WaiterOrderItemRead]
    notes: str


class ManagerStats(BaseModel):
    total_revenue: float
    total_orders: int
    menu_items_count: int


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/waiter/tables",
    response_model=List[TableRead],
    dependencies=[Depends(require_role(["Waiter", "Manager"]))]
)
async def get_waiter_tables(session: Session = Depends(get_session)):
    """Returnează toate mesele cu statusul lor curent din DB."""
    results = session.exec(select(Table, User).outerjoin(User, Table.waiter_id == User.id).order_by(Table.number)).all()
    return [
        TableRead(
            id=t.id,
            number=t.number,
            capacity=t.capacity,
            status=t.status.value,
            location=t.location,
            waiter_id=t.waiter_id,
            waiter_name=u.name if u else None
        )
        for t, u in results
    ]


@router.patch(
    "/waiter/tables/{table_id}/status",
    response_model=TableRead,
    dependencies=[Depends(require_role(["Waiter", "Manager"]))]
)
async def update_table_status(
    table_id: int,
    update: TableStatusUpdate,
    session: Session = Depends(get_session)
):
    """Actualizează statusul unei mese în DB."""
    table = session.get(Table, table_id)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Masa cu ID {table_id} nu există"
        )
    table.status = update.status
    session.add(table)
    session.commit()
    session.refresh(table)
    
    # Preia și User pentru a-l include în răspuns
    u = session.get(User, table.waiter_id) if table.waiter_id else None
    
    return TableRead(
        id=table.id,
        number=table.number,
        capacity=table.capacity,
        status=table.status.value,
        location=table.location,
        waiter_id=table.waiter_id,
        waiter_name=u.name if u else None
    )

@router.put("/waiter/tables/{table_id}/claim")
async def claim_table(
    table_id: int, 
    current_user: User = Depends(require_role(["Waiter"])),
    session: Session = Depends(get_session)
):
    """Chelnerul își asignează o masă."""
    table = session.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Masa nu există")
    
    table.waiter_id = current_user.id
    session.add(table)
    session.commit()

    await manager.broadcast_to_role("waiter", {
        "event": "TABLE_CLAIMED",
        "table": table.number,
        "waiter_name": current_user.name
    })

    return {"status": "ok", "message": "Masa a fost preluată"}


@router.post("/waiter/tables/{table_id}/orders")
async def waiter_create_order(
    table_id: int,
    order: OrderCreatePayload,
    current_user: User = Depends(require_role(["Waiter"])),
    session: Session = Depends(get_session)
):
    """Chelnerul adaugă produse la o masă (Walk-in sau Append)."""
    table = session.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Masa nu există")
    
    if table.waiter_id and table.waiter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Masa este asignată altui coleg")
        
    if not table.waiter_id:
        # Preluare implicită dacă nu era preluată
        table.waiter_id = current_user.id
        session.add(table)
        await manager.broadcast_to_role("waiter", {
            "event": "TABLE_CLAIMED",
            "table": table.number,
            "waiter_name": current_user.name
        })

    return await process_order_creation_logic(session, table, order, source="waiter")


@router.post("/tables/{table_id}/request-bill")
async def request_bill(table_id: int, request: BillRequest, session: Session = Depends(get_session)):
    """Clientul (sau chelnerul) cere nota de plată."""
    table = session.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Masa nu există")

    method_text = "Cash" if request.payment_method.lower() == "cash" else "POS/Card"
    msg = f"Masa {table.number} vrea nota. A pregătit {method_text}." if request.payment_method.lower() == "cash" else f"Masa {table.number} vrea nota. Du-te cu {method_text}."
    
    await manager.broadcast_to_role("waiter", {
        "event": "BILL_REQUESTED",
        "table": table.number,
        "target_waiter_id": table.waiter_id,
        "message": msg,
        "payment_method": request.payment_method.lower()
    })
    
    return {"status": "ok", "message": "Nota a fost cerută"}


@router.post("/tables/{table_id}/close", dependencies=[Depends(require_role(["Waiter", "Manager"]))])
async def close_table(table_id: int, session: Session = Depends(get_session)):
    """Închide masa: order=paid, masa=free, dezasignează chelnerul, deconectează clientul."""
    table = session.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Masa nu există")

    # Închidem comanda activă
    order = session.exec(
        select(Order)
        .where(Order.table_id == table_id)
        .where(Order.status.in_([OrderStatus.pending, OrderStatus.ready, OrderStatus.served]))
    ).first()

    if order:
        order.status = OrderStatus.paid
        session.add(order)

    # Eliberăm masa și chelnerul
    table.status = TableStatus.free
    table.waiter_id = None
    session.add(table)
    
    session.commit()

    # Deconectăm clienții de la masă prin trimiterea unui event WS specific
    await manager.broadcast_to_role("guest", {
        "event": "SESSION_CLOSED",
        "table": table.number
    })

    return {"status": "closed", "message": "Masa a fost închisă și eliberată"}


@router.get(
    "/waiter/tables/{table_id}/active-order",
    response_model=Optional[WaiterOrderRead],
    dependencies=[Depends(require_role(["Waiter", "Manager"]))]
)
async def get_waiter_table_active_order(table_id: int, session: Session = Depends(get_session)):
    """Returnează comanda activă (pending sau ready) a unei mese, dacă există."""
    # Prioritizăm comenzile pending sau ready (active)
    order = session.exec(
        select(Order)
        .where(Order.table_id == table_id)
        .where(Order.status.in_([OrderStatus.pending, OrderStatus.ready]))
        .order_by(Order.created_at.desc())
    ).first()

    if not order:
        return None

    order_items = session.exec(
        select(OrderItem).where(OrderItem.order_id == order.id)
    ).all()

    items = []
    for oi in order_items:
        menu_item = session.get(MenuItem, oi.menu_item_id)
        if menu_item:
            items.append(WaiterOrderItemRead(
                id=oi.id,
                name=menu_item.name,
                quantity=oi.quantity,
                status=oi.status.value,
                special_instructions=oi.special_instructions
            ))

    return WaiterOrderRead(
        id=order.id,
        status=order.status.value,
        total_price=order.total_price,
        items=items,
        notes=order.special_requests or ""
    )


@router.get(
    "/chef/active-orders",
    response_model=List[ChefOrderRead],
    dependencies=[Depends(require_role(["Chef", "Manager"]))]
)
async def get_chef_orders(session: Session = Depends(get_session)):
    """Returnează comenzile cu status 'pending' pentru KDS."""
    from core.ai import run_ai_kds_optimizer, run_ai_safety_agent

    orders = session.exec(
        select(Order)
        .where(Order.status == OrderStatus.pending)
        .order_by(Order.created_at)
    ).all()

    result = []
    for order in orders:
        table = session.get(Table, order.table_id)
        table_number = table.number if table else order.table_id

        order_items = session.exec(
            select(OrderItem).where(OrderItem.order_id == order.id)
        ).all()

        items = []
        items_for_ai = []
        for oi in order_items:
            menu_item = session.get(MenuItem, oi.menu_item_id)
            if menu_item:
                items.append(ChefOrderItemRead(
                    id=oi.id, 
                    name=menu_item.name, 
                    quantity=oi.quantity, 
                    status=oi.status.value,
                    special_instructions=oi.special_instructions
                ))
                items_for_ai.append({"prep_time": menu_item.prep_time_minutes or 10})

        cooking_strategy = run_ai_kds_optimizer(items_for_ai)
        urgency = run_ai_safety_agent(order.special_requests or "")

        result.append(ChefOrderRead(
            id=order.id,
            table_number=table_number,
            items=items,
            notes=order.special_requests or "",
            ai_metadata=AiMetadata(urgency=urgency, cooking_strategy=cooking_strategy)
        ))

    return result


@router.get(
    "/manager/stats",
    response_model=ManagerStats,
    dependencies=[Depends(require_role(["Manager"]))]
)
async def get_manager_stats(session: Session = Depends(get_session)):
    """Returnează statistici agregate din DB pentru dashboard-ul managerului."""
    orders = session.exec(select(Order)).all()
    total_revenue = round(sum(o.total_price for o in orders), 2)
    total_orders = len(orders)
    menu_items_count = len(session.exec(select(MenuItem)).all())

    return ManagerStats(
        total_revenue=total_revenue,
        total_orders=total_orders,
        menu_items_count=menu_items_count,
    )
