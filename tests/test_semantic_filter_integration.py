"""
Integration tests for SemanticFilter with Orchestrator activities

Tests end-to-end filtering in the context of actual activity execution.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from orchestrator.activities.provision import Provision
from orchestrator.activity import ActivityContext
from orchestrator.playbooks import Playbook


@pytest.fixture
def mock_components():
    """Create mocked components for integration tests."""
    # Mock context builder
    context_builder = MagicMock()
    context_builder.workspace_root = "/fake/workspace"
    context_builder.build_activity_context.return_value = {
        "activity": "provision",
        "specification_summary": "Test service",
        "tools": [],
    }

    # Mock LLM client
    llm_client = MagicMock()
    llm_client.chat_completion = AsyncMock()

    # Mock playbook registry
    playbook_registry = MagicMock()
    playbook_registry.filter_relevant_playbooks = AsyncMock()
    playbook_registry.get_playbook_context_for_llm.return_value = {
        "available_playbooks": [],
        "instructions": "Use semantic filtering",
    }

    return {
        "context_builder": context_builder,
        "llm_client": llm_client,
        "playbook_registry": playbook_registry,
    }


@pytest.fixture
def activity_context():
    """Create sample activity context."""
    return ActivityContext(
        user_input="Deploy service-catalog to Railway production",
        service_name="service-catalog",
        specification=None,
        manifest=None,
    )


@pytest.mark.asyncio
async def test_provision_activity_uses_semantic_filtering(mock_components, activity_context):
    """Test that Provision activity uses semantic filtering."""
    # Setup mocks
    mock_components["llm_client"].chat_completion.return_value = """
    {
        "infrastructure_requirements": {"railway_services": ["service-catalog"]},
        "selected_playbooks": ["railway.001"],
        "execution_plan": {"steps": ["create_service"]}
    }
    """

    mock_components["playbook_registry"].filter_relevant_playbooks.return_value = [
        Playbook(
            name="railway.001",
            description="Deploy to Railway",
            path="railway/railway.001.md",
            activity="provision",
            metadata={"domain": "railway", "mcp_native": True},
        )
    ]

    # Create activity with mocks
    activity = Provision()
    activity.context_builder = mock_components["context_builder"]
    activity.llm_client = mock_components["llm_client"]
    activity.playbook_registry = mock_components["playbook_registry"]

    # Execute (will fail due to missing MCP, but we're testing filtering call)
    try:
        await activity.execute(activity_context)
    except Exception:
        pass  # Expected to fail on actual execution

    # Verify semantic filtering was called
    mock_components["playbook_registry"].filter_relevant_playbooks.assert_called_once()
    call_args = mock_components["playbook_registry"].filter_relevant_playbooks.call_args

    # Verify correct parameters
    assert call_args.kwargs["activity_name"] == "provision"
    assert "service-catalog" in call_args.kwargs["task"]
    assert call_args.kwargs["llm_client"] == mock_components["llm_client"]
    assert call_args.kwargs["max_playbooks"] == 5


@pytest.mark.asyncio
async def test_multiple_activities_consistent_filtering(mock_components):
    """Test that multiple activities use consistent filtering."""
    from orchestrator.activities.build import Build
    from orchestrator.activities.deploy import Deploy

    # Setup common mocks
    for activity_class in [Build, Deploy]:
        activity = activity_class()
        activity.context_builder = mock_components["context_builder"]
        activity.llm_client = mock_components["llm_client"]
        activity.playbook_registry = mock_components["playbook_registry"]

        mock_components["llm_client"].chat_completion.return_value = "{}"
        mock_components["playbook_registry"].filter_relevant_playbooks.return_value = []

        ctx = ActivityContext(
            user_input=f"Test {activity_class.__name__}",
            service_name="test-service",
            specification=None,
            manifest=None,
        )

        try:
            await activity.execute(ctx)
        except Exception:
            pass

    # Verify both activities called filtering
    assert mock_components["playbook_registry"].filter_relevant_playbooks.call_count >= 2


@pytest.mark.asyncio
async def test_token_usage_reduction(mock_components, activity_context):
    """Test that semantic filtering reduces token usage."""
    # Create many playbooks (simulate large registry)
    many_playbooks = [
        Playbook(
            name=f"playbook.{i:03d}",
            description=f"Playbook {i} description" * 10,  # Long description
            path=f"playbooks/playbook.{i:03d}.md",
            activity="provision",
            metadata={"domain": f"domain{i}"},
        )
        for i in range(50)  # 50 playbooks
    ]

    # Mock filtering to return only 5
    filtered_playbooks = many_playbooks[:5]
    mock_components["playbook_registry"].filter_relevant_playbooks.return_value = filtered_playbooks
    mock_components["playbook_registry"].get_playbook_context_for_llm.return_value = {
        "available_playbooks": [
            {"name": pb.name, "description": pb.description}
            for pb in filtered_playbooks
        ],
        "instructions": "Use semantic filtering",
    }

    mock_components["llm_client"].chat_completion.return_value = "{}"

    # Create activity
    activity = Provision()
    activity.context_builder = mock_components["context_builder"]
    activity.llm_client = mock_components["llm_client"]
    activity.playbook_registry = mock_components["playbook_registry"]

    try:
        await activity.execute(activity_context)
    except Exception:
        pass

    # Verify filtering was called
    mock_components["playbook_registry"].filter_relevant_playbooks.assert_called_once()

    # Verify get_playbook_context was called with filtered list
    mock_components["playbook_registry"].get_playbook_context_for_llm.assert_called()
    call_args = mock_components["playbook_registry"].get_playbook_context_for_llm.call_args

    # Should receive filtered playbooks (5 instead of 50)
    assert call_args.kwargs.get("playbooks") is not None
    assert len(call_args.kwargs["playbooks"]) <= 5


@pytest.mark.asyncio
async def test_filtering_fallback_on_llm_failure(mock_components, activity_context):
    """Test graceful degradation when LLM filtering fails."""
    # Mock filter_relevant_playbooks to raise exception
    mock_components["playbook_registry"].filter_relevant_playbooks.side_effect = Exception("LLM unavailable")

    # Fallback: get_playbook_context should still work
    mock_components["playbook_registry"].get_playbook_context_for_llm.return_value = {
        "available_playbooks": [],
        "instructions": "Fallback mode",
    }

    mock_components["llm_client"].chat_completion.return_value = "{}"

    activity = Provision()
    activity.context_builder = mock_components["context_builder"]
    activity.llm_client = mock_components["llm_client"]
    activity.playbook_registry = mock_components["playbook_registry"]

    # Should not crash, should use fallback
    try:
        await activity.execute(activity_context)
    except Exception as e:
        # Activity may fail for other reasons, but not due to filtering
        assert "LLM unavailable" not in str(e)

