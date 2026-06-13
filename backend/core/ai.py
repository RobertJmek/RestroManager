from typing import List, Dict, Any
import json
import re
from openai import AsyncOpenAI
from core.config import settings

# ============================================================================
# AI RECOMMENDATION AGENT (DeepSeek V3 / "4 Flash")
# ============================================================================

_deepseek_client = None
_chat_sessions: Dict[str, List[Dict]] = {}

# Câte feluri poate conține o sugestie. Nu mai impunem un număr fix (1 fel sau 5,
# depinde de cerere) — lăsăm agentul să decidă. Plafonul e doar o plasă de
# siguranță ca modelul să nu întoarcă tot meniul deodată.
MAX_SUGGESTED_DISHES = 8

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
- When recommending, suggest only the dishes that genuinely fit the request, each with clear reasoning
- Include dish prices and brief descriptions
- Guide customers toward placing an order
- Keep response_text concise (max ~4 sentences). In suggested_dishes include exactly the dishes you actually recommend — there is no fixed count, it may be one or several; pick only what truly fits and never pad the list
- Reply in the same language the customer used

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

        # Call DeepSeek API (OpenAI-compatible) with full conversation context.
        # Chiar și cu JSON mode, modelul scapă ocazional un răspuns gol/netparsabil
        # pe câte un tur (mai ales multi-tur). Reîncercăm o dată înainte de fallback:
        # un singur retry rezolvă marea majoritate a acestor rateuri intermitente.
        result = None
        for attempt in range(2):
            response = await client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=messages,
                temperature=0.4,
                # 800 era prea puțin: la cereri în română cu mai multe feluri, JSON-ul
                # se tăia la mijloc și parsarea pica → fallback. 1500 lasă spațiu să se
                # închidă obiectul (output-ul e oricum plafonat la 3 feluri prin prompt).
                max_tokens=1500,
                # JSON mode: pe conversațiile multi-tur modelul „aluneca" în proză liberă
                # (răspunsul pe turul 2+ nu mai conținea JSON → parse fail → fallback).
                # Forțează emiterea unui obiect JSON valid. Promptul conține deja "JSON".
                response_format={"type": "json_object"},
            )

            # Parse JSON robustly (modelul adaugă des proză în jurul JSON-ului, mai ales
            # la cereri complexe). _extract_json izolează obiectul {...} din răspuns.
            raw_content = response.choices[0].message.content or ""
            parsed = _extract_json(raw_content)
            if parsed and isinstance(parsed, dict):
                result = parsed
                break

        if result is None:
            # SAFETY: Return safe fallback instead of arbitrary model output
            # This prevents off-topic/unsafe content from leaking through.
            # Formulare neutră, fără salut — un salut („what are you in the mood for?")
            # în mijlocul conversației pare că botul și-a șters memoria și a resetat.
            result = {
                "response_text": "Sorry, I didn't quite catch that — could you rephrase? I can suggest dishes or drink pairings that fit what you're after.",
                "suggested_dishes": [],
                "follow_up_question": None
            }

        # Validate and sanitize AI suggestions against actual menu items
        valid_menu_ids = {item["id"] for item in menu_items}
        menu_lookup = {item["id"]: item for item in menu_items}
        
        # Fără număr fix de sugestii — doar plafonul de siguranță (vezi MAX_SUGGESTED_DISHES).
        raw_suggestions = result.get("suggested_dishes", [])[:MAX_SUGGESTED_DISHES]
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
    for item in menu_items:  # Scan the whole menu; MAX_SUGGESTED_DISHES caps the result
        name_lower = item.get("name", "").lower()
        tags_lower = " ".join(item.get("dietary_tags") or []).lower()
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
        "suggested_dishes": matched[:MAX_SUGGESTED_DISHES],
        "follow_up_question": "Would you like more details about any of these?",
        "session_id": session_id,
        "agent": "fallback"
    }

