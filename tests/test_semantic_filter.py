"""
Tests for SemanticFilter - LLM-based semantic filtering

Verifies:
- LLM filtering selects relevant playbooks
- Fallback behavior when filtering fails
- Edge cases (empty playbooks, invalid tasks)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from orchestrator.semantic_filter import SemanticFilter
from orchestrator.playbooks import Playbook


@pytest.fixture
def sample_playbooks():
    """Create sample playbooks for testing."""
    return [
        Playbook(
            name="railway.001",
            description="Deploy service to Railway platform using RailwayMCP",
            path="railway/railway.001-deploy.md",
            activity="deploy",
            metadata={"domain": "railway", "mcp_native": True},
        ),
        Playbook(
            name="github.001",
            description="Create GitHub repository using GitHubMCP",
            path="github/github.001-create-repo.md",
            activity="provision",
            metadata={"domain": "github", "mcp_native": True},
        ),
        Playbook(
            name="docker.001",
            description="Build and package Docker container",
            path="docker/docker.001-build.md",
            activity="build",
            metadata={"domain": "docker", "mcp_native": False},
        ),
        Playbook(
            name="pytest.001",
            description="Run pytest tests with coverage reporting",
            path="testing/pytest.001-run-tests.md",
            activity="test",
            metadata={"domain": "testing", "mcp_native": False},
        ),
        Playbook(
            name="manual.001",
            description="Manual checklist for deployment verification",
            path="manual/manual.001-checklist.md",
            activity="deploy",
            metadata={"domain": "manual", "mcp_native": False, "manual_steps": True},
        ),
    ]


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client."""
    client = MagicMock()
    client.chat_completion = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_filter_playbooks_basic(mock_llm_client, sample_playbooks):
    """Test basic playbook filtering with LLM."""
    # Mock LLM response selecting railway and github playbooks
    mock_llm_client.chat_completion.return_value = """
    {
        "selected_playbooks": ["railway.001", "github.001"],
        "reasoning": "Railway for deployment, GitHub for repo creation"
    }
    """

    filter = SemanticFilter(llm_client=mock_llm_client, max_items=3)

    result = await filter.filter_playbooks(
        activity_name="deploy",
        task="Deploy my application to Railway",
        all_playbooks=sample_playbooks,
        max_playbooks=3,
    )

    # Should return filtered playbooks
    assert len(result) <= 3
    assert any(pb.name == "railway.001" for pb in result)

    # LLM should have been called
    mock_llm_client.chat_completion.assert_called_once()


@pytest.mark.asyncio
async def test_filter_playbooks_fewer_than_max(mock_llm_client, sample_playbooks):
    """Test filtering when playbooks <= max_playbooks."""
    filter = SemanticFilter(llm_client=mock_llm_client, max_items=5)

    # Only 3 playbooks, max is 5
    limited_playbooks = sample_playbooks[:3]

    result = await filter.filter_playbooks(
        activity_name="deploy",
        task="Deploy application",
        all_playbooks=limited_playbooks,
        max_playbooks=10,
    )

    # Should return all playbooks without LLM call
    assert len(result) == 3
    mock_llm_client.chat_completion.assert_not_called()


@pytest.mark.asyncio
async def test_filter_playbooks_empty_list(mock_llm_client):
    """Test filtering with empty playbook list."""
    filter = SemanticFilter(llm_client=mock_llm_client, max_items=5)

    result = await filter.filter_playbooks(
        activity_name="deploy",
        task="Deploy application",
        all_playbooks=[],
        max_playbooks=5,
    )

    # Should return empty list
    assert len(result) == 0
    mock_llm_client.chat_completion.assert_not_called()


@pytest.mark.asyncio
async def test_filter_playbooks_llm_failure(mock_llm_client, sample_playbooks):
    """Test fallback when LLM call fails."""
    # Mock LLM failure
    mock_llm_client.chat_completion.side_effect = Exception("LLM connection failed")

    filter = SemanticFilter(llm_client=mock_llm_client, max_items=5)

    result = await filter.filter_playbooks(
        activity_name="deploy",
        task="Deploy application",
        all_playbooks=sample_playbooks,
        max_playbooks=3,
    )

    # Should return first N playbooks as fallback
    assert len(result) == 3
    assert result[0].name == sample_playbooks[0].name


