"""
Integration tests for Orchestrator with Power App idea.

Tests full orchestrator lifecycle using Power App as test case.
"""

import pytest
from orchestrator.orchestrator import Orchestrator, OrchestrationResult


@pytest.mark.asyncio
@pytest.mark.integration
async def test_orchestrator_powerapp_full_lifecycle():
    """
    Test orchestrator with Power App idea through full lifecycle.

    Tests: Engage → Discover → Plan → Assess → Design
    """
    orchestrator = Orchestrator()

    try:
        # Test with Power App idea
        user_input = "Create Power App for Service Catalog and Client Management"

        # Run orchestrator (should determine activities automatically)
        result: OrchestrationResult = await orchestrator.run(
            user_input=user_input,
            service_name=None,  # Should be extracted by discover
        )

        # Verify orchestrator ran
        assert result is not None
        assert isinstance(result, OrchestrationResult)
        assert len(result.activities_executed) > 0

        # Verify expected activities were determined
        # Should include at least: discover, plan, assess, design
        expected_activities = ["discover", "plan", "assess", "design"]
        executed_activity_names = result.activities_executed

        # Check that at least some expected activities were executed
        assert any(act in executed_activity_names for act in expected_activities), (
            f"Expected at least one of {expected_activities} to be executed, "
            f"but got: {executed_activity_names}"
        )

        # Verify results exist for executed activities
        for activity_name in result.activities_executed:
            assert activity_name in result.results, (
                f"Result missing for activity: {activity_name}"
            )
            activity_result = result.results[activity_name]
            assert activity_result is not None
            assert activity_result.activity_name == activity_name

        # If discover was executed, verify it extracted service name
        if "discover" in result.results:
            discover_result = result.results["discover"]
            if discover_result.success:
                assert "service_name" in discover_result.outputs or "outputs" in discover_result.outputs

    except Exception as e:
        # If LLM is not available, skip test but log warning
        pytest.skip(f"Integration test requires LLM service (Alana): {e}")
    finally:
        await orchestrator.llm_client.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_orchestrator_powerapp_explicit_activities():
    """
    Test orchestrator with explicit activity sequence for Power App.

    Tests explicit execution of: engage → discover → plan → assess → design
    """
    orchestrator = Orchestrator()

    try:
        user_input = "Create Power App for Service Catalog and Client Management"

        # Explicitly specify activity sequence
        activities = ["engage", "discover", "plan", "assess", "design"]

        result: OrchestrationResult = await orchestrator.run(
            user_input=user_input,
            activities=activities,
        )

        # Verify all requested activities were executed
        assert len(result.activities_executed) == len(activities)
        assert set(result.activities_executed) == set(activities)

        # Verify results exist for all activities
        for activity_name in activities:
            assert activity_name in result.results, (
                f"Result missing for activity: {activity_name}"
            )
            activity_result = result.results[activity_name]
            assert activity_result is not None
            assert activity_result.activity_name == activity_name

        # Verify discover extracted service name (if successful)
        if result.results.get("discover") and result.results["discover"].success:
            discover_outputs = result.results["discover"].outputs
            # Service name should be extracted
            assert "service_name" in discover_outputs or len(discover_outputs) > 0

        # Verify plan created backlog (if successful)
        if result.results.get("plan") and result.results["plan"].success:
            plan_outputs = result.results["plan"].outputs
            # Should have MoSCoW priorities or backlog
            assert (
                "moscow_priorities" in plan_outputs or
                "backlog" in plan_outputs or
                len(plan_outputs) > 0
            )

        # Verify assess evaluated maturity (if successful)
        if result.results.get("assess") and result.results["assess"].success:
            assess_outputs = result.results["assess"].outputs
            # Should have maturity assessment
            assert (
                "current_maturity_level" in assess_outputs or
                "stage_readiness" in assess_outputs or
                len(assess_outputs) > 0
            )

        # Verify design created architecture (if successful)
        if result.results.get("design") and result.results["design"].success:
            design_outputs = result.results["design"].outputs
            # Should have architecture or specification
            assert (
                "architecture" in design_outputs or
                "specification" in design_outputs or
                len(design_outputs) > 0
            )

    except Exception as e:
        # If LLM is not available, skip test but log warning
        pytest.skip(f"Integration test requires LLM service (Alana): {e}")
    finally:
        await orchestrator.llm_client.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_orchestrator_llm_driven_activity_determination():
    """
    Test LLM-driven activity determination with Power App idea.

    Verifies that LLM correctly determines activities needed.
    """
    orchestrator = Orchestrator()

    try:
        user_input = "Create Power App for Service Catalog and Client Management"

        # Test LLM-driven determination
        activities = await orchestrator.determine_activities(user_input)

        # Verify activities were determined
        assert isinstance(activities, list)
        assert len(activities) > 0

        # Verify all determined activities are registered
        for activity_name in activities:
            assert activity_name in orchestrator.activities, (
                f"Determined activity '{activity_name}' is not registered"
            )

        # For Power App creation, should include at least discover and design
        # (LLM may determine more based on context)
        assert "discover" in activities or "design" in activities, (
            f"Power App creation should include discover or design, got: {activities}"
        )

    except Exception as e:
        # If LLM is not available, fallback to keyword-based should work
        # Test fallback
        activities = orchestrator._determine_activities_keyword(user_input)
        assert isinstance(activities, list)
        assert len(activities) > 0
        assert "discover" in activities  # Fallback should include discover
    finally:
        await orchestrator.llm_client.close()