def clear_chat_session(session_id: str):
    """Clear chat history for a session"""
    if session_id in _chat_sessions:
        del _chat_sessions[session_id]


def _extract_json(raw: str):
    """
    Extrage primul obiect JSON dintr-un răspuns al modelului. Întoarce dict sau
    None dacă nu se poate parsa (apelantul decide ce fallback folosește).

    Strategie: parse direct → strip code-fence ```json ... ``` → scanare cu
    echilibrare de acolade pentru a izola exact blocul {...} din proză.
    """
    if not raw:
        return None
    text = raw.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass

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
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        return None
    return None


# ============================================================================
# AGENT AI 3: MANAGER ANALYTICS AGENT (conversational, session-based)
# ============================================================================
# Răspunde managerului la întrebări în limbaj natural despre datele de vânzări
# (revenue, comenzi, top produse). Folosește același client DeepSeek + _extract_json.

# Istoric separat de cel al clienților (_chat_sessions) ca să nu se amestece sesiunile.
_insights_sessions: Dict[str, List[Dict]] = {}


def _format_report_for_prompt(report: Dict[str, Any]) -> str:
    """Compactează raportul într-un text lizibil pentru promptul modelului."""
    top = ", ".join(
        f"{t.get('name')} ({t.get('quantity_sold')} buc)"
        for t in report.get("top_items", [])
    ) or "fără date"
    by_day = ", ".join(
        f"{d.get('date')}: {d.get('revenue')} RON"
        for d in report.get("revenue_by_day", [])
    ) or "fără date"
    return (
        f"Perioadă: {report.get('start_date')} → {report.get('end_date')}\n"
        f"Venit total: {report.get('total_revenue')} RON\n"
        f"Număr comenzi: {report.get('total_orders')}\n"
        f"Valoare medie comandă: {report.get('average_order_value')} RON\n"
        f"Top produse: {top}\n"
        f"Venit pe zile: {by_day}"
    )


def _format_menu_for_prompt(menu_items: List[Dict[str, Any]]) -> str:
    """
    Listă compactă cu prețul curent al fiecărui produs, pentru ca agentul să poată
    sugera prețuri concrete (ex: happy hour) fără să inventeze valoarea de bază.
    """
    if not menu_items:
        return ""
    lines = []
    for it in menu_items:
        cat = it.get("category")
        cat_txt = f" [{cat}]" if cat else ""
        avail = "" if it.get("is_available", True) else " (indisponibil)"
        lines.append(f"- {it.get('name')}{cat_txt}: {it.get('price')} RON{avail}")
    return "PREȚURI MENIU (preț curent per produs):\n" + "\n".join(lines)


