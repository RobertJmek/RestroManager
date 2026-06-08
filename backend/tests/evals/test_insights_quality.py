"""
Manager Insights Agent — REAL Evals (consume API tokens)

These call the LIVE DeepSeek model and score its actual output. They are OPT-IN:
they only run when RUN_AI_EVALS=1 (and a key is configured), so normal test runs
and CI stay free. Run them deliberately when you want to measure quality:

    RUN_AI_EVALS=1 pytest tests/evals/test_insights_quality.py -v -s

Deterministic regression tests for the same agent's plumbing (parsing, fallback,
prompt assembly) live in tests/unit/core/test_insights_agent.py and run for free.
"""

import os
import pytest

from core.config import settings
from core.ai import run_manager_insights_agent
from tests.evals.metrics import (
    grounding_score,
    report_numbers,
    extract_numbers,
    is_discount_of,
)


def _evals_enabled() -> bool:
    return bool(os.getenv("RUN_AI_EVALS")) and settings.USE_AI_RECOMMENDATIONS and bool(settings.DEEPSEEK_API_KEY)


pytestmark = [
    pytest.mark.eval,
    pytest.mark.skipif(
        not _evals_enabled(),
        reason="Real AI eval — set RUN_AI_EVALS=1 and configure DEEPSEEK_API_KEY to run (consumes tokens).",
    ),
]


# Relaxed targets — real model output is non-deterministic.
GROUNDING_TARGET = 0.80


class TestInsightsGroundingReal:
    @pytest.mark.asyncio
    async def test_summary_is_grounded(self, mock_report, mock_menu_prices):
        """A summary request should cite figures backed by the report, not invented ones."""
        result = await run_manager_insights_agent(
            message="Rezumă pe scurt vânzările din această perioadă.",
            session_id="eval-ins-ground",
            report_data=mock_report,
            menu_items=mock_menu_prices,
        )
        assert result["agent"] != "fallback", "model did not answer (fallback) — check API/key"

        allowed = report_numbers(mock_report)
        text = result["response_text"] + " " + " ".join(result["insights"])
        score = grounding_score(text, allowed)
        print(f"\n[insights] grounding score: {score:.2f}")
        assert score >= GROUNDING_TARGET, f"grounding {score:.2f} < {GROUNDING_TARGET}: {text}"

    @pytest.mark.asyncio
    async def test_missing_figure_is_not_invented(self, mock_report):
        """Asked about data it doesn't have (no menu prices given), it should not fabricate a price."""
        result = await run_manager_insights_agent(
            message="Care este prețul exact al unei Margherita Pizza?",
            session_id="eval-ins-missing",
            report_data=mock_report,
            menu_items=None,  # deliberately withhold prices
        )
        # The report carries no per-item price, so a confident "35 RON" would be a hallucination.
        # We don't hard-pin wording; we check it doesn't assert a specific RON price.
        text = result["response_text"].lower()
        hedged = any(k in text for k in ["nu am", "nu dețin", "nu este", "nu sunt", "lipsesc", "nu apar"])
        print(f"\n[insights] missing-data reply: {result['response_text'][:160]}")
        assert hedged or "ron" not in text, f"may have invented a price: {result['response_text']}"


class TestInsightsPricingReal:
    @pytest.mark.asyncio
    async def test_happy_hour_derives_from_real_price(self, mock_report, mock_menu_prices):
        """Happy-hour suggestion for a known item should relate to its real menu price."""
        pizza = next(i for i in mock_menu_prices if i["name"] == "Margherita Pizza")
        base = pizza["price"]  # 35.0
        result = await run_manager_insights_agent(
            message="Ce preț de happy hour ai sugera pentru Margherita Pizza? Dă o cifră concretă.",
            session_id="eval-ins-happyhour",
            report_data=mock_report,
            menu_items=mock_menu_prices,
        )
        assert result["agent"] != "fallback"
        nums = extract_numbers(result["response_text"] + " " + " ".join(result["insights"]))
        print(f"\n[insights] base={base} numbers={nums}")
        # At least one number should be the base price or a plausible discount of it.
        ok = any(abs(n - base) < 0.5 or is_discount_of(n, base) for n in nums)
        assert ok, f"no number related to real price {base}: {nums}"
