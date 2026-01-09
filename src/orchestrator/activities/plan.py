"""
Plan Activity - MoSCoW prioritization, requirements breakdown, milestone planning

SPECTRA-Grade planning activity that creates structured backlogs and milestone plans.
"""

import json
import logging
from typing import Dict, Optional

from ..activity import Activity, ActivityContext, ActivityResult

logger = logging.getLogger(__name__)


class Plan(Activity):
    """
    Plan - MoSCoW prioritization and milestone planning activity.

    Uses LLM to analyze requirements and create:
    - Prioritized backlog (Must Have, Should Have, Could Have, Won't Have)
    - Milestone timeline
    - Requirements breakdown
    """

    async def execute(self, context: ActivityContext) -> ActivityResult:
        """
        Execute plan activity.

        Args:
            context: Activity context

        Returns:
            ActivityResult with planning outputs
        """
        logger.info(f"Executing Plan activity for: {context.user_input}")

        # Build context for planning
        activity_context = self.context_builder.build_activity_context(
            activity_name="plan",
            service_name=context.service_name,
            specification=context.specification,
            manifest=context.manifest,
        )

        # Format prompt for MoSCoW prioritization
        system_prompt = self.format_prompt(context=activity_context)

        user_message = f"""
Analyze the requirements and create a comprehensive plan for: {context.user_input}

PLANNING TASKS:
1. MoSCoW Prioritization:
   - Must Have: Essential features without which the solution fails
   - Should Have: Important features that add significant value
   - Could Have: Nice-to-have features if time permits
   - Won't Have: Excluded features (for this iteration)

2. Requirements Breakdown:
   - Functional requirements
   - Non-functional requirements
   - Technical requirements
   - Business requirements

3. Milestone Planning:
   - Define clear milestones with deliverables
   - Estimate timeline for each milestone
   - Identify dependencies between milestones

4. Backlog Structure:
   - Organize requirements into actionable tasks
   - Prioritize tasks within each MoSCoW category
   - Identify risks and blockers

Respond in JSON format with:
- moscow_priorities: {{must_have: [], should_have: [], could_have: [], wont_have: []}}
- requirements_breakdown: {{functional: [], non_functional: [], technical: [], business: []}}
- milestones: [{{name, description, deliverables: [], timeline, dependencies: []}}]
- backlog: [{{task, priority, category, effort_estimate, dependencies: []}}]
"""

        try:
            # Call LLM for planning
            logger.debug("Calling LLM for planning analysis...")
            llm_response = await self.call_llm(system_prompt, user_message, max_tokens=2048)

            # Extract planning results
            moscow_priorities = llm_response.get("moscow_priorities", {
                "must_have": [],
                "should_have": [],
                "could_have": [],
                "wont_have": [],
            })
            requirements_breakdown = llm_response.get("requirements_breakdown", {
                "functional": [],
                "non_functional": [],
                "technical": [],
                "business": [],
            })
            milestones = llm_response.get("milestones", [])
            backlog = llm_response.get("backlog", [])

            outputs = {
                "moscow_priorities": moscow_priorities,
                "requirements_breakdown": requirements_breakdown,
                "milestones": milestones,
                "backlog": backlog,
            }

            logger.info("Planning complete")

            return ActivityResult(
                activity_name="plan",
                success=True,
                outputs=outputs,
                errors=[],
            )

        except Exception as e:
            logger.error(f"Plan activity failed: {e}", exc_info=True)
            return ActivityResult(
                activity_name="plan",
                success=False,
                outputs={},
                errors=[str(e)],
            )

    def format_prompt(self, context: Dict, history: Optional[list] = None) -> str:
        """
        Format system prompt for plan activity.

        Args:
            context: Context dictionary
            history: Optional history entries

        Returns:
            Formatted system prompt
        """
        prompt_parts = [
            "You are a SPECTRA Planning Analyst - an expert in MoSCoW prioritization and milestone planning.",
            "",
            "YOUR MISSION:",
            "Analyze requirements and create structured plans with MoSCoW prioritization, requirements breakdown,",
            "milestone planning, and actionable backlogs.",
            "",
            "MoSCoW PRIORITIZATION RULES:",
            "- Must Have: Essential features - solution fails without these",
            "- Should Have: Important features - significant value, but not critical",
            "- Could Have: Nice-to-have - valuable but not essential",
            "- Won't Have: Explicitly excluded - out of scope for this iteration",
            "",
            "MILESTONE PLANNING:",
            "- Define clear, measurable milestones",
            "- Each milestone should have concrete deliverables",
            "- Identify dependencies between milestones",
            "- Estimate realistic timelines",
            "",
            "BACKLOG STRUCTURE:",
            "- Break requirements into actionable tasks",
            "- Prioritize tasks within each MoSCoW category",
            "- Estimate effort (S/M/L/XL or hours)",
            "- Identify task dependencies",
            "",
        ]

        if context.get("specification_summary"):
            prompt_parts.append(f"SPECIFICATION SUMMARY:\n{context['specification_summary']}\n")
        if context.get("manifest_summary"):
            prompt_parts.append(f"MANIFEST SUMMARY:\n{context['manifest_summary']}\n")

        if history:
            prompt_parts.extend([
                "",
                "RECENT HISTORY:",
                json.dumps(history[-2:], indent=2),
            ])

        prompt_parts.extend([
            "",
            "OUTPUT FORMAT:",
            "Provide structured planning results in JSON format:",
            "- moscow_priorities: Categorized requirements",
            "- requirements_breakdown: Functional/non-functional/technical/business",
            "- milestones: Timeline with deliverables and dependencies",
            "- backlog: Prioritized actionable tasks",
        ])

        return "\n".join(prompt_parts)