def _insights_fallback(report: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """Rezumat determinist al cifrelor când AI-ul nu e disponibil (fără API key)."""
    insights = [
        f"Venit total {report.get('total_revenue')} RON din {report.get('total_orders')} comenzi.",
        f"Valoare medie pe comandă: {report.get('average_order_value')} RON.",
    ]
    top_items = report.get("top_items", [])
    if top_items:
        insights.append(f"Cel mai vândut produs: {top_items[0].get('name')}.")
    return {
        "response_text": (
            "Asistentul AI nu este configurat momentan. Iată un rezumat al perioadei:\n"
            + "\n".join(f"• {i}" for i in insights)
        ),
        "insights": insights,
        "follow_up_question": None,
        "session_id": session_id,
        "agent": "fallback",
    }


async def run_manager_insights_agent(
    message: str,
    session_id: str,
    report_data: Dict[str, Any],
    menu_items: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Agent conversațional care analizează raportul de vânzări pentru manager.

    SAFETY: răspunde DOAR despre datele/operațiunile acestui restaurant.
    Păstrează istoricul conversației per session_id (ultimele 10 mesaje).

    `menu_items` (opțional): listă cu prețul curent al produselor, ca agentul să
    poată sugera prețuri concrete (ex: happy hour) fără să inventeze valoarea de bază.
    """
    if not settings.USE_AI_RECOMMENDATIONS or not settings.DEEPSEEK_API_KEY:
        return _insights_fallback(report_data, session_id)

    client = get_deepseek_client()
    if not client:
        return _insights_fallback(report_data, session_id)

    menu_section = _format_menu_for_prompt(menu_items)
    menu_block = f"\n\n{menu_section}" if menu_section else ""

    system_prompt = f"""Ești un analist de business pentru un restaurant. Ajuți managerul să înțeleagă datele de vânzări.

DATELE DE VÂNZĂRI PENTRU PERIOADA SELECTATĂ:
{_format_report_for_prompt(report_data)}{menu_block}

================================================================================
REGULI STRICTE:
================================================================================
1. Răspunde DOAR despre aceste date de vânzări și despre operațiunile restaurantului
   (venituri, comenzi, produse populare, tendințe, sugestii de promovare/meniu).
2. Nu inventa cifre — folosește doar datele de mai sus. Dacă o cifră lipsește, spune asta.
   Pentru sugestii de preț (ex: happy hour, reduceri) pornește de la prețul curent din
   lista de prețuri a meniului și aplică reducerea, indicând atât prețul nou cât și procentul.
3. Fii concis și concret. Oferă observații acționabile.

Răspunde în acest format JSON:
{{"response_text": "Răspunsul tău conversațional", "insights": ["observație 1", "observație 2"], "follow_up_question": "O întrebare de continuare sau null"}}"""

    try:
        history = _insights_sessions.get(session_id, [])
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            if msg["role"] in ["user", "assistant"]:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": message})

        response = await client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=1200,
            # Același motiv ca la agentul de client: pe conversații multi-tur modelul
            # poate aluneca în proză fără JSON. Forțăm un obiect JSON valid.
            response_format={"type": "json_object"},
        )
        raw_content = response.choices[0].message.content or ""
        result = _extract_json(raw_content)

        # Parse eșuat sau răspuns gol → rezumat determinist.
        if not result or not result.get("response_text"):
            return _insights_fallback(report_data, session_id)
        response_text = result["response_text"]

        insights = result.get("insights", [])
        if not isinstance(insights, list):
            insights = []

        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response_text})
        _insights_sessions[session_id] = history[-10:]

        return {
            "response_text": response_text,
            "insights": [str(i) for i in insights],
            "follow_up_question": result.get("follow_up_question"),
            "session_id": session_id,
            "agent": settings.DEEPSEEK_MODEL,
        }
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Manager insights agent error: %s", e)
        return _insights_fallback(report_data, session_id)


def clear_insights_session(session_id: str):
    """Șterge istoricul conversației de insights pentru o sesiune."""
    if session_id in _insights_sessions:
        del _insights_sessions[session_id]


# ============================================================================
# AGENT AI 4: MENU CONTENT GENERATOR (single-shot, non-destructiv)
# ============================================================================
# Pentru manager: generează descriere, etichete dietetice, categorie sugerată și
# interval de preț pentru un produs nou, pornind de la nume + ingrediente.

def _menu_content_fallback(
    name: str,
    ingredients: str,
    existing_categories: List[str],
) -> Dict[str, Any]:
    """Sugestie template când AI-ul nu e disponibil."""
    desc = f"{name} preparat cu {ingredients}." if ingredients else f"{name} — preparatul casei."
    return {
        "description": desc[:500],
        "dietary_tags": "",
        "suggested_category": {
            "name": existing_categories[0] if existing_categories else "General",
            "is_new": not bool(existing_categories),
        },
        "price_band": {"min": 0.0, "max": 0.0},
        "prep_time_minutes": None,
        "agent": "fallback",
    }


async def run_menu_content_agent(
    name: str,
    ingredients: str = "",
    existing_categories: List[str] = None,
    price_hint: float = None,
) -> Dict[str, Any]:
    """
    Generează conținut pentru un produs de meniu (single-shot).

    Returnează descriere, etichete dietetice, categorie sugerată (cu flag is_new
    recalculat pe server) și interval de preț. NU scrie nimic în baza de date.
    """
    existing_categories = existing_categories or []

    def _finalize(result: Dict[str, Any], agent: str) -> Dict[str, Any]:
        """Validează output-ul: recalculează is_new față de categoriile reale."""
        # Modelul poate întoarce câmpuri cu tipuri neașteptate (string în loc de
        # obiect) — tolerăm asta ca să nu pierdem o descriere altfel bună.
        cat = result.get("suggested_category")
        if isinstance(cat, dict):
            cat_name = (cat.get("name") or "").strip()
        elif isinstance(cat, str):
            cat_name = cat.strip()
        else:
            cat_name = ""
        cat_name = cat_name or (existing_categories[0] if existing_categories else "General")
        # Sursa de adevăr pentru is_new e lista reală, nu ce zice modelul.
        lookup = {c.lower(): c for c in existing_categories}
        if cat_name.lower() in lookup:
            cat_name = lookup[cat_name.lower()]
            is_new = False
        else:
            is_new = True
        band = result.get("price_band")
        if not isinstance(band, dict):
            band = {}
        try:
            band_min = round(float(band.get("min", 0.0)), 2)
            band_max = round(float(band.get("max", 0.0)), 2)
        except (TypeError, ValueError):
            band_min = band_max = 0.0
        prep = result.get("prep_time_minutes")
        try:
            prep = int(prep) if prep is not None else None
        except (TypeError, ValueError):
            prep = None
        return {
            "description": str(result.get("description", ""))[:500],
            "dietary_tags": str(result.get("dietary_tags", ""))[:255],
            "suggested_category": {"name": cat_name, "is_new": is_new},
            "price_band": {"min": band_min, "max": band_max},
            "prep_time_minutes": prep,
            "agent": agent,
        }

    if not settings.USE_AI_RECOMMENDATIONS or not settings.DEEPSEEK_API_KEY:
        return _menu_content_fallback(name, ingredients, existing_categories)

    client = get_deepseek_client()
    if not client:
        return _menu_content_fallback(name, ingredients, existing_categories)

    categories_text = ", ".join(existing_categories) if existing_categories else "(niciuna încă)"
    price_text = f"\nPreț orientativ sugerat de manager: {price_hint} RON" if price_hint else ""
    system_prompt = f"""Ești un copywriter culinar care creează conținut pentru meniul unui restaurant.

CATEGORII EXISTENTE: {categories_text}

Pentru produsul dat (nume + ingrediente), generează:
- O descriere atrăgătoare pentru clienți (max 400 caractere).
- Etichete dietetice/alergeni relevante, separate prin virgulă (ex: "vegetarian, fără gluten, conține nuci"). Lasă "" dacă nu e cazul.
- Categoria potrivită: alege din categoriile existente dacă se potrivește una, altfel propune un nume nou.
- Un interval de preț estimat în RON (min/max).
- Timp de preparare estimat în minute (sau null).

Răspunde DOAR cu JSON în acest format:
{{"description": "...", "dietary_tags": "...", "suggested_category": {{"name": "...", "is_new": true}}, "price_band": {{"min": 0.0, "max": 0.0}}, "prep_time_minutes": 15}}"""

    user_prompt = f"Nume produs: {name}\nIngrediente: {ingredients or 'nespecificate'}{price_text}"

    try:
        response = await client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
            max_tokens=800,
        )
        raw_content = response.choices[0].message.content or ""
        result = _extract_json(raw_content)
        if not result or not result.get("description"):
            return _menu_content_fallback(name, ingredients, existing_categories)
        return _finalize(result, settings.DEEPSEEK_MODEL)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Menu content agent error: %s", e)
        return _menu_content_fallback(name, ingredients, existing_categories)
