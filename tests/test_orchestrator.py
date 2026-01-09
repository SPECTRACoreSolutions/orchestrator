"""
Tests for Orchestrator
"""

import pytest
from orchestrator.orchestrator import Orchestrator
from orchestrator.activity import ActivityContext


@pytest.mark.asyncio
async def test_orchestrator_initialization():
    """Test Orchestrator initialization."""
    orchestrator = Orchestrator()
    assert "discover" in orchestrator.activities
    await orchestrator.llm_client.close()


@pytest.mark.asyncio
async def test_orchestrator_determine_activities():
    """Test activity determination."""
    orchestrator = Orchestrator()

    activities = await orchestrator.determine_activities("discover logging service")
    assert "discover" in activities

    await orchestrator.llm_client.close()


@pytest.mark.asyncio
async def test_orchestrator_run_discover_mock():
    """Test orchestrator run with discover activity (mocked)."""
    orchestrator = Orchestrator()

    # Mock discover activity to avoid LLM calls in tests
    async def mock_execute(context):
        from orchestrator.activity import ActivityResult
        return ActivityResult(
            activity_name="discover",
            success=True,
            outputs={"service_name": "test"},
            errors=[],
        )

    orchestrator.activities["discover"].execute = mock_execute

    try:
        result = await orchestrator.run(
            user_input="discover test service",
            activities=["discover"],
        )
        assert result.success
        assert "discover" in result.activities_executed
    except (ValueError, FileNotFoundError):
        # Expected if workspace root not found
        pytest.skip("Workspace root not found in test environment")
    finally:
        await orchestrator.llm_client.close()

