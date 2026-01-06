"""
Tests for LLM Client
"""

import pytest
from orchestrator.llm_client import LLMClient


@pytest.mark.asyncio
async def test_llm_client_initialization():
    """Test LLM client initialization."""
    client = LLMClient()
    assert client.api_url == "http://localhost:8001/v1/chat/completions"
    assert client.api_key == "token-irrelevant"
    assert client.model == "mistralai/Mistral-7B-Instruct-v0.3"
    await client.close()


@pytest.mark.asyncio
async def test_llm_client_custom_config():
    """Test LLM client with custom configuration."""
    client = LLMClient(
        api_url="http://example.com/v1/chat/completions",
        api_key="test-key",
        model="test-model",
    )
    assert client.api_url == "http://example.com/v1/chat/completions"
    assert client.api_key == "test-key"
    assert client.model == "test-model"
    await client.close()


@pytest.mark.asyncio
async def test_llm_client_health_check_no_service():
    """Test health check when service is not available."""
    client = LLMClient(api_url="http://localhost:9999/v1/chat/completions")
    # This should not raise, just return False
    result = await client.health_check()
    assert isinstance(result, bool)
    await client.close()

