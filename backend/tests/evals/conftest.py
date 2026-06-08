"""
Shared fixtures for AI agent evaluation tests.
Provides mock DeepSeek responses, standardized menu data, and test queries.
"""

import json
import pytest
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import patch, MagicMock

# Load mock data from files
def load_json(filename: str) -> Any:
    data_dir = Path(__file__).parent / "data"
    with open(data_dir / filename, "r") as f:
        return json.load(f)


@pytest.fixture
def mock_menu() -> List[Dict]:
    """Standardized menu for reproducible evaluations."""
    return load_json("mock_menu.json")


@pytest.fixture
def test_queries() -> List[Dict]:
    """Golden dataset of test queries with expected outcomes."""
    return load_json("test_queries.json")


@pytest.fixture
def off_topic_inputs() -> List[str]:
    """Adversarial inputs for safety testing."""
    return load_json("off_topic_inputs.json")


@pytest.fixture
def mock_deepseek_vegan_response() -> Dict:
    """Simulated DeepSeek response for vegan query."""
    return {
        "response_text": "Here are some delicious vegan options from our menu!",
        "suggested_dishes": [
            {"item_id": 101, "name": "Vegan Pasta Primavera", "reasoning": "Fresh vegetables with marinara", "price": 28.0},
            {"item_id": 102, "name": "Quinoa Buddha Bowl", "reasoning": "Nutritious and filling", "price": 32.0},
            {"item_id": 103, "name": "Grilled Veggie Wrap", "reasoning": "Light and healthy", "price": 24.0}
        ],
        "follow_up_question": "Would you like to know more about any of these?"
    }


@pytest.fixture
def mock_deepseek_spicy_response() -> Dict:
    """Simulated DeepSeek response for spicy query."""
    return {
        "response_text": "Spicy lovers, you're in for a treat!",
        "suggested_dishes": [
            {"item_id": 201, "name": "Spicy Chicken Wings", "reasoning": "Hot buffalo sauce", "price": 35.0},
            {"item_id": 202, "name": "Thai Red Curry", "reasoning": "Authentic spicy flavors", "price": 38.0}
        ],
        "follow_up_question": "How spicy do you like it?"
    }


@pytest.fixture
def mock_deepseek_off_topic_violation() -> Dict:
    """Simulates an off-topic response that should trigger guardrail."""
    return {
        "response_text": "Here's how to write a Python function...",
        "suggested_dishes": [],
        "follow_up_question": None
    }


@pytest.fixture
def mock_deepseek_safe_fallback() -> Dict:
    """Expected safe fallback for off-topic queries."""
    return {
        "response_text": "I'm your food assistant and can only help with menu recommendations and dining advice. Is there something from our menu you'd like to know about?",
        "suggested_dishes": [],
        "follow_up_question": None
    }


@pytest.fixture
def mock_deepseek_client(mock_deepseek_vegan_response):
    """Mock AsyncOpenAI client for DeepSeek API."""
    mock_client = MagicMock()
    
    # Create async mock for chat.completions.create
    async def mock_create(*args, **kwargs):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(mock_deepseek_vegan_response)
        return mock_response
    
    mock_client.chat.completions.create = mock_create
    return mock_client


@pytest.fixture(autouse=True)
def reset_chat_sessions():
    """Clear chat sessions before each test (both customer and manager agents)."""
    from core.ai import _chat_sessions, _insights_sessions
    _chat_sessions.clear()
    _insights_sessions.clear()
    yield
    _chat_sessions.clear()
    _insights_sessions.clear()


# ---------------------------------------------------------------------------
# Manager-side agents (insights + menu content) — fixtures & helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_report() -> Dict:
    """Standardized sales report for reproducible insights evaluations."""
    return load_json("mock_report.json")


@pytest.fixture
def mock_menu_prices(mock_menu) -> List[Dict]:
    """Menu price list in the shape the insights endpoint passes to the agent."""
    return [
        {
            "name": item["name"],
            "price": item["price"],
            "is_available": item.get("is_available", True),
            "category": item.get("category"),
        }
        for item in mock_menu
    ]


@pytest.fixture
def mock_categories() -> List[str]:
    """Existing categories used by the menu content agent."""
    return ["Pizza", "Burgers", "Salads", "Desserts"]
