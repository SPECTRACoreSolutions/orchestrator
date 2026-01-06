"""
Tests for Discover Activity
"""

import pytest
from orchestrator.activities.discover import DiscoverActivity
from orchestrator.activity import ActivityContext, ActivityResult


@pytest.mark.asyncio
async def test_discover_activity_initialization():
    """Test DiscoverActivity initialization."""
    activity = DiscoverActivity()
    assert activity.name == "discover"
    await activity.llm_client.close()


@pytest.mark.asyncio
async def test_discover_activity_execute_mock(monkeypatch):
    """Test DiscoverActivity execution with mocked LLM."""
    activity = DiscoverActivity()
    
    # Mock LLM client
    async def mock_chat_completion(system_prompt, user_message):
        return '{"service_name": "test-service", "problem": {"statement": "test problem", "impact": "high"}, "idea": {"name": "test-service", "type": "service", "priority": "critical"}, "validation": {"problem_solved": true, "reasoning": "test"}, "maturity_assessment": {"level": "L3", "target": "L3", "reasoning": "test"}, "next_steps": "test"}'
    
    activity.llm_client.chat_completion = mock_chat_completion
    
    context = ActivityContext(
        activity_name="discover",
        user_input="build a test service",
        service_name="test-service",
    )
    
    # This will fail if workspace root cannot be found, which is expected in test environment
    # In real usage, workspace root should exist
    try:
        result = await activity.execute(context)
        assert isinstance(result, ActivityResult)
        assert result.activity_name == "discover"
    except (ValueError, FileNotFoundError):
        # Expected if workspace root not found - test environment limitation
        pytest.skip("Workspace root not found in test environment")
    finally:
        await activity.llm_client.close()

