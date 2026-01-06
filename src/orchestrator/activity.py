"""
Activity Base Class - Abstract base class for all activities

Activities are AI agents that use LLM to make autonomous decisions.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .context import ContextBuilder
from .llm_client import LLMClient
from .playbooks import Playbook, PlaybookRegistry
from .state import ActivityHistory, Manifest

logger = logging.getLogger(__name__)


@dataclass
class ActivityContext:
    """Context for activity execution."""

    activity_name: str
    service_name: Optional[str] = None
    user_input: Optional[str] = None
    specification: Optional[Dict] = None
    manifest: Optional[Dict] = None
    tools: Optional[List[Dict]] = None
    history: Optional[List[Dict]] = None


@dataclass
class ActivityResult:
    """Result of activity execution."""

    activity_name: str
    success: bool
    outputs: Dict[str, Any]
    errors: List[str]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}


class Activity(ABC):
    """
    Abstract base class for all activities.
    
    Activities are AI agents that:
    - Use LLM to make decisions (not hardcoded logic)
    - Load context (specification, manifest, tools, history)
    - Format prompts with injected context
    - Call LLM for decision-making
    - Execute playbooks/tools based on LLM decisions
    - Update manifest with results
    - Record history for self-learning
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        context_builder: Optional[ContextBuilder] = None,
        playbook_registry: Optional[PlaybookRegistry] = None,
        workspace_root: Optional[Any] = None,
    ):
        """
        Initialize activity.
        
        Args:
            llm_client: LLM client instance. If None, creates new one.
            context_builder: Context builder instance. If None, creates new one.
            playbook_registry: Playbook registry instance. If None, creates new one.
            workspace_root: Workspace root path (for context builder).
        """
        self.llm_client = llm_client or LLMClient()
        self.context_builder = context_builder or ContextBuilder(workspace_root=workspace_root)
        self.playbook_registry = playbook_registry or PlaybookRegistry(workspace_root=workspace_root)
        self.name = self.__class__.__name__.replace("Activity", "").lower()

    @abstractmethod
    async def execute(self, context: ActivityContext) -> ActivityResult:
        """
        Execute the activity.
        
        Args:
            context: Activity context
            
        Returns:
            ActivityResult
        """
        pass

    def format_prompt(self, context: Dict, history: Optional[List[Dict]] = None) -> str:
        """
        Format system prompt with context.
        
        Args:
            context: Context dictionary
            history: Optional history entries
            
        Returns:
            Formatted system prompt
        """
        # Base implementation - subclasses should override
        prompt_parts = [
            f"You are the {self.name} activity agent for SPECTRA orchestrator.",
            "",
            "CONTEXT:",
            json.dumps(context, indent=2),
        ]
        
        if history:
            prompt_parts.extend([
                "",
                "HISTORY (past decisions/outcomes):",
                json.dumps(history, indent=2),
            ])
        
        return "\n".join(prompt_parts)

    async def call_llm(self, system_prompt: str, user_message: str) -> Dict:
        """
        Call LLM and parse JSON response.
        
        Args:
            system_prompt: System prompt
            user_message: User message
            
        Returns:
            Parsed JSON response
            
        Raises:
            ValueError: If response cannot be parsed as JSON
        """
        response = await self.llm_client.chat_completion(system_prompt, user_message)
        
        # Try to parse JSON from response
        try:
            # Extract JSON from markdown code blocks if present
            json_content = response
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_content = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                if json_end > json_start:
                    json_content = response[json_start:json_end].strip()
            
            return json.loads(json_content)
        except json.JSONDecodeError as e:
            logger.warning(f"Could not parse LLM response as JSON: {e}")
            logger.warning(f"Response: {response[:200]}...")
            # Return raw response as dict
            return {"raw_response": response}

    async def execute_playbook(self, playbook_name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a playbook.
        
        Args:
            playbook_name: Playbook name
            args: Arguments to pass to playbook
            
        Returns:
            Execution result
        """
        playbook = self.playbook_registry.get_playbook(playbook_name)
        if not playbook:
            raise ValueError(f"Playbook not found: {playbook_name}")
        
        return self.playbook_registry.execute_playbook(playbook, args)

    def update_manifest(self, manifest: Manifest, outputs: Dict[str, Any]):
        """
        Update manifest with outputs.
        
        Args:
            manifest: Manifest object
            outputs: Outputs to add
        """
        for name, value in outputs.items():
            manifest.add_output(name, value)

    def record_history(
        self,
        history: ActivityHistory,
        decision: Dict[str, Any],
        outcome: str,
        result: ActivityResult,
        context: Optional[Dict] = None,
    ):
        """
        Record activity execution in history.
        
        Args:
            history: ActivityHistory object
            decision: Decision made by LLM
            outcome: "success" or "failure"
            result: ActivityResult
            context: Optional context used
        """
        history.add_entry(
            decision=decision,
            context=context or {},
            outcome=outcome,
            result={
                "outputs": result.outputs,
                "errors": result.errors,
                **result.metadata,
            },
        )

    def load_history(self) -> ActivityHistory:
        """
        Load activity history.
        
        Returns:
            ActivityHistory object
        """
        return self.context_builder.load_history(self.name)