@pytest.mark.asyncio
async def test_filter_playbooks_invalid_json(mock_llm_client, sample_playbooks):
    """Test handling of invalid JSON response."""
    # Mock LLM returning invalid JSON
    mock_llm_client.chat_completion.return_value = "This is not JSON"

    filter = SemanticFilter(llm_client=mock_llm_client, max_items=5)

    result = await filter.filter_playbooks(
        activity_name="deploy",
        task="Deploy application",
        all_playbooks=sample_playbooks,
        max_playbooks=3,
    )

    # Should fallback to first N playbooks
    assert len(result) == 3


@pytest.mark.asyncio
async def test_filter_playbooks_partial_match(mock_llm_client, sample_playbooks):
    """Test filtering when LLM returns some invalid playbook names."""
    # Mock LLM response with mix of valid and invalid names
    mock_llm_client.chat_completion.return_value = """
    {
        "selected_playbooks": ["railway.001", "nonexistent.999", "github.001"],
        "reasoning": "Selected deployment playbooks"
    }
    """

    filter = SemanticFilter(llm_client=mock_llm_client, max_items=5)

    result = await filter.filter_playbooks(
        activity_name="deploy",
        task="Deploy application",
        all_playbooks=sample_playbooks,
        max_playbooks=5,
    )

    # Should only return valid playbooks
    assert all(pb.name in ["railway.001", "github.001"] for pb in result)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_filter_playbooks_adds_fallbacks(mock_llm_client, sample_playbooks):
    """Test that fallback playbooks are added when LLM returns too few."""
    # Mock LLM returning only 1 playbook (less than minimum 3)
    mock_llm_client.chat_completion.return_value = """
    {
        "selected_playbooks": ["railway.001"],
        "reasoning": "Only one matches perfectly"
    }
    """

    filter = SemanticFilter(llm_client=mock_llm_client, max_items=5)

    result = await filter.filter_playbooks(
        activity_name="deploy",
        task="Deploy application",
        all_playbooks=sample_playbooks,
        max_playbooks=5,
    )

    # Should add fallback playbooks to meet minimum
    assert len(result) >= min(3, len(sample_playbooks))


@pytest.mark.asyncio
async def test_filter_context_generic(mock_llm_client):
    """Test generic context filtering for non-playbook items."""
    # Mock LLM response with item indices
    mock_llm_client.chat_completion.return_value = """
    {
        "selected_items": [0, 2, 4]
    }
    """

    filter = SemanticFilter(llm_client=mock_llm_client, max_items=3)

    items = [
        {"name": "item1", "description": "First item"},
        {"name": "item2", "description": "Second item"},
        {"name": "item3", "description": "Third item"},
        {"name": "item4", "description": "Fourth item"},
        {"name": "item5", "description": "Fifth item"},
    ]

    result = await filter.filter_context(
        task="Find relevant items",
        items=items,
        max_items=3,
    )

    # Should return items at indices 0, 2, 4
    assert len(result) <= 3
    mock_llm_client.chat_completion.assert_called_once()


@pytest.mark.asyncio
async def test_filter_context_invalid_indices(mock_llm_client):
    """Test context filtering with invalid indices."""
    # Mock LLM response with out-of-bounds indices
    mock_llm_client.chat_completion.return_value = """
    {
        "selected_items": [0, 99, -1, 2]
    }
    """

    filter = SemanticFilter(llm_client=mock_llm_client, max_items=3)

    items = [
        {"name": "item1", "description": "First item"},
        {"name": "item2", "description": "Second item"},
        {"name": "item3", "description": "Third item"},
    ]

    result = await filter.filter_context(
        task="Find relevant items",
        items=items,
        max_items=3,
    )

    # Should only return valid indices (0, 2)
    assert len(result) == 2
    assert result[0]["name"] == "item1"
    assert result[1]["name"] == "item3"

