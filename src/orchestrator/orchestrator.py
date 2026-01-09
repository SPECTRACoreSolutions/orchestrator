"""
Orchestrator - Main orchestrator class

Runs activities and sequences execution.
"""

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .activity import Activity, ActivityContext, ActivityResult
from .activities.assess import Assess
from .activities.build import Build
from .activities.design import Design
from .activities.discover import Discover
from .activities.engage import Engage
from .activities.finalise import Finalise
from .activities.monitor import Monitor
from .activities.optimise import Optimise
from .activities.plan import Plan
from .activities.provision import Provision
from .activities.test import Test
from .activities.deploy import Deploy
from .context import ContextBuilder
from .llm_client import LLMClient
from .playbooks import PlaybookRegistry

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationResult:
    """Result of orchestration execution."""

    success: bool
    activities_executed: List[str]
    results: Dict[str, ActivityResult]
    errors: List[str]


class Orchestrator:
    """
    Main orchestrator class.

    Orchestrates activity execution and sequences activities.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        context_builder: Optional[ContextBuilder] = None,
        playbook_registry: Optional[PlaybookRegistry] = None,
        workspace_root: Optional[Path] = None,
    ):
        """
        Initialize orchestrator.

        Args:
            llm_client: LLM client instance. If None, creates new one.
            context_builder: Context builder instance. If None, creates new one.
            playbook_registry: Playbook registry instance. If None, creates new one.
            workspace_root: Workspace root path.
        """
        self.llm_client = llm_client or LLMClient()
        self.context_builder = context_builder or ContextBuilder(workspace_root=workspace_root)
        self.playbook_registry = playbook_registry or PlaybookRegistry(workspace_root=workspace_root)

        # Register all 12 activities
        self.activities: Dict[str, Activity] = {
            "engage": Engage(
                llm_client=self.llm_client,
                context_builder=self.context_builder,
                playbook_registry=self.playbook_registry,
                workspace_root=workspace_root,
            ),
            "discover": Discover(
                llm_client=self.llm_client,
                context_builder=self.context_builder,
                playbook_registry=self.playbook_registry,
                workspace_root=workspace_root,
            ),
            "plan": Plan(
                llm_client=self.llm_client,
                context_builder=self.context_builder,
                playbook_registry=self.playbook_registry,
                workspace_root=workspace_root,
            ),
            "assess": Assess(
                llm_client=self.llm_client,
                context_builder=self.context_builder,
                playbook_registry=self.playbook_registry,
                workspace_root=workspace_root,
            ),
            "design": Design(
                llm_client=self.llm_client,
                context_builder=self.context_builder,
                playbook_registry=self.playbook_registry,
                workspace_root=workspace_root,
            ),
            "provision": Provision(
                llm_client=self.llm_client,
                context_builder=self.context_builder,
                playbook_registry=self.playbook_registry,
                workspace_root=workspace_root,
            ),
            "build": Build(
                llm_client=self.llm_client,
                context_builder=self.context_builder,
                playbook_registry=self.playbook_registry,
                workspace_root=workspace_root,
            ),
            "test": Test(
                llm_client=self.llm_client,
                context_builder=self.context_builder,
                playbook_registry=self.playbook_registry,
                workspace_root=workspace_root,
            ),
            "deploy": Deploy(
                llm_client=self.llm_client,
                context_builder=self.context_builder,
                playbook_registry=self.playbook_registry,
                workspace_root=workspace_root,
            ),
            "monitor": Monitor(
                llm_client=self.llm_client,
                context_builder=self.context_builder,
                playbook_registry=self.playbook_registry,
                workspace_root=workspace_root,
            ),
            "optimise": Optimise(
                llm_client=self.llm_client,
                context_builder=self.context_builder,
                playbook_registry=self.playbook_registry,
                workspace_root=workspace_root,
            ),
            "finalise": Finalise(
                llm_client=self.llm_client,
                context_builder=self.context_builder,
                playbook_registry=self.playbook_registry,
                workspace_root=workspace_root,
            ),
        }

    async def run(
        self,
        user_input: str,
        activities: Optional[List[str]] = None,
        service_name: Optional[str] = None,
    ) -> OrchestrationResult:
        """
        Run orchestrator with user input.

        Args:
            user_input: User input/command
            activities: List of activities to run. If None, determines automatically.
            service_name: Optional service name

        Returns:
            OrchestrationResult
        """
        logger.info(f"Orchestrator run: {user_input}")

        # Determine activities if not provided
        if activities is None:
            activities = await self.determine_activities(user_input)

        logger.info(f"Activities to execute: {activities}")

        results: Dict[str, ActivityResult] = {}
        errors: List[str] = []

        # Execute activities in sequence
        for activity_name in activities:
            if activity_name not in self.activities:
                error_msg = f"Activity not found: {activity_name}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue

            try:
                activity = self.activities[activity_name]

                # Build context
                context = ActivityContext(
                    activity_name=activity_name,
                    service_name=service_name,
                    user_input=user_input,
                )

                # Execute activity
                logger.info(f"Executing activity: {activity_name}")
                result = await activity.execute(context)
                results[activity_name] = result

                if not result.success:
                    errors.extend(result.errors)
                    logger.warning(f"Activity {activity_name} failed: {result.errors}")
                    # Continue with next activity (don't stop on failure)

            except Exception as e:
                error_msg = f"Activity {activity_name} execution failed: {e}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
                results[activity_name] = ActivityResult(
                    activity_name=activity_name,
                    success=False,
                    outputs={},
                    errors=[error_msg],
                )

        success = len(errors) == 0 and all(r.success for r in results.values())

        return OrchestrationResult(
            success=success,
            activities_executed=activities,
            results=results,
            errors=errors,
        )

    async def run_activity(
        self,
        activity_name: str,
        context: ActivityContext,
    ) -> ActivityResult:
        """
        Run a single activity.

        Args:
            activity_name: Activity name
            context: Activity context

        Returns:
            ActivityResult

        Raises:
            ValueError: If activity not found
        """
        if activity_name not in self.activities:
            raise ValueError(f"Activity not found: {activity_name}")

        activity = self.activities[activity_name]
        return await activity.execute(context)

    async def determine_activities(self, user_input: str) -> List[str]:
        """
        Determine which activities to run based on user input (LLM-driven).

        Uses LLM to analyze user intent and determine the appropriate sequence
        of activities to execute.

        Args:
            user_input: User input/command

        Returns:
            List of activity names in execution order
        """
        # Build system prompt with available activities
        available_activities = {
            "engage": "Client registration and directory setup",
            "discover": "Problem understanding and solution validation",
            "plan": "MoSCoW prioritization, requirements breakdown, milestone planning",
            "assess": "Maturity assessment, readiness evaluation, stage completeness",
            "design": "Architecture generation, Specification creation",
            "provision": "Infrastructure provisioning",
            "build": "Code generation and compilation",
            "test": "Test execution and validation",
            "deploy": "Deployment to Railway",
            "monitor": "Health monitoring and metrics",
            "optimise": "Performance optimization",
            "finalise": "9-step finalize protocol",
        }

        activities_desc = "\n".join(
            [f"- {name}: {desc}" for name, desc in available_activities.items()]
        )

        system_prompt = f"""You are a SPECTRA Orchestrator activity planner.

