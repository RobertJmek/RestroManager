"""
Shared fixtures/helpers for the manager-side AI agent unit tests
(deterministic, mocked — no real API calls).
"""

from typing import Dict, List
from unittest.mock import MagicMock

import pytest


MOCK_REPORT: Dict = {
    "start_date": "2026-06-01",
    "end_date": "2026-06-07",
    "total_revenue": 4520.0,
    "total_orders": 128,
    "average_order_value": 35.31,
    "top_items": [
        {"name": "Margherita Pizza", "quantity_sold": 64},
        {"name": "Classic Cheeseburger", "quantity_sold": 41},
        {"name": "Caesar Salad", "quantity_sold": 33},
    ],
    "revenue_by_day": [
        {"date": "2026-06-06", "revenue": 2100.0},
        {"date": "2026-06-07", "revenue": 2420.0},
    ],
}

MOCK_MENU_PRICES: List[Dict] = [
    {"name": "Margherita Pizza", "price": 35.0, "is_available": True, "category": "Pizza"},
    {"name": "Classic Cheeseburger", "price": 40.0, "is_available": True, "category": "Burgers"},
    {"name": "Caesar Salad", "price": 26.0, "is_available": True, "category": "Salads"},
    {"name": "Fresh Fruit Salad", "price": 18.0, "is_available": True, "category": "Desserts"},
]


@pytest.fixture
def mock_report() -> Dict:
    return {**MOCK_REPORT}


@pytest.fixture
def mock_menu_prices() -> List[Dict]:
    return [dict(i) for i in MOCK_MENU_PRICES]


@pytest.fixture
def mock_categories() -> List[str]:
    return ["Pizza", "Burgers", "Salads", "Desserts"]


def make_mock_deepseek(content: str, capture: List[Dict] = None) -> MagicMock:
    """
    Mock DeepSeek client whose chat.completions.create returns `content`.
    If `capture` is given, each call's kwargs (incl. messages) are recorded so
    tests can assert what was actually sent in the prompt.
    """
    client = MagicMock()

    async def _create(*args, **kwargs):
        if capture is not None:
            capture.append(kwargs)
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.content = content
        resp.choices[0].finish_reason = "stop"
        return resp

    client.chat.completions.create = _create
    return client


@pytest.fixture(autouse=True)
def reset_agent_sessions():
    """Clear in-memory conversation history between tests."""
    from core.ai import _chat_sessions, _insights_sessions
    _chat_sessions.clear()
    _insights_sessions.clear()
    yield
    _chat_sessions.clear()
    _insights_sessions.clear()
