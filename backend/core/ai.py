from typing import List, Dict, Any
import json
from openai import AsyncOpenAI
from core.config import settings

# Existing stub functions (kept for compatibility)
def run_ai_kds_optimizer(items: List[dict]) -> str:
    """
    AGENT AI 1: Kitchen Optimizer.
    Analizează complexitatea produselor pentru a sugera prioritizarea.
    """
    total_prep_expected = sum([item.get("prep_time", 10) for item in items])
    if total_prep_expected > 25:
        return "HIGH_COMPLEXITY - Start Prep Immediately"
    return "STANDARD_PRIORITY"

def run_ai_safety_agent(notes: str) -> str:
    """
    AGENT AI 2: Safety & Urgency Agent.
    Detectează riscuri de sănătate sau solicitări urgente.
    """
    keywords = ["alergie", "allergy", "urgent", "copil", "baby"]
    if any(word in notes.lower() for word in keywords):
        return "CRITICAL"
    return "NORMAL"

# ============================================================================
# AI RECOMMENDATION AGENT (DeepSeek V3 / "4 Flash")
# ============================================================================

_deepseek_client = None
_chat_sessions: Dict[str, List[Dict]] = {}

def get_deepseek_client():
    """Initialize DeepSeek client lazily (OpenAI-compatible API)"""
    global _deepseek_client
    if _deepseek_client is None and settings.DEEPSEEK_API_KEY:
        _deepseek_client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )
    return _deepseek_client

async def run_chat_recommendation_agent(
    message: str,
    session_id: str,
    menu_items: List[Dict],
    past_orders: List = None
) -> Dict[str, Any]:
    """
    Chat-based AI agent that recommends dishes to customers.

    SAFETY: Only answers food/menu related questions.
    """
    if not settings.USE_AI_RECOMMENDATIONS or not settings.DEEPSEEK_API_KEY:
        return _fallback_chat_response(message, menu_items, session_id)

    # Build menu context
    menu_text = json.dumps([{
        "id": i["id"],
        "name": i["name"],
        "description": i.get("description", ""),
        "price": i.get("price"),
        "dietary_tags": i.get("dietary_tags", "")
    } for i in menu_items[:30]], indent=2)

    # System prompt with SAFETY GUARD
    system_prompt = f"""You are a restaurant AI assistant helping customers find dishes they'll love.

TODAY'S MENU:
{menu_text}

================================================================================
STRICT SAFETY GUARD - YOU MUST FOLLOW THESE RULES:
================================================================================

1. ONLY answer questions about:
   - Menu items and food descriptions
   - Dish recommendations based on preferences
   - Dietary advice (vegan, gluten-free, allergies)
   - Ingredients and allergens
   - Drink pairings with menu items
   - Restaurant services

2. If asked about ANYTHING ELSE (politics, coding, homework, general knowledge,
   medical diagnosis, personal advice, news, weather, etc.), you MUST respond
   EXACTLY with this message and NOTHING else:
   "I'm your food assistant and can only help with menu recommendations and dining advice. Is there something from our menu you'd like to know about?"

3. NEVER provide:
   - Medical advice beyond basic allergen information
   - Code or technical help
   - Opinions on non-food topics
   - Personal or career advice
   - General knowledge answers

4. Stay helpful but firmly within food/dining scope.

================================================================================
CONVERSATION STYLE:
================================================================================
- Be warm, conversational, and friendly (not robotic)
- Ask 1-2 clarifying questions before making recommendations
- When recommending, suggest 2-3 specific dishes with clear reasoning
- Include dish prices and brief descriptions
- Guide customers toward placing an order

Respond in this JSON format:
{{"response_text": "Your conversational reply", "suggested_dishes": [{{"item_id": 1, "name": "Dish Name", "reasoning": "Why this matches", "price": 15.99}}], "follow_up_question": "Ask something to continue the conversation or null"}}"""

    try:
        client = get_deepseek_client()
        if not client:
            return _fallback_chat_response(message, menu_items, session_id)

        # Call DeepSeek API (OpenAI-compatible)
        response = await client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            temperature=0.4,
            max_tokens=800
        )

        # Try to parse JSON response, fallback if model doesn't return valid JSON
        try:
            response_text = response.choices[0].message.content.strip()
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            result = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback: treat as plain text response
            result = {
                "response_text": response.choices[0].message.content,
                "suggested_dishes": [],
                "follow_up_question": None
            }

        # Update chat history
        chat_history = _chat_sessions.get(session_id, [])
        chat_history.append({"role": "user", "content": message})
        chat_history.append({"role": "assistant", "content": result.get("response_text", "")})
        _chat_sessions[session_id] = chat_history[-10:]  # Keep last 10 messages

        return {
            "response_text": result.get("response_text", ""),
            "suggested_dishes": result.get("suggested_dishes", []),
            "follow_up_question": result.get("follow_up_question"),
            "session_id": session_id,
            "agent": settings.DEEPSEEK_MODEL
        }

    except Exception as e:
        import traceback
        print(f"\n=== DeepSeek API Error ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {e}")
        print(f"\nFull traceback:")
        traceback.print_exc()
        print(f"=== End Error ===\n")
        return _fallback_chat_response(message, menu_items, session_id)

def _fallback_chat_response(message: str, menu_items: List[Dict], session_id: str = "") -> Dict[str, Any]:
    """Fallback when AI is unavailable - simple keyword matching"""
    message_lower = message.lower()
    keywords = message_lower.split()

    matched = []
    for item in menu_items[:5]:
        score = sum(1 for kw in keywords if kw in item.get("name", "").lower())
        if score > 0:
            matched.append({
                "item_id": item["id"],
                "name": item["name"],
                "reasoning": "Matches your request",
                "price": item.get("price"),
                "confidence": 0.7
            })

    if not matched:
        matched = [
            {"item_id": item["id"], "name": item["name"],
             "reasoning": "Popular choice", "price": item.get("price"), "confidence": 0.6}
            for item in menu_items[:3]
        ]

    return {
        "response_text": "Here are some dishes you might like:",
        "suggested_dishes": matched[:3],
        "follow_up_question": "Would you like to see more options?",
        "session_id": session_id,
        "agent": "fallback"
    }

def clear_chat_session(session_id: str):
    """Clear chat history for a session"""
    if session_id in _chat_sessions:
        del _chat_sessions[session_id]
