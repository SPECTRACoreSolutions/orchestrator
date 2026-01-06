"""
Orchestrator - Main orchestrator class

Runs activities and sequences execution.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .activity import Activity, ActivityContext, ActivityResult
from .activities.discover import DiscoverActivity
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
        
        # Register activities
        self.activities: Dict[str, Activity] = {
            "discover": DiscoverActivity(
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
            activities = self.determine_activities(user_input)
        
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

    def determine_activities(self, user_input: str) -> List[str]:
        """
        Determine which activities to run based on user input.
        
        Args:
            user_input: User input/command
            
        Returns:
            List of activity names
        """
        input_lower = user_input.lower()
        
        # Simple keyword-based determination (can be enhanced with LLM later)
        activities = []
        
        if any(keyword in input_lower for keyword in ["discover", "find", "understand", "analyse"]):
            activities.append("discover")
        
        if any(keyword in input_lower for keyword in ["build", "create", "generate", "make"]):
            # Build activity will be added later
            pass
        
        if any(keyword in input_lower for keyword in ["test", "validate", "check"]):
            # Test activity will be added later
            pass
        
        if any(keyword in input_lower for keyword in ["deploy", "publish", "release"]):
            # Deploy activity will be added later
            pass
        
        # Default to discover if no activities determined
        if not activities:
            activities = ["discover"]
        
        return activities