Your task is to analyze user input and determine which activities should be executed
and in what order.

AVAILABLE ACTIVITIES:
{activities_desc}

ACTIVITY EXECUTION ORDER (typical sequence):
1. engage - First-time CLIENT registration (ONLY for external customer engagements)
2. discover - Understand problem and validate solution
3. plan - Prioritize requirements and plan milestones
4. assess - Evaluate maturity and readiness
5. design - Generate architecture and specification
6. provision - Set up infrastructure
7. build - Generate and compile code
8. test - Execute tests and validate
9. deploy - Deploy to production
10. monitor - Monitor health and metrics
11. optimise - Optimize performance
12. finalise - Complete finalize protocol

ENGAGE ACTIVITY - CRITICAL SKIP RULES:
❌ SKIP ENGAGE if:
   - Building internal SPECTRA services (portal, webhooks, etc.)
   - Creating Labs queue ideas (internal projects)
   - Building tools/services for SPECTRA itself
   - User input mentions "SPECTRA" + "service/tool/app" (internal project)
   - User input is about testing, development, or internal infrastructure

✅ USE ENGAGE only if:
   - First-time external customer/client engagement
   - Setting up new customer project
   - User explicitly mentions "client" or "customer" engagement

CONTEXT CLUES TO SKIP ENGAGE:
- "Build a SPECTRA..." → Internal service, SKIP ENGAGE
- "Create SPECTRA service..." → Internal service, SKIP ENGAGE
- "Power App for service catalog" → Internal tool, SKIP ENGAGE
- "Service catalog client manager" → Internal service, SKIP ENGAGE

