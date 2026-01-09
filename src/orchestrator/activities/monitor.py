"""
Monitor Activity - Health monitoring and alerting

SPECTRA-Grade monitoring activity.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

from ..activity import Activity, ActivityContext, ActivityResult
from ..state import ActivityHistory, Manifest

logger = logging.getLogger(__name__)


class Monitor(Activity):
    """
    Monitor - Health monitoring and alerting activity.

    Uses LLM and playbooks to set up monitoring dashboards and alerts.
    """

    async def execute(self, context: ActivityContext) -> ActivityResult:
        """
        Execute monitor activity.

        Args:
            context: Activity context

        Returns:
            ActivityResult with monitoring outputs
        """
        logger.info(f"Executing Monitor activity for: {context.user_input}")

        workspace_root = self.context_builder.workspace_root

        # Build context for monitoring
        activity_context = self.context_builder.build_activity_context(
            activity_name="monitor",
            service_name=context.service_name,
            specification=context.specification,
            manifest=context.manifest,
        )

        # Get playbook metadata for monitoring
        # Use semantic filtering to get most relevant playbooks
        filtered_playbooks = await self.playbook_registry.filter_relevant_playbooks(
            activity_name="monitor",
            task=context.user_input,
            llm_client=self.llm_client,
            max_playbooks=5,
        )

        # Get playbook context with filtered playbooks
        playbook_context = self.playbook_registry.get_playbook_context_for_llm(
            activity_name="monitor",
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

        # Format prompt for monitoring
        system_prompt = self.format_prompt(context=activity_context, history=history_summary)

        user_message = f"""
Set up monitoring and alerting for: {context.user_input}

MONITORING TASKS:
1. Monitoring Requirements Analysis:
   - Determine required metrics (latency, errors, throughput, etc.)
   - Identify alerting thresholds
   - Specify dashboard requirements

2. Dashboard Provisioning:
   - Create monitoring dashboards (Grafana, Railway, etc.)
   - Configure metric collection
   - Set up visualization panels

3. Alert Configuration:
   - Configure alert thresholds
   - Set up alerting channels (Discord, email, etc.)
   - Configure escalation policies

4. Validation:
   - Verify monitoring active
   - Confirm dashboards accessible
   - Validate alerts working

AVAILABLE PLAYBOOKS:
{json.dumps(playbook_context.get("available_playbooks", []), indent=2)}

SPECTRA MONITORING STANDARDS:
- Dashboard-as-code: All dashboards defined programmatically
- Comprehensive metrics: Latency, errors, throughput, resource usage
- Proactive alerting: Alert before issues impact users
- Observability: Full visibility into system behavior

