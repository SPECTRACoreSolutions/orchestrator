"""
Semantic Filter - LLM-based semantic filtering for context optimization

Industry-standard approach following OpenAI, Anthropic, LangChain patterns.
Replaces prompt truncation with intelligent content selection.
"""

import json
import logging
from typing import Dict, List, Optional

from .playbooks import Playbook
from .llm_client import LLMClient

logger = logging.getLogger(__name__)


class SemanticFilter:
    """
    LLM-based semantic filtering for playbooks and context.

    Uses LLM to intelligently select most relevant items based on task understanding,
    reducing prompt size while maintaining accuracy.

    Pattern: Pre-filtering via LLM before main execution (industry standard)
    """

    def __init__(self, llm_client: LLMClient, max_items: int = 5):
        """
        Initialize semantic filter.

        Args:
            llm_client: LLM client for filtering
            max_items: Maximum items to return (default: 5)
        """
        self.llm_client = llm_client
        self.max_items = max_items

    async def filter_playbooks(
        self,
        activity_name: str,
        task: str,
        all_playbooks: List[Playbook],
        max_playbooks: Optional[int] = None,
    ) -> List[Playbook]:
        """
        Filter playbooks to most relevant for task using LLM.

        Args:
            activity_name: Activity name (e.g., "provision")
            task: User task description
            all_playbooks: All available playbooks
            max_playbooks: Maximum playbooks to return (defaults to self.max_items)

        Returns:
            List of most relevant playbooks (top N)
        """
        if not all_playbooks:
            logger.warning("No playbooks provided for filtering")
            return []

        max_playbooks = max_playbooks or self.max_items

        # If we have fewer playbooks than max, return all
        if len(all_playbooks) <= max_playbooks:
            logger.debug(f"Playbook count ({len(all_playbooks)}) <= max ({max_playbooks}), returning all")
            return all_playbooks

        logger.info(f"Filtering {len(all_playbooks)} playbooks to top {max_playbooks} for task: {task[:100]}...")

        try:
            # Build filter prompt
            filter_prompt = self._build_filter_prompt(
                activity_name=activity_name,
                task=task,
                all_playbooks=all_playbooks,
                max_playbooks=max_playbooks,
            )

            # Call LLM for filtering
            logger.debug("Calling LLM for semantic filtering...")
            response = await self.llm_client.chat_completion(
                system_prompt=filter_prompt["system"],
                user_message=filter_prompt["user"],
                max_tokens=512,
                temperature=0.3,
            )

            # Parse response
            selected_names = self._parse_filter_response(response)

            # Map names to playbooks
            playbook_map = {pb.name: pb for pb in all_playbooks}
            filtered_playbooks = [
                playbook_map[name] for name in selected_names
                if name in playbook_map
            ]

            logger.info(f"Filtered to {len(filtered_playbooks)} playbooks: {[pb.name for pb in filtered_playbooks]}")

            # Fallback: if filtering returned too few, add highest priority playbooks
            if len(filtered_playbooks) < min(3, len(all_playbooks)):
                logger.warning(f"Filtering returned only {len(filtered_playbooks)} playbooks, adding fallbacks")
                remaining = [pb for pb in all_playbooks if pb not in filtered_playbooks]
                filtered_playbooks.extend(remaining[:max(0, max_playbooks - len(filtered_playbooks))])

            return filtered_playbooks[:max_playbooks]

        except Exception as e:
            logger.error(f"Semantic filtering failed: {e}", exc_info=True)
            logger.warning(f"Falling back to first {max_playbooks} playbooks")
            # Fallback: return first N playbooks
            return all_playbooks[:max_playbooks]

    async def filter_context(
        self,
        task: str,
        items: List[Dict],
        item_description_key: str = "description",
        max_items: Optional[int] = None,
    ) -> List[Dict]:
        """
        Generic semantic filtering for any list of items.

        Args:
            task: User task description
            items: List of items to filter
            item_description_key: Key for item description (default: "description")
            max_items: Maximum items to return (defaults to self.max_items)

        Returns:
            List of most relevant items
        """
        if not items:
            return []

        max_items = max_items or self.max_items

        if len(items) <= max_items:
            return items

        logger.info(f"Filtering {len(items)} items to top {max_items} for task: {task[:100]}...")

        try:
            # Build simplified filter prompt
            system_prompt = """You are a semantic filter that selects the most relevant items for a task.

Your job is to analyze the task and select the most relevant items from a list.

Respond with JSON: {"selected_items": [index1, index2, ...]}
where indices are 0-based positions in the items list."""

            user_message = f"""Task: {task}

Available items ({len(items)}):
{json.dumps([{
    "index": i,
    "name": item.get("name", f"item_{i}"),
    "description": item.get(item_description_key, "")[:200]
} for i, item in enumerate(items)], indent=2)}

Select the {max_items} most relevant items for this task.
Return JSON: {{"selected_items": [...]}}"""

            # Call LLM
            response = await self.llm_client.chat_completion(
                system_prompt=system_prompt,
                user_message=user_message,
                max_tokens=512,
                temperature=0.3,
            )

            # Parse response
            try:
                # Extract JSON
                json_content = response
                if "```json" in response:
                    json_start = response.find("```json") + 7
                    json_end = response.find("```", json_start)
                    json_content = response[json_start:json_end].strip()

                result = json.loads(json_content)
                selected_indices = result.get("selected_items", [])

                # Validate indices
                filtered_items = [
                    items[i] for i in selected_indices
                    if isinstance(i, int) and 0 <= i < len(items)
                ]

                logger.info(f"Filtered to {len(filtered_items)} items")
                return filtered_items[:max_items]

            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Could not parse filter response: {e}")
                return items[:max_items]

        except Exception as e:
            logger.error(f"Context filtering failed: {e}", exc_info=True)
            return items[:max_items]

    def _build_filter_prompt(
        self,
        activity_name: str,
        task: str,
        all_playbooks: List[Playbook],
        max_playbooks: int,
    ) -> Dict[str, str]:
        """
        Build filter prompt for LLM.

        Args:
            activity_name: Activity name
            task: User task
            all_playbooks: All playbooks
            max_playbooks: Max to select

        Returns:
            Dict with "system" and "user" prompts
        """
        system_prompt = """You are a SPECTRA Playbook Selector - an expert in selecting the most relevant playbooks for a task.

Your job is to analyze the user's task and select the most relevant playbooks that will help accomplish that task.

SELECTION CRITERIA:
1. Task Requirements - Does the playbook directly address the task?
2. Domain Match - Does the playbook domain match the task domain (e.g., Railway, GitHub)?
3. Capability Match - Do the playbook's capabilities align with what's needed?
4. MCP-Native Preference - Prefer playbooks marked as MCP-native when available
5. Automation - Prefer playbooks that can be automated over manual ones

IMPORTANT:
- Be selective - only choose playbooks that are DIRECTLY relevant
- Quality over quantity - better to select 3 highly relevant than 5 somewhat relevant
- Consider the complete workflow - select playbooks that work together
- Avoid redundant playbooks that do similar things

Respond with JSON: {"selected_playbooks": ["playbook1", "playbook2", ...], "reasoning": "brief explanation"}"""

        # Build playbook summaries (minimal to save tokens)
        playbook_summaries = []
        for pb in all_playbooks:
            summary = {
                "name": pb.name,
                "description": pb.description[:200],  # Limit description length
                "domain": pb.metadata.get("domain", "unknown"),
                "mcp_native": pb.metadata.get("mcp_native", False),
                "automation_possible": pb.metadata.get("automation_possible", True),
            }
            playbook_summaries.append(summary)

        user_message = f"""Activity: {activity_name}
Task: {task}

Available playbooks ({len(all_playbooks)}):
{json.dumps(playbook_summaries, indent=2)}

Select the {max_playbooks} most relevant playbooks for this task.
Consider the task requirements, domain match, and automation capabilities.

Return JSON: {{"selected_playbooks": [...], "reasoning": "..."}}"""

        return {
            "system": system_prompt,
            "user": user_message,
        }

    def _parse_filter_response(self, response: str) -> List[str]:
        """
        Parse LLM filter response to extract selected playbook names.

        Args:
            response: LLM response

        Returns:
            List of selected playbook names
        """
        try:
            # Extract JSON from response
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

            # Try to find JSON object if not in code block
            if not json_content.strip().startswith("{"):
                start_brace = json_content.find("{")
                end_brace = json_content.rfind("}")
                if start_brace >= 0 and end_brace > start_brace:
                    json_content = json_content[start_brace:end_brace + 1]

            # Parse JSON
            result = json.loads(json_content)
            selected = result.get("selected_playbooks", [])

            if result.get("reasoning"):
                logger.debug(f"Filter reasoning: {result['reasoning']}")

            return selected

        except json.JSONDecodeError as e:
            logger.warning(f"Could not parse filter response as JSON: {e}")
            logger.warning(f"Response: {response[:200]}...")
            return []
        except Exception as e:
            logger.error(f"Error parsing filter response: {e}")
            return []

