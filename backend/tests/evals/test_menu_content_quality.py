"""
Menu Content Generator Agent Evaluation Tests

Evaluates run_menu_content_agent (single-shot generation of description, dietary
tags, suggested category, price band, prep time for a new menu item).

Focus is the server-side validation in _finalize, which is the trust boundary:
- is_new is recomputed against the REAL category list (model's flag is ignored)
- fields are length-clamped and type-coerced
- malformed model output is tolerated, not crashed on
- fallback template when AI is disabled

All deterministic, NO real API calls.
"""

import json
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from core.ai import run_menu_content_agent
from tests.evals.conftest import make_mock_deepseek


@contextmanager
def mocked_ai(content: str, capture=None):
    with patch("core.ai.settings.USE_AI_RECOMMENDATIONS", True), \
         patch("core.ai.settings.DEEPSEEK_API_KEY", "test-key"), \
         patch("core.ai.settings.DEEPSEEK_MODEL", "deepseek-test"), \
         patch("core.ai.get_deepseek_client", return_value=make_mock_deepseek(content, capture)):
        yield


class TestCategoryValidation:
    """is_new is the server's call, not the model's."""

    @pytest.mark.asyncio
    async def test_existing_category_forces_is_new_false(self, mock_categories):
        """Model claims a brand-new category that already exists → corrected to is_new=False."""
        content = json.dumps({
            "description": "Pizza picantă cu salam.",
            "dietary_tags": "",
            "suggested_category": {"name": "pizza", "is_new": True},  # wrong + wrong case
            "price_band": {"min": 30.0, "max": 40.0},
            "prep_time_minutes": 15,
        })
        with mocked_ai(content):
            result = await run_menu_content_agent(
                name="Pizza Diavola", ingredients="salam, ardei iute",
                existing_categories=mock_categories,
            )

        assert result["suggested_category"]["is_new"] is False
        assert result["suggested_category"]["name"] == "Pizza"  # normalized to existing casing

    @pytest.mark.asyncio
    async def test_new_category_forces_is_new_true(self, mock_categories):
        """Model claims existing for a category that's actually new → corrected to is_new=True."""
        content = json.dumps({
            "description": "Tapas spaniole de partajat.",
            "dietary_tags": "vegetarian",
            "suggested_category": {"name": "Tapas", "is_new": False},
            "price_band": {"min": 20.0, "max": 28.0},
            "prep_time_minutes": 12,
        })
        with mocked_ai(content):
            result = await run_menu_content_agent(
                name="Patatas Bravas", ingredients="cartofi, sos picant",
                existing_categories=mock_categories,
            )

        assert result["suggested_category"]["is_new"] is True
        assert result["suggested_category"]["name"] == "Tapas"

    @pytest.mark.asyncio
    async def test_category_as_plain_string_tolerated(self, mock_categories):
        """Model returns suggested_category as a string instead of an object."""
        content = json.dumps({
            "description": "Desert cu ciocolată.",
            "dietary_tags": "vegetarian",
            "suggested_category": "Desserts",
            "price_band": {"min": 18.0, "max": 24.0},
            "prep_time_minutes": 10,
        })
        with mocked_ai(content):
            result = await run_menu_content_agent(
                name="Lava Cake", existing_categories=mock_categories,
            )

        assert result["suggested_category"]["name"] == "Desserts"
        assert result["suggested_category"]["is_new"] is False


class TestFieldSanitization:
    """Output fields are clamped/coerced regardless of what the model returns."""

    @pytest.mark.asyncio
    async def test_long_fields_are_truncated(self, mock_categories):
        content = json.dumps({
            "description": "x" * 900,
            "dietary_tags": "y" * 400,
            "suggested_category": {"name": "Pizza", "is_new": False},
            "price_band": {"min": 30.0, "max": 40.0},
            "prep_time_minutes": 15,
        })
        with mocked_ai(content):
            result = await run_menu_content_agent(name="Test", existing_categories=mock_categories)

        assert len(result["description"]) <= 500
        assert len(result["dietary_tags"]) <= 255

    @pytest.mark.asyncio
    async def test_price_band_coerced_and_rounded(self, mock_categories):
        content = json.dumps({
            "description": "ok",
            "dietary_tags": "",
            "suggested_category": {"name": "Pizza", "is_new": False},
            "price_band": {"min": "29.999", "max": "41.234"},  # strings
            "prep_time_minutes": 15,
        })
        with mocked_ai(content):
            result = await run_menu_content_agent(name="Test", existing_categories=mock_categories)

        assert result["price_band"]["min"] == 30.0
        assert result["price_band"]["max"] == 41.23

    @pytest.mark.asyncio
    async def test_missing_or_invalid_price_band_defaults(self, mock_categories):
        content = json.dumps({
            "description": "ok",
            "dietary_tags": "",
            "suggested_category": {"name": "Pizza", "is_new": False},
            "price_band": "necunoscut",  # invalid type
            "prep_time_minutes": "nu știu",  # invalid → None
        })
        with mocked_ai(content):
            result = await run_menu_content_agent(name="Test", existing_categories=mock_categories)

        assert result["price_band"] == {"min": 0.0, "max": 0.0}
        assert result["prep_time_minutes"] is None


class TestFallback:
    """Deterministic template when AI is unavailable."""

    @pytest.mark.asyncio
    async def test_fallback_when_ai_disabled(self, mock_categories):
        with patch("core.ai.settings.USE_AI_RECOMMENDATIONS", False):
            result = await run_menu_content_agent(
                name="Bruschette", ingredients="roșii, busuioc",
                existing_categories=mock_categories,
            )

        assert result["agent"] == "fallback"
        assert result["description"]  # non-empty
        assert "Bruschette" in result["description"]

    @pytest.mark.asyncio
    async def test_empty_description_falls_back(self, mock_categories):
        """Model returns no usable description → fallback template."""
        content = json.dumps({"description": "", "suggested_category": {"name": "Pizza"}})
        with mocked_ai(content):
            result = await run_menu_content_agent(
                name="Mystery", ingredients="x", existing_categories=mock_categories,
            )

        assert result["agent"] == "fallback"


class TestStructure:
    """Response shape contract."""

    @pytest.mark.asyncio
    async def test_response_fields_present(self, mock_categories):
        content = json.dumps({
            "description": "ok",
            "dietary_tags": "vegetarian",
            "suggested_category": {"name": "Pizza", "is_new": False},
            "price_band": {"min": 30.0, "max": 40.0},
            "prep_time_minutes": 15,
        })
        with mocked_ai(content):
            result = await run_menu_content_agent(name="Test", existing_categories=mock_categories)

        for field in ("description", "dietary_tags", "suggested_category", "price_band", "prep_time_minutes", "agent"):
            assert field in result
        assert set(result["suggested_category"].keys()) == {"name", "is_new"}
        assert set(result["price_band"].keys()) == {"min", "max"}
