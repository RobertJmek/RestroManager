"""
Manager Insights Agent Evaluation Tests

Evaluates the conversational sales-analysis agent (run_manager_insights_agent):
- Grounding/faithfulness: cites only figures present in the report (no hallucination)
- Pricing: happy-hour/discount suggestions are derived from real menu prices
  (regression for the bug where the agent had no prices and answered generically)
- Robustness: parses JSON wrapped in prose; falls back safely on garbage
- Multi-turn: conversation history is retained per session
- Fallback: deterministic summary when AI is disabled

All tests are deterministic and make NO real API calls (the DeepSeek client is
mocked or fallback mode is forced).
"""

import json
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from core.ai import run_manager_insights_agent, _format_report_for_prompt
from tests.evals.conftest import make_mock_deepseek
from tests.evals.metrics import grounding_score, report_numbers, is_discount_of


GROUNDING_TARGET = 0.99  # insights must not invent figures


@contextmanager
def mocked_ai(content: str, capture=None):
    """Force the AI path on and route it through a mock DeepSeek client."""
    with patch("core.ai.settings.USE_AI_RECOMMENDATIONS", True), \
         patch("core.ai.settings.DEEPSEEK_API_KEY", "test-key"), \
         patch("core.ai.settings.DEEPSEEK_MODEL", "deepseek-test"), \
         patch("core.ai.get_deepseek_client", return_value=make_mock_deepseek(content, capture)):
        yield


class TestInsightsGrounding:
    """The agent must answer only from the data it was given."""

    @pytest.mark.asyncio
    async def test_fallback_numbers_are_grounded(self, mock_report):
        """Fallback summary cites only figures present in the report."""
        with patch("core.ai.settings.USE_AI_RECOMMENDATIONS", False):
            result = await run_manager_insights_agent(
                message="Cum au fost vânzările?",
                session_id="ins-fallback-001",
                report_data=mock_report,
            )

        assert result["agent"] == "fallback"
        allowed = report_numbers(mock_report)
        text = result["response_text"] + " " + " ".join(result["insights"])
        score = grounding_score(text, allowed)
        assert score >= GROUNDING_TARGET, f"Fallback grounding {score:.2f} < {GROUNDING_TARGET}"

    @pytest.mark.asyncio
    async def test_ai_response_numbers_are_grounded(self, mock_report, mock_menu_prices):
        """A well-behaved AI answer that cites report figures scores fully grounded."""
        content = json.dumps({
            "response_text": "Venit total 4520.0 RON din 128 comenzi, valoare medie 35.31 RON.",
            "insights": ["Margherita Pizza s-a vândut în 64 de porții."],
            "follow_up_question": None,
        })
        with mocked_ai(content):
            result = await run_manager_insights_agent(
                message="Rezumă perioada",
                session_id="ins-ground-001",
                report_data=mock_report,
                menu_items=mock_menu_prices,
            )

        allowed = report_numbers(mock_report)
        text = result["response_text"] + " " + " ".join(result["insights"])
        assert grounding_score(text, allowed) >= GROUNDING_TARGET


class TestInsightsPricing:
    """Regression: agent must have menu prices and use them for price suggestions."""

    @pytest.mark.asyncio
    async def test_menu_prices_reach_the_prompt(self, mock_report, mock_menu_prices):
        """Every menu item name + price must appear in the system prompt."""
        capture = []
        content = json.dumps({"response_text": "ok", "insights": [], "follow_up_question": None})
        with mocked_ai(content, capture=capture):
            await run_manager_insights_agent(
                message="Ce preț de happy hour la Margherita Pizza?",
                session_id="ins-price-001",
                report_data=mock_report,
                menu_items=mock_menu_prices,
            )

        system_prompt = capture[0]["messages"][0]["content"]
        for item in mock_menu_prices:
            assert item["name"] in system_prompt, f"{item['name']} missing from prompt"
            assert str(item["price"]) in system_prompt, f"price of {item['name']} missing"

    @pytest.mark.asyncio
    async def test_happy_hour_price_is_discount_of_real_price(self, mock_report, mock_menu_prices):
        """A suggested happy-hour price should be a plausible discount of the menu price."""
        pizza = next(i for i in mock_menu_prices if i["name"] == "Margherita Pizza")
        base = pizza["price"]  # 35.0
        suggested = round(base * 0.8, 2)  # 20% off → 28.0
        content = json.dumps({
            "response_text": f"Pentru happy hour la Margherita Pizza propun {suggested} RON (−20% de la {base} RON).",
            "insights": [f"Reducere 20% la Margherita Pizza: {suggested} RON."],
            "follow_up_question": None,
        })
        with mocked_ai(content):
            result = await run_manager_insights_agent(
                message="Sugerează un preț de happy hour pentru Margherita Pizza",
                session_id="ins-price-002",
                report_data=mock_report,
                menu_items=mock_menu_prices,
            )

        assert is_discount_of(suggested, base), "suggested price not a plausible discount"
        assert str(suggested) in result["response_text"]


class TestInsightsRobustness:
    """Parsing resilience and safe degradation."""

    @pytest.mark.asyncio
    async def test_prose_wrapped_json_is_parsed(self, mock_report):
        """JSON surrounded by prose is still extracted (not dumped to fallback)."""
        content = (
            "Sigur, iată analiza:\n```json\n"
            + json.dumps({"response_text": "Venit bun.", "insights": ["ok"], "follow_up_question": None})
            + "\n```\nSper că ajută!"
        )
        with mocked_ai(content):
            result = await run_manager_insights_agent(
                message="analiză",
                session_id="ins-robust-001",
                report_data=mock_report,
            )

        assert result["agent"] != "fallback"
        assert result["response_text"] == "Venit bun."

    @pytest.mark.asyncio
    async def test_unparseable_output_falls_back(self, mock_report):
        """Non-JSON model output degrades to the deterministic summary."""
        with mocked_ai("îmi pare rău, nu am înțeles"):
            result = await run_manager_insights_agent(
                message="analiză",
                session_id="ins-robust-002",
                report_data=mock_report,
            )

        assert result["agent"] == "fallback"

    @pytest.mark.asyncio
    async def test_multi_turn_history_retained(self, mock_report):
        """Second turn in a session sends the first turn back as context."""
        capture = []
        content = json.dumps({"response_text": "răspuns", "insights": [], "follow_up_question": None})
        with mocked_ai(content, capture=capture):
            sid = "ins-history-001"
            await run_manager_insights_agent("prima întrebare", sid, mock_report)
            await run_manager_insights_agent("a doua întrebare", sid, mock_report)

        second_call_messages = capture[1]["messages"]
        contents = [m["content"] for m in second_call_messages]
        assert "prima întrebare" in contents, "first user turn not replayed on turn 2"
        assert "răspuns" in contents, "first assistant turn not replayed on turn 2"


class TestInsightsStructure:
    """Response shape contract used by the API/frontend."""

    @pytest.mark.asyncio
    async def test_response_fields_present(self, mock_report):
        with patch("core.ai.settings.USE_AI_RECOMMENDATIONS", False):
            result = await run_manager_insights_agent(
                message="rezumat", session_id="ins-struct-001", report_data=mock_report
            )
        for field in ("response_text", "insights", "follow_up_question", "session_id", "agent"):
            assert field in result
        assert isinstance(result["insights"], list)

    def test_report_formatter_includes_key_figures(self, mock_report):
        text = _format_report_for_prompt(mock_report)
        assert "4520.0" in text
        assert "128" in text
        assert "Margherita Pizza" in text
