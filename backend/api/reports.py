from datetime import date, datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import Session, select, func
from sqlalchemy import cast, Date

from db.session import get_session
from models.user import User
from models.order import Order
from models.order_item import OrderItem
from models.menu_item import MenuItem
from core.security import require_role

router = APIRouter(prefix="/reports", tags=["Reports"])


class TopItemRead(BaseModel):
    name: str
    quantity_sold: int


class RevenueByDay(BaseModel):
    date: str
    revenue: float


class RangeReportRead(BaseModel):
    start_date: str
    end_date: str
    total_revenue: float
    total_orders: int
    average_order_value: float
    top_items: List[TopItemRead]
    revenue_by_day: List[RevenueByDay]


def _parse_date(d: Optional[str]) -> date:
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Format dată invalid: {d}. Folosește YYYY-MM-DD.")


def build_range_report(
    session: Session,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> RangeReportRead:
    """
    Calculează raportul de vânzări pe o perioadă (revenue, comenzi, top items, revenue/zi).

    Sursă unică de adevăr pentru raport — folosită atât de endpoint-ul /reports/range,
    cât și de agentul AI de insights (api/insights.py). Datele lipsă (None) cad pe ziua curentă.
    """
    today = datetime.now(timezone.utc).date()

    start = _parse_date(start_date) if start_date else today
    end = _parse_date(end_date) if end_date else today

    if start > end:
        start, end = end, start

    start_dt = datetime(start.year, start.month, start.day)
    end_dt = datetime(end.year, end.month, end.day, 23, 59, 59)

    date_range = Order.created_at.between(start_dt, end_dt)

    # Total revenue
    revenue_stmt = select(func.coalesce(func.sum(Order.total_price), 0)).where(date_range)
    total_revenue = float(session.exec(revenue_stmt).one())

    # Total orders
    count_stmt = select(func.count()).where(date_range)
    total_orders = int(session.exec(count_stmt).one())

    average_order_value = round(total_revenue / total_orders, 2) if total_orders > 0 else 0.0

    # Top 3 items
    top_stmt = (
        select(MenuItem.name, func.sum(OrderItem.quantity).label("qty"))
        .join(OrderItem, MenuItem.id == OrderItem.menu_item_id)
        .join(Order, OrderItem.order_id == Order.id)
        .where(date_range)
        .group_by(MenuItem.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(3)
    )
    top_rows = session.exec(top_stmt).all()
    top_items = [TopItemRead(name=str(row[0]), quantity_sold=int(row[1])) for row in top_rows]

    # Revenue by day
    day_stmt = (
        select(
            cast(Order.created_at, Date).label("day"),
            func.coalesce(func.sum(Order.total_price), 0).label("revenue")
        )
        .where(date_range)
        .group_by(cast(Order.created_at, Date))
        .order_by(cast(Order.created_at, Date))
    )
    day_rows = session.exec(day_stmt).all()
    revenue_by_day = [RevenueByDay(date=str(row[0]), revenue=float(row[1])) for row in day_rows]

    return RangeReportRead(
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        total_revenue=total_revenue,
        total_orders=total_orders,
        average_order_value=average_order_value,
        top_items=top_items,
        revenue_by_day=revenue_by_day,
    )


@router.get("/range", response_model=RangeReportRead)
async def get_range_report(
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(["Manager"]))
):
    """Raport pe o perioadă — doar Manager."""
    return build_range_report(session, start_date, end_date)
