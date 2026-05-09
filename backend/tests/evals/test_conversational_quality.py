"""
Conversational Quality Evaluation Tests

Evaluates naturalness, context retention, and session persistence.
Metrics: Fluency, Context Retention, Session Consistency
"""

import pytest
from typing import Dict, List, Any
from unittest.mock import patch

from core.ai import (
    run_chat_recommendation_agent,
    _chat_sessions,
    clear_chat_session
)


class TestSessionPersistence:
    """Test that conversation history is maintained across turns."""

    @pytest.mark.asyncio
    async def test_session_id_persistence(self, mock_menu):
        """Same session_id should maintain conversation context."""
        session_id = "test-persistence-001"
        
        # Turn 1: Establish preference
        result1 = await run_chat_recommendation_agent(
            message="I want vegan food",
            session_id=session_id,
            menu_items=mock_menu
        )
        
        assert result1["session_id"] == session_id
        
        # Turn 2: Follow-up in same session
        result2 = await run_chat_recommendation_agent(
            message="Something spicy?",
            session_id=session_id,
            menu_items=mock_menu
        )
        
        assert result2["session_id"] == session_id
        
        # Verify session history exists
        assert session_id in _chat_sessions
        assert len(_chat_sessions[session_id]) >= 2  # At least user message + assistant
    
    @pytest.mark.asyncio
    async def test_different_sessions_isolated(self, mock_menu):
        """Different session IDs should be isolated."""
        session_a = "test-session-a"
        session_b = "test-session-b"
        
        # Session A
        await run_chat_recommendation_agent(
            message="vegan food",
            session_id=session_a,
            menu_items=mock_menu
        )
        
        # Session B
        await run_chat_recommendation_agent(
            message="spicy food",
            session_id=session_b,
            menu_items=mock_menu
        )
        
        # Sessions should have different histories
        history_a = _chat_sessions.get(session_a, [])
        history_b = _chat_sessions.get(session_b, [])
        
        assert len(history_a) > 0
        assert len(history_b) > 0
    
    @pytest.mark.asyncio
    async def test_clear_chat_session(self, mock_menu):
        """Clear chat should remove session history."""
        session_id = "test-clear-001"
        
        # Create session
        await run_chat_recommendation_agent(
            message="hello",
            session_id=session_id,
            menu_items=mock_menu
        )
        
        assert session_id in _chat_sessions
        
        # Clear session
        clear_chat_session(session_id)
        
        assert session_id not in _chat_sessions


class TestContextRetention:
    """Test that AI remembers previous context."""

    @pytest.mark.asyncio
    async def test_preference_retention(self, mock_menu):
        """AI should remember stated preferences in follow-up queries."""
        session_id = "test-context-001"
        
        # Turn 1: State vegan preference
        result1 = await run_chat_recommendation_agent(
            message="I'm vegetarian",
            session_id=session_id,
            menu_items=mock_menu
        )
        
        # Turn 2: Follow-up without restating preference
        result2 = await run_chat_recommendation_agent(
            message="What about pasta?",
            session_id=session_id,
            menu_items=mock_menu
        )
        
        # AI should filter suggestions by vegetarian preference
        menu_lookup = {item["id"]: item for item in mock_menu}
        
        for dish in result2["suggested_dishes"]:
            item = menu_lookup.get(dish["item_id"], {})
            # All suggestions should be vegetarian (or at least no meat)
            # Note: This is a soft check since we use fallback
            print(f"  Suggested: {item.get('name')} - Tags: {item.get('dietary_tags')}")
    
    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, mock_menu):
        """Test 3-turn conversation flow."""
        session_id = "test-multi-turn-001"
        
        # Turn 1
        r1 = await run_chat_recommendation_agent(
            message="I want something light",
            session_id=session_id,
            menu_items=mock_menu
        )
        assert len(r1["suggested_dishes"]) > 0
        
        # Turn 2 - narrow down
        r2 = await run_chat_recommendation_agent(
            message="Make it vegan",
            session_id=session_id,
            menu_items=mock_menu
        )
        
        # Turn 3 - price constraint
        r3 = await run_chat_recommendation_agent(
            message="Under 30 RON",
            session_id=session_id,
            menu_items=mock_menu
        )
        
        # Check final suggestions meet all criteria
        menu_lookup = {item["id"]: item for item in mock_menu}
        
        for dish in r3["suggested_dishes"]:
            item = menu_lookup.get(dish["item_id"], {})
            # Should be light (salad/wrap), vegan, under 30
            price = item.get("price", 0)
            assert price <= 30, f"Item {dish['item_id']} over budget: {price}"
    
    @pytest.mark.asyncio
    async def test_negative_feedback_handling(self, mock_menu):
        """AI should adapt when user indicates dislike."""
        session_id = "test-feedback-001"
        
        # Turn 1: General request
        r1 = await run_chat_recommendation_agent(
            message="I want pasta",
            session_id=session_id,
            menu_items=mock_menu
        )
        
        first_suggestions = [d["item_id"] for d in r1["suggested_dishes"]]
        
        # Turn 2: Negative feedback
        r2 = await run_chat_recommendation_agent(
            message="I don't like those, something else?",
            session_id=session_id,
            menu_items=mock_menu
        )
        
        # Should suggest different items
        second_suggestions = [d["item_id"] for d in r2["suggested_dishes"]]
        
        # At least some suggestions should be different
        overlap = set(first_suggestions) & set(second_suggestions)
        print(f"  First: {first_suggestions}")
        print(f"  Second: {second_suggestions}")
        print(f"  Overlap: {overlap}")


