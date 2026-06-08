"""
Menu Content Generator Agent — REAL Evals (consume API tokens)

Calls the LIVE model to generate content for a new menu item and scores the
result. OPT-IN via RUN_AI_EVALS=1:

    RUN_AI_EVALS=1 pytest tests/evals/test_menu_content_quality.py -v -s

Deterministic regression tests for the validation boundary (is_new recompute,
field clamping, fallback) live in tests/unit/core/test_menu_content_agent.py.
"""

import os
import pytest

from core.config import settings
from core.ai import run_menu_content_agent


def _evals_enabled() -> bool:
    return bool(os.getenv("RUN_AI_EVALS")) and settings.USE_AI_RECOMMENDATIONS and bool(settings.DEEPSEEK_API_KEY)


pytestmark = [
    pytest.mark.eval,
    pytest.mark.skipif(
        not _evals_enabled(),
        reason="Real AI eval — set RUN_AI_EVALS=1 and configure DEEPSEEK_API_KEY to run (consumes tokens).",
    ),
]


class TestMenuContentReal:
    @pytest.mark.asyncio
    async def test_generates_valid_structure(self, mock_categories):
        """Real generation must satisfy the field contract used by the menu form."""
        result = await run_menu_content_agent(
            name="Pizza Diavola",
            ingredients="sos de roșii, mozzarella, salam picant, ardei iute",
            existing_categories=mock_categories,
        )
        assert result["agent"] != "fallback", "model did not answer (fallback) — check API/key"

        assert 0 < len(result["description"]) <= 500
        assert len(result["dietary_tags"]) <= 255

        band = result["price_band"]
        assert band["min"] >= 0 and band["max"] >= 0
        assert band["min"] <= band["max"], f"price band inverted: {band}"

        prep = result["prep_time_minutes"]
        assert prep is None or (isinstance(prep, int) and prep >= 0)

        cat = result["suggested_category"]
        assert cat["name"], "empty category name"
        print(f"\n[menu] desc[:80]={result['description'][:80]!r} band={band} cat={cat}")

    @pytest.mark.asyncio
    async def test_pizza_maps_to_existing_category(self, mock_categories):
        """A pizza should be slotted into the existing 'Pizza' category, not a new one."""
        result = await run_menu_content_agent(
            name="Pizza Quattro Formaggi",
            ingredients="mozzarella, gorgonzola, parmezan, provolone",
            existing_categories=mock_categories,
        )
        assert result["agent"] != "fallback"
        cat = result["suggested_category"]
        print(f"\n[menu] suggested category: {cat}")
        assert cat["name"].lower() == "pizza", f"expected existing 'Pizza', got {cat}"
        assert cat["is_new"] is False
