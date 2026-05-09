from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from typing import Optional, List
from pydantic import BaseModel
from uuid import uuid4

from db.session import get_session
from models.menu_item import MenuItem
from core.security import get_current_user_optional
from core.ai import run_chat_recommendation_agent, clear_chat_session

router = APIRouter(prefix="/recommendations")


class ChatRecommendationRequest(BaseModel):
    message: str
    session_id: Optional[str] = None  # Null for new chat


class ClearChatRequest(BaseModel):
    session_id: str


class SuggestedDish(BaseModel):
    item_id: int
    name: str
    reasoning: str
    price: float
    confidence: Optional[float] = None


class ChatRecommendationResponse(BaseModel):
    response_text: str
    suggested_dishes: List[SuggestedDish]
    follow_up_question: Optional[str] = None
    session_id: str
    agent: str


@router.post("/chat", response_model=ChatRecommendationResponse)
async def chat_recommendations(
    request: ChatRecommendationRequest,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user_optional)
):
    """
    Chat with AI to get personalized dish recommendations.
    Maintains conversation history per session.
    """
    # Generate session ID if new chat
    session_id = request.session_id or str(uuid4())

    # Fetch available menu items
    menu_items = session.exec(
        select(MenuItem).where(MenuItem.is_available == True)
    ).all()

    # Run chat-based recommendation agent
    response = await run_chat_recommendation_agent(
        message=request.message,
        session_id=session_id,
        menu_items=[{
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "price": item.price,
            "dietary_tags": item.dietary_tags
        } for item in menu_items],
        past_orders=[]  # Simplified - can be extended with order history
    )

    return ChatRecommendationResponse(**response)


@router.post("/chat/clear")
async def clear_chat(
    request: ClearChatRequest,
    current_user = Depends(get_current_user_optional)
):
    """Clear chat session (call when customer places order or starts new session)"""
    clear_chat_session(request.session_id)
    return {"status": "cleared"}
