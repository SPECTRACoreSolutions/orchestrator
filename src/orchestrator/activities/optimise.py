"""
Optimise Activity - Performance optimization

SPECTRA-Grade optimization activity.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

from ..activity import Activity, ActivityContext, ActivityResult
from ..state import ActivityHistory, Manifest

logger = logging.getLogger(__name__)


class Optimise(Activity):
    """
    Optimise - Performance optimization activity.

    Uses LLM to analyze metrics and implement optimizations autonomously.
    """

    async def execute(self, context: ActivityContext) -> ActivityResult:
        """
        Execute optimise activity.

        Args:
            context: Activity context

        Returns:
            ActivityResult with optimization outputs
        """
        logger.info(f"Executing Optimise activity for: {context.user_input}")

        workspace_root = self.context_builder.workspace_root

        # Build context for optimization
        activity_context = self.context_builder.build_activity_context(
            activity_name="optimise",
            service_name=context.service_name,
            specification=context.specification,
            manifest=context.manifest,
        )

        # Get playbook metadata for optimization
        # Use semantic filtering to get most relevant playbooks
        filtered_playbooks = await self.playbook_registry.filter_relevant_playbooks(
            activity_name="optimise",
            task=context.user_input,
            llm_client=self.llm_client,
            max_playbooks=5,
        )

        # Get playbook context with filtered playbooks
        playbook_context = self.playbook_registry.get_playbook_context_for_llm(
            activity_name="optimise",
            playbooks=filtered_playbooks,
        )

        # Load history
        history = self.load_history()
        recent_history = history.get_recent(2)
        history_summary = []
        for entry in recent_history:
            entry_dict = entry.__dict__
            summary = {
                "decision": str(entry_dict.get("decision", ""))[:200] if entry_dict.get("decision") else None,
                "outcome": entry_dict.get("outcome"),
                "timestamp": entry_dict.get("timestamp"),
            }
            history_summary.append(summary)

        # Format prompt for optimization
        system_prompt = self.format_prompt(context=activity_context, history=history_summary)

        user_message = f"""
Analyze performance and optimize service for: {context.user_input}

OPTIMIZATION TASKS:
1. Performance Analysis:
   - Analyze current performance metrics (latency, throughput, resource usage)
   - Identify bottlenecks and optimization opportunities
   - Determine optimization priorities

2. Optimization Opportunities:
   - Identify code-level optimizations
   - Identify infrastructure optimizations
   - Identify configuration optimizations

3. Optimization Implementation:
   - Implement code optimizations
   - Apply infrastructure optimizations
   - Update configuration settings

4. Validation:
   - Validate performance improvements
   - Verify no regressions
   - Confirm metrics improved

AVAILABLE PLAYBOOKS:
{json.dumps(playbook_context.get("available_playbooks", []), indent=2)}

SPECTRA OPTIMIZATION STANDARDS:
- Data-driven: Optimize based on metrics, not assumptions
- Autonomous learning: Learn from historical data
- No regressions: Optimize without breaking functionality
- Measurable impact: Quantify improvements

