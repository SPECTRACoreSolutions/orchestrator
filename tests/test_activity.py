"""
Tests for Activity Base Class
"""

import pytest
from orchestrator.activity import Activity, ActivityContext, ActivityResult
from orchestrator.llm_client import LLMClient


class TestActivity(Activity):
    """Test activity implementation."""
    
    async def execute(self, context: ActivityContext) -> ActivityResult:
        return ActivityResult(
            activity_name="test",
            success=True,
            outputs={"test": "value"},
            errors=[],
        )


@pytest.mark.asyncio
async def test_activity_initialization():
    """Test Activity initialization."""
    activity = TestActivity()
    assert activity.name == "test"
    await activity.llm_client.close()


@pytest.mark.asyncio
async def test_activity_format_prompt():
    """Test prompt formatting."""
    activity = TestActivity()
    context = {"test": "value"}
    prompt = activity.format_prompt(context)
    assert "test activity agent" in prompt.lower()
    assert "test" in prompt
    await activity.llm_client.close()


@pytest.mark.asyncio
async def test_activity_call_llm_mock(monkeypatch):
    """Test LLM calling with mocked response."""
    activity = TestActivity()
    
    async def mock_chat_completion(system_prompt, user_message):
        return '{"key": "value"}'
    
    activity.llm_client.chat_completion = mock_chat_completion
    
    result = await activity.call_llm("System prompt", "User message")
    assert result == {"key": "value"}
    
    await activity.llm_client.close()