NOTE: Not all activities are needed for every request. Select only the activities
that are appropriate for the user's intent. For example:
- "Build a SPECTRA service catalog app" → SKIP engage, use discover, plan, assess, design, provision, build, test, deploy
- "Create a new service for customer X" → engage, discover, plan, assess, design
- "Deploy the portal service" → deploy
- "Check service health" → monitor
- "Finalize the project" → finalise

Respond with a JSON object containing:
- activities: List of activity names in execution order
- reasoning: Brief explanation of why these activities were selected"""

        user_message = f"""Analyze this user input and determine which activities to execute:

"{user_input}"

Return JSON with activities array and reasoning."""

        try:
            # Call LLM for activity determination
            logger.debug("Calling LLM for activity determination...")
            response = await self.llm_client.chat_completion(
                system_prompt=system_prompt,
                user_message=user_message,
                max_tokens=512,
                temperature=0.3,
            )

            # Try to parse JSON response
            # Extract JSON from response (may be wrapped in markdown code blocks)
            json_match = re.search(r'\{[\s\S]*"activities"[\s\S]*\}', response)
            if json_match:
                response = json_match.group(0)

            try:
                result = json.loads(response)
                activities = result.get("activities", [])
                reasoning = result.get("reasoning", "")

                # Validate activities exist
                valid_activities = []
                for activity in activities:
                    if activity in self.activities:
                        valid_activities.append(activity)
                    else:
                        logger.warning(f"Invalid activity requested: {activity}")

                if reasoning:
                    logger.info(f"Activity determination reasoning: {reasoning}")

                # Default to discover if no valid activities found
                if not valid_activities:
                    logger.warning("No valid activities determined, defaulting to discover")
                    valid_activities = ["discover"]

                logger.info(f"Determined activities: {valid_activities}")
                return valid_activities

            except json.JSONDecodeError as e:
                logger.warning(f"Could not parse LLM response as JSON: {e}")
                logger.warning(f"Response: {response[:200]}...")
                # Fallback to keyword-based determination
                return self._determine_activities_keyword(user_input)

        except Exception as e:
            logger.warning(f"LLM-based activity determination failed: {e}, falling back to keyword-based")
            return self._determine_activities_keyword(user_input)

    def _determine_activities_keyword(self, user_input: str) -> List[str]:
        """
        Fallback keyword-based activity determination.

        Args:
            user_input: User input/command

        Returns:
            List of activity names
        """
        input_lower = user_input.lower()
        activities = []

        if any(keyword in input_lower for keyword in ["discover", "find", "understand", "analyse"]):
            activities.append("discover")

        if any(keyword in input_lower for keyword in ["plan", "prioritize", "moscow", "backlog"]):
            activities.append("plan")

        if any(keyword in input_lower for keyword in ["assess", "maturity", "readiness", "evaluate"]):
            activities.append("assess")

        if any(keyword in input_lower for keyword in ["design", "architecture", "specification"]):
            activities.append("design")

        if any(keyword in input_lower for keyword in ["build", "create", "generate", "make"]):
            activities.append("build")

        if any(keyword in input_lower for keyword in ["test", "validate", "check"]):
            activities.append("test")

        if any(keyword in input_lower for keyword in ["deploy", "publish", "release"]):
            activities.append("deploy")

        if any(keyword in input_lower for keyword in ["monitor", "health", "metrics"]):
            activities.append("monitor")

        if any(keyword in input_lower for keyword in ["optimise", "optimize", "performance"]):
            activities.append("optimise")

        if any(keyword in input_lower for keyword in ["finalise", "finalize", "complete"]):
            activities.append("finalise")

        # Default to discover if no activities determined
        if not activities:
            activities = ["discover"]

        return activities

