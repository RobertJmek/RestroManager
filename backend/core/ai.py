from typing import List, Dict, Any
import json
import re
from openai import AsyncOpenAI
from core.config import settings

# Existing stub functions (kept for compatibility)
def run_ai_kds_optimizer(items: List[dict]) -> str:
    """
    AGENT AI 1: Kitchen Optimizer.
    Analizează complexitatea produselor pentru a sugera prioritizarea.
    """
    total_prep_expected = sum([item.get("prep_time") if item.get("prep_time") is not None else 10 for item in items])
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

_FALLBACK_RESULT = {
    "response_text": "I'm here to help you find great dishes from our menu! What type of food are you in the mood for today?",
    "suggested_dishes": [],
    "follow_up_question": None,
}


def _extract_json(raw: str) -> dict:
    """
    Robustly extract the first JSON object from a model response.

    Strategy (in order):
    1. Direct parse — the response is clean JSON already.
    2. Strip a single ```json ... ``` or ``` ... ``` fence, then parse.
    3. Regex scan — find the first '{' and walk forward tracking brace depth
       so we pull out exactly the outermost {...} block regardless of surrounding prose.
    4. Fallback — return the safe default so the conversation can continue.
    """
    text = raw.strip()

    # 1. Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Strip a code fence
    fence_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
    fence_match = fence_pattern.search(text)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # 3. Brace-balanced extraction — handles JSON embedded in prose
    start = text.find("{")
    if start != -1:
        depth = 0
        in_string = False
        escape_next = False
        for i, ch in enumerate(text[start:], start=start):
            if escape_next:
                escape_next = False
                continue
            if ch == "\\" and in_string:
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break  # Malformed JSON — fall through to fallback

    # 4. Safe fallback
    import logging
    logging.getLogger(__name__).warning(
        "DeepSeek JSON parse failed — raw response was: %r", raw[:500]
    )
    return dict(_FALLBACK_RESULT)


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
   - Menu items and food descriptions,prices dietary info,allergens info
   - Dish recommendations based on preferences
   - Dietary advice (vegan, gluten-free, allergies)
   - Ingredients and allergens
   - Drink pairings with menu items
   - Restaurant services

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

        # Build messages array with system prompt + conversation history + current message
        chat_history = _chat_sessions.get(session_id, [])
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add previous conversation history (already capped at last 10)
        for msg in chat_history:
            # Map our stored roles to OpenAI roles (user/assistant)
            role = msg["role"]
            if role in ["user", "assistant"]:
                messages.append({"role": role, "content": msg["content"]})
        
        # Add current user message
        messages.append({"role": "user", "content": message})

        # Call DeepSeek API (OpenAI-compatible) with full conversation context
        response = await client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=messages,
            temperature=0.4,
            max_tokens=1500  # Increased from 800 — Romanian responses were truncating the JSON object
        )

        # Detect truncation before attempting to parse — a cut-off response will never be valid JSON
        import logging as _logging
        finish_reason = response.choices[0].finish_reason
        raw_content = response.choices[0].message.content or ""
        if finish_reason == "length":
            _logging.getLogger(__name__).warning(
                "DeepSeek response truncated (finish_reason='length'). "
                "Consider raising max_tokens further. Raw tail: %r",
                raw_content[-200:]
            )

        # Robust JSON extraction: find the first {...} block anywhere in the response,
        # regardless of surrounding markdown fences, prose, or extra whitespace.
        result = _extract_json(raw_content)

        # Validate and sanitize AI suggestions against actual menu items
        valid_menu_ids = {item["id"] for item in menu_items}
        menu_lookup = {item["id"]: item for item in menu_items}
        
        raw_suggestions = result.get("suggested_dishes", [])[:3]  # Limit to max 3
        validated_dishes = []
        
        for suggestion in raw_suggestions:
            item_id = suggestion.get("item_id")
            
            # Skip if item_id is not in current menu
            if item_id not in valid_menu_ids:
                continue
            
            # Use actual menu data (overwrite AI's potentially hallucinated name/price)
            menu_item = menu_lookup[item_id]
            validated_dishes.append({
                "item_id": item_id,
                "name": menu_item["name"],  # From DB, not AI
                "reasoning": suggestion.get("reasoning", "Recommended for you"),
                "price": menu_item.get("price", 0),  # From DB, not AI
            })
        
        # Update chat history
        chat_history = _chat_sessions.get(session_id, [])
        chat_history.append({"role": "user", "content": message})
        
        # If no valid dishes but we have a valid AI response, still show the conversation
        # Only use fallback if DeepSeek completely failed to give a useful response
        if not validated_dishes and not result.get("response_text"):
            _chat_sessions[session_id] = chat_history[-10:]
            return _fallback_chat_response(message, menu_items, session_id)
        
        chat_history.append({"role": "assistant", "content": result.get("response_text", "")})
        _chat_sessions[session_id] = chat_history[-10:]  # Keep last 10 messages

        return {
            "response_text": result.get("response_text", ""),
            "suggested_dishes": validated_dishes,
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
    for item in menu_items[:10]:  # Check more items
        name_lower = item.get("name", "").lower()
        tags_lower = " ".join(item.get("dietary_tags", [])).lower()
        desc_lower = item.get("description", "").lower()
        
        # Score from name, tags, and description
        score = sum(1 for kw in keywords if kw in name_lower)
        score += sum(0.5 for kw in keywords if kw in tags_lower)  # Partial score for tags
        score += sum(0.3 for kw in keywords if kw in desc_lower)   # Partial score for description
        
        if score > 0:
            matched.append({
                "item_id": item["id"],
                "name": item["name"],
                "reasoning": "Matches your request",
                "price": item.get("price"),
                "confidence": min(score * 0.3, 0.9),
                "score": score  # For sorting
            })
    
    # Sort by score descending
    matched.sort(key=lambda x: x.get("score", 0), reverse=True)

    # If no keyword matches, use menu items or generic fallback
    if not matched:
        if menu_items:
            # Use first 3 items from menu as popular choices
            matched = [{
                "item_id": item["id"],
                "name": item["name"],
                "reasoning": "Popular choice",
                "price": item.get("price", 0)
            } for item in menu_items[:3]]
        else:
            # No menu items available, use generic suggestion
            matched = [{
                "item_id": 1,
                "name": "Chef's Special",
                "reasoning": "Ask your server for today's special!",
                "price": 0
            }]
    
    # Build response text
    dish_text = "\n\n".join([f"{d['name']}\n{d['price']} RON\n{d['reasoning']}" for d in matched])
    response_text = f"Here are some dishes you might like:\n\n{dish_text}"
    
    return {
        "response_text": response_text,
        "suggested_dishes": matched[:3],
        "follow_up_question": "Would you like more details about any of these?",
        "session_id": session_id,
        "agent": "fallback"
    }

def clear_chat_session(session_id: str):
    """Clear chat history for a session"""
    if session_id in _chat_sessions:
        del _chat_sessions[session_id]