Respond in JSON format with:
- performance_analysis: {{"current_metrics": {{}}, "bottlenecks": [], "priorities": []}}
- optimization_opportunities: {{"code_level": [], "infrastructure": [], "configuration": []}}
- optimization_plan: {{"optimizations": [{{"type": str, "description": str, "impact": str, "implementation": []}}]}}
- optimization_results: {{"optimizations_applied": [], "metrics_before": {{}}, "metrics_after": {{}}, "improvement_percent": float}}
- validation: {{improvements_validated: bool, no_regressions: bool, metrics_improved: bool}}
"""

        try:
            # Call LLM for optimization analysis
            logger.debug("Calling LLM for performance optimization analysis...")
            llm_response = await self.call_llm(system_prompt, user_message, max_tokens=2048)

            # Extract optimization results
            performance_analysis = llm_response.get("performance_analysis", {})
            optimization_opportunities = llm_response.get("optimization_opportunities", {})
            optimization_plan = llm_response.get("optimization_plan", {})
            optimization_results = llm_response.get("optimization_results", {})
            validation = llm_response.get("validation", {})

            outputs = {
                "performance_analysis": performance_analysis,
                "optimization_opportunities": optimization_opportunities,
                "optimization_plan": optimization_plan,
                "optimization_results": optimization_results,
                "validation": validation,
            }

            # Update manifest
            manifests_dir = workspace_root / ".spectra" / "manifests"
            manifests_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = manifests_dir / "optimise-manifest.yaml"

            manifest = Manifest(activity="optimise")
            manifest.start()
            self.update_manifest(manifest, outputs)

            # Record quality gates
            manifest.record_quality_gate("performance_analyzed", bool(performance_analysis))
            manifest.record_quality_gate("optimization_opportunities_identified",
                                       len(optimization_opportunities.get("code_level", [])) > 0 or
                                       len(optimization_opportunities.get("infrastructure", [])) > 0)
            manifest.record_quality_gate("optimization_plan_created", bool(optimization_plan))
            manifest.record_quality_gate("optimizations_applied",
                                       len(optimization_results.get("optimizations_applied", [])) > 0)
            manifest.record_quality_gate("improvements_validated", validation.get("improvements_validated", False))
            manifest.record_quality_gate("no_regressions", validation.get("no_regressions", False))
            manifest.record_quality_gate("metrics_improved", validation.get("metrics_improved", False))

            manifest.complete(success=validation.get("metrics_improved", False))
            manifest.save(manifest_path)

            logger.info("Optimization complete")
            logger.info(f"Manifest saved to: {manifest_path}")

            # Record history
            history_path = workspace_root / ".spectra" / "history" / "optimise-history.yaml"
            history_path.parent.mkdir(parents=True, exist_ok=True)
            self.record_history(
                history=history,
                decision=llm_response,
                outcome="success" if validation.get("metrics_improved", False) else "partial",
                result=ActivityResult(
                    activity_name="optimise",
                    success=validation.get("metrics_improved", False),
                    outputs=outputs,
                    errors=[],
                ),
                context=activity_context,
            )
            history.save(history_path)
            logger.debug(f"History saved to: {history_path}")

            return ActivityResult(
                activity_name="optimise",
                success=validation.get("metrics_improved", False),
                outputs=outputs,
                errors=[],
            )

        except Exception as e:
            logger.error(f"Optimise activity failed: {e}", exc_info=True)
            return ActivityResult(
                activity_name="optimise",
                success=False,
                outputs={},
                errors=[str(e)],
            )

    def format_prompt(self, context: Dict, history: Optional[list] = None) -> str:
        """
        Format system prompt for optimise activity.

        Args:
            context: Context dictionary
            history: Optional history entries

        Returns:
            Formatted system prompt
        """
        prompt_parts = [
            "You are a SPECTRA Performance Engineer - an expert in performance optimization.",
            "",
            "YOUR MISSION:",
            "Analyze performance and optimize services following SPECTRA optimization standards.",
            "",
            "SPECTRA OPTIMIZATION STANDARDS:",
            "- Data-driven: Optimize based on metrics, not assumptions",
            "- Autonomous learning: Learn from historical data",
            "- No regressions: Optimize without breaking functionality",
            "- Measurable impact: Quantify improvements",
            "",
            "OPTIMIZATION PRINCIPLES:",
            "- Measure first: Understand baseline metrics",
            "- Identify bottlenecks: Focus on highest-impact optimizations",
            "- Iterate: Optimize incrementally, measure impact",
            "- Validate: Ensure optimizations don't introduce regressions",
            "",
            "OPTIMIZATION AREAS:",
            "- Code-level: Algorithm improvements, caching, query optimization",
            "- Infrastructure: Resource allocation, scaling, networking",
            "- Configuration: Environment variables, feature flags, timeouts",
            "",
        ]

        if context.get("specification_summary"):
            prompt_parts.append(f"SPECIFICATION SUMMARY:\n{context['specification_summary']}\n")
        if context.get("manifest_summary"):
            prompt_parts.append(f"MANIFEST SUMMARY:\n{context['manifest_summary']}\n")
        if context.get("monitoring_metrics"):
            prompt_parts.append(f"MONITORING METRICS:\n{json.dumps(context['monitoring_metrics'], indent=2)}\n")

        if history:
            prompt_parts.extend([
                "",
                "RECENT HISTORY:",
                json.dumps(history[-2:], indent=2),
            ])

        prompt_parts.extend([
            "",
            "OUTPUT FORMAT:",
            "Respond in JSON format with performance_analysis, optimization_opportunities, optimization_plan, optimization_results, and validation fields.",
        ])

        return "\n".join(prompt_parts)
