from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional
from pydantic import BaseModel

from core.security import require_role
from db.session import get_session
from models.table import Table, TableStatus
from models.order import Order, OrderStatus
from models.order_item import OrderItem
from models.menu_item import MenuItem

router = APIRouter(tags=["Dashboards RBAC"])


# ─── Schemas ───────────────────────────────────────────────────────────────────

class TableRead(BaseModel):
    id: int
    number: int
    capacity: int
    status: str
    location: Optional[str] = None


class TableStatusUpdate(BaseModel):
    status: TableStatus


class ChefOrderItemRead(BaseModel):
    name: str
    quantity: int


class AiMetadata(BaseModel):
    urgency: str
    cooking_strategy: str


class ChefOrderRead(BaseModel):
    id: int
    table_number: int
    items: List[ChefOrderItemRead]
    notes: str
    ai_metadata: AiMetadata


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
    tables = session.exec(select(Table).order_by(Table.number)).all()
    return [
        TableRead(
            id=t.id,
            number=t.number,
            capacity=t.capacity,
            status=t.status.value,
            location=t.location,
        )
        for t in tables
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
    return TableRead(
        id=table.id,
        number=table.number,
        capacity=table.capacity,
        status=table.status.value,
        location=table.location,
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
                items.append(ChefOrderItemRead(name=menu_item.name, quantity=oi.quantity))
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
