import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from core.ai import (
    run_ai_kds_optimizer,
    run_ai_safety_agent,
    run_manager_insights_agent,
    run_menu_content_agent,
    clear_insights_session,
)

def test_run_ai_kds_optimizer_high_complexity():
    items = [{"prep_time": 15}, {"prep_time": 15}]
    result = run_ai_kds_optimizer(items)
    assert result == "HIGH_COMPLEXITY - Start Prep Immediately"

def test_run_ai_kds_optimizer_standard():
    items = [{"prep_time": 10}, {"prep_time": 10}]
    result = run_ai_kds_optimizer(items)
    assert result == "STANDARD_PRIORITY"

def test_run_ai_safety_agent_critical():
    notes = "Fara alune, are alergie severa"
    result = run_ai_safety_agent(notes)
    assert result == "CRITICAL"

def test_run_ai_safety_agent_normal():
    notes = "Vreau mai mult sos"
    result = run_ai_safety_agent(notes)
    assert result == "NORMAL"


# ============================================================================
# AGENT AI 3: Manager Analytics Agent
# ============================================================================

SAMPLE_REPORT = {
    "start_date": "2026-05-01",
    "end_date": "2026-05-07",
    "total_revenue": 1250.5,
    "total_orders": 40,
    "average_order_value": 31.26,
    "top_items": [{"name": "Burger", "quantity_sold": 25}],
    "revenue_by_day": [{"date": "2026-05-01", "revenue": 200.0}],
}


def _mock_client_returning(content: str):
    """Build an AsyncOpenAI-like mock whose completion returns `content`."""
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    choice.finish_reason = "stop"
    completion = MagicMock()
    completion.choices = [choice]
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=completion)
    return client


@pytest.mark.asyncio
async def test_insights_fallback_when_no_api_key():
    with patch("core.ai.settings.DEEPSEEK_API_KEY", None):
        result = await run_manager_insights_agent("Cum au fost vânzările?", "s1", SAMPLE_REPORT)
    assert result["agent"] == "fallback"
    assert result["session_id"] == "s1"
    assert isinstance(result["insights"], list) and result["insights"]
    # Rezumatul determinist trebuie să conțină cifra reală
    assert "1250.5" in result["response_text"]


@pytest.mark.asyncio
async def test_insights_agent_parses_model_json():
    payload = json.dumps({
        "response_text": "Vânzările au crescut.",
        "insights": ["Burger e cel mai vândut", "Venit 1250.5 RON"],
        "follow_up_question": "Vrei detalii pe zile?",
    })
    mock_client = _mock_client_returning(payload)
    clear_insights_session("s-json")
    with patch("core.ai.settings.DEEPSEEK_API_KEY", "fake-key"), \
         patch("core.ai.settings.USE_AI_RECOMMENDATIONS", True), \
         patch("core.ai.get_deepseek_client", return_value=mock_client):
        result = await run_manager_insights_agent("De ce a crescut?", "s-json", SAMPLE_REPORT)
    assert result["agent"] != "fallback"
    assert result["response_text"] == "Vânzările au crescut."
    assert result["insights"] == ["Burger e cel mai vândut", "Venit 1250.5 RON"]
    assert result["follow_up_question"] == "Vrei detalii pe zile?"


@pytest.mark.asyncio
async def test_insights_agent_session_history_accumulates():
    mock_client = _mock_client_returning(json.dumps({"response_text": "ok", "insights": []}))
    clear_insights_session("s-hist")
    with patch("core.ai.settings.DEEPSEEK_API_KEY", "fake-key"), \
         patch("core.ai.settings.USE_AI_RECOMMENDATIONS", True), \
         patch("core.ai.get_deepseek_client", return_value=mock_client):
        await run_manager_insights_agent("Q1", "s-hist", SAMPLE_REPORT)
        await run_manager_insights_agent("Q2", "s-hist", SAMPLE_REPORT)
    from core.ai import _insights_sessions
    # 2 mesaje user + 2 assistant
    assert len(_insights_sessions["s-hist"]) == 4


@pytest.mark.asyncio
async def test_insights_agent_falls_back_on_unparseable_response():
    mock_client = _mock_client_returning("not json at all, just prose")
    with patch("core.ai.settings.DEEPSEEK_API_KEY", "fake-key"), \
         patch("core.ai.settings.USE_AI_RECOMMENDATIONS", True), \
         patch("core.ai.get_deepseek_client", return_value=mock_client):
        result = await run_manager_insights_agent("Q", "s-bad", SAMPLE_REPORT)
    # _extract_json cade pe textul de recomandare meniu → tratat ca eșec → fallback insights
    assert result["agent"] == "fallback"


