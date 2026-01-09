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

    async def call_llm(
        self, 
        system_prompt: str, 
        user_message: str, 
        max_tokens: int = 512,
        response_format: Optional[dict] = None,
    ) -> Dict:
        """
        Call LLM and parse JSON response.

        Args:
            system_prompt: System prompt
            user_message: User message
            max_tokens: Maximum tokens for response (default: 512)

        Returns:
            Parsed JSON response

        Raises:
            ValueError: If response cannot be parsed as JSON
        """
        response = await self.llm_client.chat_completion(
            system_prompt, 
            user_message, 
            max_tokens=max_tokens,
            response_format=response_format,
        )

        # #region agent log
        import json as json_module
        import time
        from pathlib import Path
        # Calculate log path from workspace root
        workspace_root = self.context_builder.workspace_root
        log_path = workspace_root / ".cursor" / "debug.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_entry = {
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": "B",
            "location": "activity.py:144",
            "message": "BEFORE JSON parsing - raw response",
            "data": {
                "response_length": len(response),
                "response_preview": response[:500] if response else None,
                "max_tokens_requested": max_tokens
            },
            "timestamp": int(time.time() * 1000)
        }
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json_module.dumps(log_entry) + "\n")
        except:
            pass
        # #endregion

        # Try to parse JSON from response
        try:
            # Extract JSON from markdown code blocks if present
            json_content = response.strip()
            
            # First, try to extract from markdown fences (handle explanatory text before fences)
            if "```json" in json_content:
                # Find all occurrences of ```json
                json_start = json_content.find("```json")
                # Skip past the fence marker
                json_start = json_content.find("\n", json_start) + 1
                # Find the closing fence
                json_end = json_content.find("```", json_start)
                if json_end > json_start:
                    json_content = json_content[json_start:json_end].strip()
                else:
                    # No closing fence, take everything after ```json
                    json_content = json_content[json_start:].strip()
            elif "```" in json_content:
                # Handle generic code fences (might be ```python or just ```)
                json_start = json_content.find("```")
                # Check if it's a language-specific fence
                fence_end_marker = json_content.find("\n", json_start)
                if fence_end_marker > json_start:
                    json_start = fence_end_marker + 1
                else:
                    json_start = json_start + 3
                # Find closing fence
                json_end = json_content.find("```", json_start)
                if json_end > json_start:
                    json_content = json_content[json_start:json_end].strip()
                else:
                    json_content = json_content[json_start:].strip()

            # Remove any explanatory text before the first {
            # Handle cases like "Here is the JSON:\n\n{...}" or "Response:\n{...}"
            if not json_content.strip().startswith("{"):
                start_brace = json_content.find("{")
                if start_brace >= 0:
                    # Remove everything before the first {
                    json_content = json_content[start_brace:]
                else:
                    # No { found, try to find JSON array
                    start_bracket = json_content.find("[")
                    if start_bracket >= 0:
                        json_content = json_content[start_bracket:]
            
            # Find the last complete JSON object (handle trailing text)
            if json_content.strip().startswith("{"):
                # Find the matching closing brace
                brace_count = 0
                end_pos = -1
                for i, char in enumerate(json_content):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = i
                            break
                if end_pos > 0:
                    json_content = json_content[:end_pos + 1]

            # Fix common JSON issues before parsing
            import re
            # Remove trailing commas before } or ]
            json_content = re.sub(r',(\s*[}\]])', r'\1', json_content)
            # Handle truncated responses: find the largest complete JSON object
            # First, try to find complete JSON by matching braces
            brace_count = 0
            start_idx = -1
            last_valid_end = -1
            for i, char in enumerate(json_content):
                if char == '{':
                    if brace_count == 0:
                        start_idx = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_idx >= 0:
                        last_valid_end = i
                    elif brace_count < 0:  # Unmatched closing brace
                        break

            # Use the last complete JSON object found
            if start_idx >= 0 and last_valid_end > start_idx:
                json_content = json_content[start_idx:last_valid_end + 1]
            elif start_idx >= 0:
                # Incomplete JSON - try to close it by finding all open structures
                # Count unmatched braces and close them
                open_braces = json_content[start_idx:].count('{') - json_content[start_idx:].count('}')
                open_brackets = json_content[start_idx:].count('[') - json_content[start_idx:].count(']')

                # Close unmatched quotes (find strings that aren't closed)
                # Pattern: find ": "value that doesn't end with quote
                json_content_fixed = json_content[start_idx:]

                # Close any unterminated strings at end of response
                lines = json_content_fixed.split('\n')
                fixed_lines = []
                for line in lines:
                    # If line has unclosed string (": "value without closing quote), close it
                    if '": "' in line and not line.strip().endswith('"') and not line.strip().endswith(','):
                        # Find the last ": "pattern and ensure string is closed
                        last_colon_quote = line.rfind('": "')
                        if last_colon_quote >= 0:
                            value_part = line[last_colon_quote + 4:]
                            if value_part and not value_part.endswith('"'):
                                line = line + '"'
                    fixed_lines.append(line)

                json_content_fixed = '\n'.join(fixed_lines)

                # Close unmatched braces/brackets
                json_content_fixed += '}' * open_braces
                json_content_fixed += ']' * open_brackets
                json_content = json_content_fixed
                logger.warning(f"JSON appears truncated, attempting to repair...")

            # Fix common JSON issues before parsing
            # Remove trailing commas before } or ]
            json_content = re.sub(r',(\s*[}\]])', r'\1', json_content)
            # Fix unterminated strings (close strings that aren't properly closed)
            # Pattern: find "key": "value that doesn't end with quote before comma/brace
            json_content = re.sub(r':\s*"([^"]*?)\n(\s*[,}\]])', r': "\1"\2', json_content)
            # Fix unclosed strings at end of truncated response
            json_content = re.sub(r':\s*"([^"]+?)$', r': "\1"', json_content, flags=re.MULTILINE)
            # Fix missing commas between object properties
            json_content = re.sub(r'"\s*\n\s*"', '",\n        "', json_content)
            # Fix missing colons in key:value pairs
            json_content = re.sub(r'"\s+([{[])', r'": \1', json_content)  # "key { -> "key": {

            # #region agent log
            log_entry2 = {
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "B",
                "location": "activity.py:230",
                "message": "AFTER JSON extraction - extracted content",
                "data": {
                    "extracted_json_length": len(json_content),
                    "extracted_preview": json_content[:500] if json_content else None,
                    "has_start_brace": json_content.strip().startswith("{") if json_content else False,
                    "has_end_brace": json_content.strip().endswith("}") if json_content else False,
                    "was_truncated": last_valid_end < len(response) - 50 if response else False
                },
                "timestamp": int(time.time() * 1000)
            }
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json_module.dumps(log_entry2) + "\n")
            except:
                pass
            # #endregion

            return json.loads(json_content)
        except json.JSONDecodeError as e:
            logger.warning(f"Could not parse LLM response as JSON: {e}")
            logger.warning(f"Response: {response[:500]}")
            # Try to fix common JSON issues
            try:
                import re
                # Remove trailing commas before } or ]
                json_content = re.sub(r',(\s*[}\]])', r'\1', json_content)
                return json.loads(json_content)
            except Exception:
                # Return raw response as dict to allow activity to continue
                return {"raw_response": response}
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