Respond in JSON format with:
- monitoring_requirements: {{"metrics": [], "thresholds": {{}}, "dashboards": []}}
- dashboard_config: {{"dashboards": [{{"name": str, "panels": [], "data_sources": []}}]}}
- alert_config: {{"alerts": [{{"name": str, "threshold": str, "channel": str, "escalation": []}}]}}
- validation: {{monitoring_active: bool, dashboards_accessible: bool, alerts_working: bool}}
"""

        try:
            # Call LLM for monitoring setup
            logger.debug("Calling LLM for monitoring setup analysis...")
            llm_response = await self.call_llm(system_prompt, user_message, max_tokens=2048)

            # Extract monitoring results
            monitoring_requirements = llm_response.get("monitoring_requirements", {})
            dashboard_config = llm_response.get("dashboard_config", {})
            alert_config = llm_response.get("alert_config", {})
            validation = llm_response.get("validation", {})

            outputs = {
                "monitoring_requirements": monitoring_requirements,
                "dashboard_config": dashboard_config,
                "alert_config": alert_config,
                "validation": validation,
            }

            # Update manifest
            manifests_dir = workspace_root / ".spectra" / "manifests"
            manifests_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = manifests_dir / "monitor-manifest.yaml"

            manifest = Manifest(activity="monitor")
            manifest.start()
            self.update_manifest(manifest, outputs)

            # Record quality gates
            manifest.record_quality_gate("monitoring_requirements_analyzed", bool(monitoring_requirements))
            manifest.record_quality_gate("dashboards_configured", len(dashboard_config.get("dashboards", [])) > 0)
            manifest.record_quality_gate("alerts_configured", len(alert_config.get("alerts", [])) > 0)
            manifest.record_quality_gate("monitoring_active", validation.get("monitoring_active", False))
            manifest.record_quality_gate("dashboards_accessible", validation.get("dashboards_accessible", False))
            manifest.record_quality_gate("alerts_working", validation.get("alerts_working", False))

            manifest.complete(success=validation.get("monitoring_active", False))
            manifest.save(manifest_path)

            logger.info("Monitoring setup complete")
            logger.info(f"Manifest saved to: {manifest_path}")

            # Record history
            history_path = workspace_root / ".spectra" / "history" / "monitor-history.yaml"
            history_path.parent.mkdir(parents=True, exist_ok=True)
            self.record_history(
                history=history,
                decision=llm_response,
                outcome="success",
                result=ActivityResult(
                    activity_name="monitor",
                    success=True,
                    outputs=outputs,
                    errors=[],
                ),
                context=activity_context,
            )
            history.save(history_path)
            logger.debug(f"History saved to: {history_path}")

            return ActivityResult(
                activity_name="monitor",
                success=True,
                outputs=outputs,
                errors=[],
            )

        except Exception as e:
            logger.error(f"Monitor activity failed: {e}", exc_info=True)
            return ActivityResult(
                activity_name="monitor",
                success=False,
                outputs={},
                errors=[str(e)],
            )

    def format_prompt(self, context: Dict, history: Optional[list] = None) -> str:
        """
        Format system prompt for monitor activity.

        Args:
            context: Context dictionary
            history: Optional history entries

        Returns:
            Formatted system prompt
        """
        prompt_parts = [
            "You are a SPECTRA Monitoring Engineer - an expert in observability and alerting.",
            "",
            "YOUR MISSION:",
            "Set up comprehensive monitoring and alerting following SPECTRA observability standards.",
            "",
            "SPECTRA MONITORING STANDARDS:",
            "- Dashboard-as-code: All dashboards defined programmatically",
            "- Comprehensive metrics: Latency, errors, throughput, resource usage",
            "- Proactive alerting: Alert before issues impact users",
            "- Observability: Full visibility into system behavior",
            "",
            "MONITORING PRINCIPLES:",
            "- Four Golden Signals: Latency, Traffic, Errors, Saturation",
            "- SLI/SLO-based alerting: Alert on SLO violations, not raw metrics",
            "- Autonomous threshold learning: Adapt thresholds based on historical data",
            "- Clear escalation paths: Know who to alert and when",
            "",
            "DASHBOARD CONFIGURATION:",
            "- Grafana dashboards (if available)",
            "- Railway metrics dashboard",
            "- Custom dashboards as needed",
            "",
            "ALERT CONFIGURATION:",
            "- Discord notifications (primary)",
            "- Email alerts (critical only)",
            "- Escalation policies",
            "",
        ]

        if context.get("specification_summary"):
            prompt_parts.append(f"SPECIFICATION SUMMARY:\n{context['specification_summary']}\n")
        if context.get("manifest_summary"):
            prompt_parts.append(f"MANIFEST SUMMARY:\n{context['manifest_summary']}\n")
        if context.get("deployment_results"):
            prompt_parts.append(f"DEPLOYMENT RESULTS:\n{json.dumps(context['deployment_results'], indent=2)}\n")

        if history:
            prompt_parts.extend([
                "",
                "RECENT HISTORY:",
                json.dumps(history[-2:], indent=2),
            ])

        prompt_parts.extend([
            "",
            "OUTPUT FORMAT:",
            "Respond in JSON format with monitoring_requirements, dashboard_config, alert_config, and validation fields.",
        ])

        return "\n".join(prompt_parts)
