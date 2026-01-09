"""
Engage Activity - Client registration and directory setup

SPECTRA-Grade client engagement activity.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

from ..activity import Activity, ActivityContext, ActivityResult
from ..state import ActivityHistory, Manifest

logger = logging.getLogger(__name__)


class Engage(Activity):
    """
    Engage - Client registration and directory setup activity.

    Uses LLM to determine client requirements and set up engagement structure.
    """

    async def execute(self, context: ActivityContext) -> ActivityResult:
        """
        Execute engage activity.

        Args:
            context: Activity context

        Returns:
            ActivityResult with engagement outputs
        """
        logger.info(f"Executing Engage activity for: {context.user_input}")

        workspace_root = self.context_builder.workspace_root

        # Build context for engagement
        activity_context = self.context_builder.build_activity_context(
            activity_name="engage",
            service_name=context.service_name,
            specification=context.specification,
            manifest=context.manifest,
        )

        # Use semantic filtering to get most relevant playbooks
        filtered_playbooks = await self.playbook_registry.filter_relevant_playbooks(
            activity_name="engage",
            task=context.user_input,
            llm_client=self.llm_client,
            max_playbooks=5,
        )

        # Get playbook context with filtered playbooks
        playbook_context = self.playbook_registry.get_playbook_context_for_llm(
            activity_name="engage",
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

        # Format prompt for client engagement
        system_prompt = self.format_prompt(context=activity_context, history=history_summary)

        user_message = f"""
Engage with client and set up engagement structure for: {context.user_input}

ENGAGEMENT TASKS:
1. Client Information Extraction:
   - Extract client name, contact details
   - Identify engagement type (project, service, support)
   - Determine engagement scope

2. Directory Structure Setup:
   - Determine appropriate directory structure for engagement
   - Create client directory if needed
   - Set up engagement subdirectories

3. Initial Configuration:
   - Create initial configuration files
   - Set up environment-specific settings
   - Configure engagement metadata

4. Validation:
   - Validate client information completeness
   - Verify directory structure created
   - Confirm configuration initialized

AVAILABLE PLAYBOOKS:
{json.dumps(playbook_context.get("available_playbooks", []), indent=2)}

Respond in JSON format with:
- client_info: {{"name": str, "contact": str, "engagement_type": str, "scope": str}}
- directory_structure: {{"client_dir": str, "engagement_dir": str, "subdirectories": []}}
- configuration: {{"config_files": [], "env_settings": {{{{}}}}, "metadata": {{{{}}}}}}
- validation: {{"client_validated": bool, "directory_created": bool, "config_initialized": bool}}
"""

        try:
            # Call LLM for engagement
            logger.debug("Calling LLM for client engagement analysis...")
            llm_response = await self.call_llm(system_prompt, user_message, max_tokens=2048)

            # Extract engagement results
            client_info = llm_response.get("client_info", {})
            directory_structure = llm_response.get("directory_structure", {})
            configuration = llm_response.get("configuration", {})
            validation = llm_response.get("validation", {})

            # Create directory structure (if client_dir specified)
            client_dir_path = None
            engagement_dir_path = None
            if directory_structure.get("client_dir"):
                client_dir = directory_structure["client_dir"]
                client_dir_path = workspace_root / "Engagement" / client_dir
                client_dir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created client directory: {client_dir_path}")

            if directory_structure.get("engagement_dir") and client_dir_path:
                engagement_dir = directory_structure["engagement_dir"]
                engagement_dir_path = client_dir_path / engagement_dir
                engagement_dir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created engagement directory: {engagement_dir_path}")

                # Create subdirectories
                for subdir in directory_structure.get("subdirectories", []):
                    subdir_path = engagement_dir_path / subdir
                    subdir_path.mkdir(parents=True, exist_ok=True)
                    logger.debug(f"Created subdirectory: {subdir_path}")

            outputs = {
                "client_info": client_info,
                "directory_structure": {
                    **directory_structure,
                    "client_dir_path": str(client_dir_path) if client_dir_path else None,
                    "engagement_dir_path": str(engagement_dir_path) if engagement_dir_path else None,
                },
                "configuration": configuration,
                "validation": validation,
            }

            # Update manifest
            manifests_dir = workspace_root / ".spectra" / "manifests"
            manifests_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = manifests_dir / "engage-manifest.yaml"

            manifest = Manifest(activity="engage")
            manifest.start()
            self.update_manifest(manifest, outputs)

            # Record quality gates
            manifest.record_quality_gate("client_info_extracted", bool(client_info.get("name")))
            manifest.record_quality_gate("directory_structure_created", bool(client_dir_path))
            manifest.record_quality_gate("configuration_initialized", bool(configuration.get("config_files")))
            manifest.record_quality_gate("client_validated", validation.get("client_validated", False))

            manifest.complete(success=True)
            manifest.save(manifest_path)

            logger.info("Engagement complete")
            logger.info(f"Manifest saved to: {manifest_path}")

            # Record history
            history_path = workspace_root / ".spectra" / "history" / "engage-history.yaml"
            history_path.parent.mkdir(parents=True, exist_ok=True)
            self.record_history(
                history=history,
                decision=llm_response,
                outcome="success",
                result=ActivityResult(
                    activity_name="engage",
                    success=True,
                    outputs=outputs,
                    errors=[],
                ),
                context=activity_context,
            )
            history.save(history_path)
            logger.debug(f"History saved to: {history_path}")

            return ActivityResult(
                activity_name="engage",
                success=True,
                outputs=outputs,
                errors=[],
            )

        except Exception as e:
            logger.error(f"Engage activity failed: {e}", exc_info=True)
            return ActivityResult(
                activity_name="engage",
                success=False,
                outputs={},
                errors=[str(e)],
            )

    def format_prompt(self, context: Dict, history: Optional[list] = None) -> str:
        """
        Format system prompt for engage activity.

        Args:
            context: Context dictionary
            history: Optional history entries

        Returns:
            Formatted system prompt
        """
        prompt_parts = [
            "You are a SPECTRA Engagement Specialist - an expert in client registration and directory setup.",
            "",
            "YOUR MISSION:",
            "Engage with clients, extract information, and set up proper engagement structure.",
            "",
            "ENGAGEMENT PRINCIPLES:",
            "- Extract comprehensive client information",
            "- Create appropriate directory structure (Engagement/{client}/{engagement}/)",
            "- Initialize configuration files and metadata",
            "- Validate all information before proceeding",
            "",
            "DIRECTORY STRUCTURE:",
            "- Client directory: Engagement/{client_name}/",
            "- Engagement directory: Engagement/{client_name}/{engagement_name}/",
            "- Subdirectories: docs/, config/, artifacts/, etc.",
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
            "Respond in JSON format with client_info, directory_structure, configuration, and validation fields.",
        ])

        return "\n".join(prompt_parts)