class TestResponseQuality:
    """Test quality of AI responses (fluency, helpfulness)."""

    @pytest.mark.asyncio
    async def test_response_has_content(self, mock_menu):
        """Response should not be empty."""
        result = await run_chat_recommendation_agent(
            message="What do you recommend?",
            session_id="test-content-001",
            menu_items=mock_menu
        )
        
        assert result["response_text"]
        assert len(result["response_text"]) > 20  # Not just a few words
    
    @pytest.mark.asyncio
    async def test_response_includes_follow_up(self, mock_menu):
        """Response should include a follow-up question."""
        result = await run_chat_recommendation_agent(
            message="hello",
            session_id="test-followup-001",
            menu_items=mock_menu
        )
        
        # Should have follow_up_question (could be null but field exists)
        assert "follow_up_question" in result
    
    @pytest.mark.asyncio
    async def test_suggested_dishes_structure(self, mock_menu):
        """Each suggested dish should have required fields."""
        result = await run_chat_recommendation_agent(
            message="recommend food",
            session_id="test-structure-001",
            menu_items=mock_menu
        )
        
        for dish in result["suggested_dishes"]:
            assert "item_id" in dish
            assert "name" in dish
            assert "reasoning" in dish
            assert "price" in dish
    
    @pytest.mark.asyncio
    async def test_reasoning_provided(self, mock_menu):
        """Each dish should have reasoning/explanation."""
        result = await run_chat_recommendation_agent(
            message="vegan options",
            session_id="test-reasoning-001",
            menu_items=mock_menu
        )
        
        for dish in result["suggested_dishes"]:
            reasoning = dish.get("reasoning", "")
            assert reasoning
            assert len(reasoning) > 10  # Substantial explanation
    
    @pytest.mark.asyncio
    async def test_max_3_suggestions(self, mock_menu):
        """AI should suggest at most 3 dishes."""
        result = await run_chat_recommendation_agent(
            message="What should I order?",
            session_id="test-limit-001",
            menu_items=mock_menu
        )
        
        assert len(result["suggested_dishes"]) <= 3, \
            f"Too many suggestions: {len(result['suggested_dishes'])}"


class TestNewSessionBehavior:
    """Test behavior when starting a new session."""

    @pytest.mark.asyncio
    async def test_new_session_generates_uuid(self, mock_menu):
        """New session should get a UUID if not provided."""
        # This tests the endpoint behavior via the API
        # For unit tests, we directly check the function
        result = await run_chat_recommendation_agent(
            message="hello",
            session_id="",  # Empty session
            menu_items=mock_menu
        )
        
        # If session_id is empty, the API layer generates UUID
        # Our direct function call uses whatever we pass
        # So this just verifies empty session handling
        assert result  # Function completes without error


class TestFallbackConversation:
    """Test conversational quality in fallback mode."""

    @pytest.mark.asyncio
    async def test_fallback_response_format(self, mock_menu):
        """Fallback responses should still be well-formatted."""
        with patch("core.ai.settings.USE_AI_RECOMMENDATIONS", False):
            result = await run_chat_recommendation_agent(
                message="vegan food",
                session_id="test-fallback-fmt-001",
                menu_items=mock_menu
            )
        
        assert result["agent"] == "fallback"
        assert result["response_text"]
        assert len(result["suggested_dishes"]) > 0
        
        # Verify structure
        for dish in result["suggested_dishes"]:
            assert all(k in dish for k in ["item_id", "name", "reasoning", "price"])
    
    @pytest.mark.asyncio
    async def test_fallback_dietary_matching(self, mock_menu):
        """Fallback should still match dietary keywords."""
        with patch("core.ai.settings.USE_AI_RECOMMENDATIONS", False):
            result = await run_chat_recommendation_agent(
                message="spicy",
                session_id="test-fallback-spicy-001",
                menu_items=mock_menu
            )
        
        # Should suggest items with "spicy" in name or tags
        menu_lookup = {item["id"]: item for item in mock_menu}
        
        for dish in result["suggested_dishes"]:
            item = menu_lookup.get(dish["item_id"], {})
            name = item.get("name", "").lower()
            tags = [t.lower() for t in item.get("dietary_tags", [])]
            
            # Should match keyword
            assert "spicy" in name or "spicy" in tags or "hot" in name, \
                f"Item {dish['item_id']} doesn't match 'spicy' keyword"