# ============================================================================
# AGENT AI 4: Menu Content Generator
# ============================================================================

@pytest.mark.asyncio
async def test_menu_content_fallback_when_no_api_key():
    with patch("core.ai.settings.DEEPSEEK_API_KEY", None):
        result = await run_menu_content_agent("Pizza Margherita", "rosii, mozzarella", ["Pizza"])
    assert result["agent"] == "fallback"
    assert "Pizza Margherita" in result["description"]
    # categoria sugerată e una existentă → nu e nouă
    assert result["suggested_category"]["is_new"] is False


@pytest.mark.asyncio
async def test_menu_content_recomputes_is_new_for_existing_category():
    # Modelul pretinde is_new=True pentru o categorie care de fapt EXISTĂ.
    payload = json.dumps({
        "description": "Pizza clasică italiană.",
        "dietary_tags": "vegetarian",
        "suggested_category": {"name": "pizza", "is_new": True},
        "price_band": {"min": 25, "max": 40},
        "prep_time_minutes": 15,
    })
    mock_client = _mock_client_returning(payload)
    with patch("core.ai.settings.DEEPSEEK_API_KEY", "fake-key"), \
         patch("core.ai.settings.USE_AI_RECOMMENDATIONS", True), \
         patch("core.ai.get_deepseek_client", return_value=mock_client):
        result = await run_menu_content_agent("Pizza Margherita", "rosii", ["Pizza", "Băuturi"])
    # Server recalculează: "pizza" se potrivește cu "Pizza" existentă → is_new False, nume normalizat
    assert result["suggested_category"]["is_new"] is False
    assert result["suggested_category"]["name"] == "Pizza"
    assert result["dietary_tags"] == "vegetarian"
    assert result["price_band"] == {"min": 25.0, "max": 40.0}
    assert result["prep_time_minutes"] == 15


@pytest.mark.asyncio
async def test_menu_content_tolerates_malformed_field_types():
    # Modelul întoarce suggested_category ca string și price_band ca listă —
    # tipuri greșite. Agentul nu trebuie să arunce descrierea bună la gunoi.
    payload = json.dumps({
        "description": "Salată proaspătă.",
        "dietary_tags": "vegan",
        "suggested_category": "Salate",   # string în loc de obiect
        "price_band": [10, 20],            # listă în loc de obiect
        "prep_time_minutes": "abc",        # ne-numeric
    })
    mock_client = _mock_client_returning(payload)
    with patch("core.ai.settings.DEEPSEEK_API_KEY", "fake-key"), \
         patch("core.ai.settings.USE_AI_RECOMMENDATIONS", True), \
         patch("core.ai.get_deepseek_client", return_value=mock_client):
        result = await run_menu_content_agent("Salată Caesar", "salată", ["Pizza"])
    # Păstrează descrierea (nu cade pe fallback), normalizează tipurile greșite.
    assert result["agent"] != "fallback"
    assert result["description"] == "Salată proaspătă."
    assert result["dietary_tags"] == "vegan"
    assert result["suggested_category"] == {"name": "Salate", "is_new": True}
    assert result["price_band"] == {"min": 0.0, "max": 0.0}
    assert result["prep_time_minutes"] is None


@pytest.mark.asyncio
async def test_menu_content_flags_genuinely_new_category():
    payload = json.dumps({
        "description": "Desert cremos.",
        "dietary_tags": "",
        "suggested_category": {"name": "Deserturi", "is_new": False},
        "price_band": {"min": 10, "max": 20},
        "prep_time_minutes": None,
    })
    mock_client = _mock_client_returning(payload)
    with patch("core.ai.settings.DEEPSEEK_API_KEY", "fake-key"), \
         patch("core.ai.settings.USE_AI_RECOMMENDATIONS", True), \
         patch("core.ai.get_deepseek_client", return_value=mock_client):
        result = await run_menu_content_agent("Tiramisu", "mascarpone", ["Pizza"])
    # "Deserturi" nu există în listă → is_new True, indiferent ce a zis modelul
    assert result["suggested_category"]["is_new"] is True
    assert result["suggested_category"]["name"] == "Deserturi"
