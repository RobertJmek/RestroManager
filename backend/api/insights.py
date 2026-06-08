from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from typing import Optional, List
from pydantic import BaseModel
from uuid import uuid4

from db.session import get_session
from models.user import User
from models.menu_item import MenuItem
from models.category import Category
from core.security import require_role
from core.ai import run_manager_insights_agent, clear_insights_session
from api.reports import build_range_report

router = APIRouter(prefix="/insights", tags=["Insights"])


class InsightsChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None  # Null pentru o conversație nouă
    start_date: Optional[str] = None  # YYYY-MM-DD; lipsă → ziua curentă
    end_date: Optional[str] = None


class ClearInsightsRequest(BaseModel):
    session_id: str


class InsightsChatResponse(BaseModel):
    response_text: str
    insights: List[str]
    follow_up_question: Optional[str] = None
    session_id: str
    agent: str


@router.post("/chat", response_model=InsightsChatResponse)
async def insights_chat(
    request: InsightsChatRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(["Manager"])),
):
    """
    Chat cu agentul AI de analiză pentru manager.
    Analizează raportul de vânzări din perioada selectată și răspunde în limbaj natural.
    """
    session_id = request.session_id or str(uuid4())

    report = build_range_report(session, request.start_date, request.end_date)

    # Prețurile curente din meniu — ca agentul să poată propune prețuri concrete
    # (ex: happy hour) pornind de la valoarea reală, nu inventată.
    menu_rows = session.exec(
        select(MenuItem.name, MenuItem.price, MenuItem.is_available, Category.name)
        .join(Category, MenuItem.category_id == Category.id)
        .order_by(Category.name, MenuItem.name)
    ).all()
    menu_items = [
        {"name": row[0], "price": row[1], "is_available": row[2], "category": row[3]}
        for row in menu_rows
    ]

    response = await run_manager_insights_agent(
        message=request.message,
        session_id=session_id,
        report_data=report.model_dump(),
        menu_items=menu_items,
    )

    return InsightsChatResponse(**response)


@router.post("/chat/clear")
async def clear_insights_chat(
    request: ClearInsightsRequest,
    current_user: User = Depends(require_role(["Manager"])),
):
    """Șterge sesiunea de chat de insights."""
    clear_insights_session(request.session_id)
    return {"status": "cleared"}
