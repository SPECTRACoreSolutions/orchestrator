"""
Assess Activity - Maturity assessment, readiness evaluation, stage completeness checks

SPECTRA-Grade assessment activity that evaluates services against The Seven Levels of Maturity.
"""

import json
import logging
from typing import Dict, Optional

from ..activity import Activity, ActivityContext, ActivityResult

logger = logging.getLogger(__name__)


class Assess(Activity):
    """
    Assess - Maturity assessment and readiness evaluation activity.

    Uses LLM to evaluate services against:
    - The Seven Levels of Maturity (L1-MVP through L7-Autonomous)
    - Stage completeness checks
    - Readiness evaluation
    - Gap analysis
    """

    async def execute(self, context: ActivityContext) -> ActivityResult:
        """
        Execute assess activity.

        Args:
            context: Activity context

        Returns:
            ActivityResult with assessment outputs
        """
        logger.info(f"Executing Assess activity for: {context.user_input}")

        # Build context for assessment
        activity_context = self.context_builder.build_activity_context(
            activity_name="assess",
            service_name=context.service_name,
            specification=context.specification,
            manifest=context.manifest,
        )

        # Format prompt for maturity assessment
        system_prompt = self.format_prompt(context=activity_context)

        user_message = f"""
Assess the current state and maturity level for: {context.user_input}

ASSESSMENT TASKS:
1. Maturity Assessment:
   - Evaluate against The Seven Levels of Maturity (L1-MVP through L7-Autonomous)
   - Determine current maturity level
   - Identify gaps to reach next level
   - Assess progress toward target maturity

2. Stage Readiness:
   - Evaluate readiness for each stage (Discover, Plan, Design, Build, Test, Deploy, Optimise, Finalise)
   - Identify what's complete vs. incomplete
   - Assess quality of artifacts produced

3. Gap Analysis:
   - Identify what's missing to reach target maturity
   - List specific gaps and blockers
   - Prioritize gaps by impact

4. Readiness Scores:
   - Score readiness for each stage (0-100)
   - Overall readiness score
   - Confidence level in assessment

THE SEVEN LEVELS OF MATURITY:
- L1-MVP: Prototype, minimum viable
- L2-Alpha: Experimental, feedback-driven
- L3-Beta: Stable, production-ready
- L4-Live: Public, available
- L5-Reactive: Optimized, responds to issues
- L6-Proactive: Intelligent, anticipates needs
- L7-Autonomous: Self-governing, transcendent

Respond in JSON format with:
- current_maturity_level: L1-L7
- target_maturity_level: L1-L7
- maturity_gaps: [{{level, gaps: [], blockers: []}}]
- stage_readiness: {{discover: score, plan: score, design: score, build: score, test: score, deploy: score, optimise: score, finalise: score}}
- overall_readiness_score: 0-100
- gap_analysis: [{{gap, impact, priority, stage}}]
- readiness_summary: "text summary"
"""

        try:
            # Call LLM for assessment
            logger.debug("Calling LLM for maturity assessment...")
            llm_response = await self.call_llm(system_prompt, user_message, max_tokens=2048)

            # Extract assessment results
            current_maturity_level = llm_response.get("current_maturity_level", "L1")
            target_maturity_level = llm_response.get("target_maturity_level", "L1")
            maturity_gaps = llm_response.get("maturity_gaps", [])
            stage_readiness = llm_response.get("stage_readiness", {})
            overall_readiness_score = llm_response.get("overall_readiness_score", 0)
            gap_analysis = llm_response.get("gap_analysis", [])
            readiness_summary = llm_response.get("readiness_summary", "")

            outputs = {
                "current_maturity_level": current_maturity_level,
                "target_maturity_level": target_maturity_level,
                "maturity_gaps": maturity_gaps,
                "stage_readiness": stage_readiness,
                "overall_readiness_score": overall_readiness_score,
                "gap_analysis": gap_analysis,
                "readiness_summary": readiness_summary,
            }

            logger.info(f"Assessment complete: {current_maturity_level} → {target_maturity_level}")

            return ActivityResult(
                activity_name="assess",
                success=True,
                outputs=outputs,
                errors=[],
            )

        except Exception as e:
            logger.error(f"Assess activity failed: {e}", exc_info=True)
            return ActivityResult(
                activity_name="assess",
                success=False,
                outputs={},
                errors=[str(e)],
            )

    def format_prompt(self, context: Dict, history: Optional[list] = None) -> str:
        """
        Format system prompt for assess activity.

        Args:
            context: Context dictionary
            history: Optional history entries

        Returns:
            Formatted system prompt
        """
        prompt_parts = [
            "You are a SPECTRA Assessment Analyst - an expert in maturity evaluation and readiness assessment.",
            "",
            "YOUR MISSION:",
            "Evaluate services against The Seven Levels of Maturity and assess readiness for each stage.",
            "",
            "THE SEVEN LEVELS OF MATURITY:",
            "- L1-MVP: Prototype, minimum viable, basic functionality",
            "- L2-Alpha: Experimental, feedback-driven, iterative improvement",
            "- L3-Beta: Stable, production-ready, reliable",
            "- L4-Live: Public, available, accessible to users",
            "- L5-Reactive: Optimized, responds to issues, self-healing",
            "- L6-Proactive: Intelligent, anticipates needs, predictive",
            "- L7-Autonomous: Self-governing, transcendent, fully autonomous",
            "",
            "STAGE READINESS CRITERIA:",
            "- Discover: Problem understood, requirements captured, solution validated",
            "- Plan: MoSCoW priorities set, milestones defined, backlog created",
            "- Design: Architecture defined, specification complete, structure designed",
            "- Build: Code written, tests passing, quality gates met",
            "- Test: Tests comprehensive, coverage adequate, quality validated",
            "- Deploy: Deployed successfully, health checks passing, monitoring active",
            "- Optimise: Performance tuned, metrics optimal, improvements applied",
            "- Finalise: Documentation complete, artifacts saved, protocol followed",
            "",
            "ASSESSMENT APPROACH:",
            "- Be objective and evidence-based",
            "- Identify specific gaps with actionable items",
            "- Score readiness honestly (0-100 scale)",
            "- Prioritize gaps by impact on maturity progression",
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
            "Provide comprehensive assessment results in JSON format:",
            "- current_maturity_level: L1-L7",
            "- target_maturity_level: L1-L7",
            "- maturity_gaps: Gaps to reach target level",
            "- stage_readiness: Readiness scores for each stage",
            "- overall_readiness_score: 0-100",
            "- gap_analysis: Prioritized list of gaps",
            "- readiness_summary: Text summary of assessment",
        ])

        return "\n".join(prompt_parts)

