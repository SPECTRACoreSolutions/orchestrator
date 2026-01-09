"""
Finalise Activity - Execute Finalize Protocol V2

SPECTRA-Grade finalization activity that executes the 9-step protocol.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..activity import Activity, ActivityContext, ActivityResult
from ..state import ActivityHistory, Manifest

logger = logging.getLogger(__name__)


class Finalise(Activity):
    """
    Finalise - Finalization activity that executes Finalize Protocol V2.

    Executes the 9-step protocol:
    1. Verify All TODOs Complete
    2. Create Session Summary (worklog)
    3. Update Registry
    4. Organize Documentation
    5. Extract Lessons Learned
    6. Create Commit Guide
    7. Provide Next Steps
    8. Save Chat to SpecStory (manual trigger - note in output)
    9. Declare Status
    """

    async def execute(self, context: ActivityContext) -> ActivityResult:
        """
        Execute finalise activity.

        Args:
            context: Activity context

        Returns:
            ActivityResult with finalization outputs
        """
        logger.info(f"Executing Finalise activity for: {context.user_input}")

        workspace_root = self.context_builder.workspace_root

        # Build context for finalization
        activity_context = self.context_builder.build_activity_context(
            activity_name="finalise",
            service_name=context.service_name,
            specification=context.specification,
            manifest=context.manifest,
        )

        # Get playbook metadata for finalization
        # Use semantic filtering to get most relevant playbooks
        filtered_playbooks = await self.playbook_registry.filter_relevant_playbooks(
            activity_name="finalise",
            task=context.user_input,
            llm_client=self.llm_client,
            max_playbooks=5,
        )

        # Get playbook context with filtered playbooks
        playbook_context = self.playbook_registry.get_playbook_context_for_llm(
            activity_name="finalise",
            playbooks=filtered_playbooks,
        )

        # Load history
        history = self.load_history()
        recent_history = history.get_recent(5)  # More history for finalization
        history_summary = []
        for entry in recent_history:
            entry_dict = entry.__dict__
            summary = {
                "decision": str(entry_dict.get("decision", ""))[:200] if entry_dict.get("decision") else None,
                "outcome": entry_dict.get("outcome"),
                "timestamp": entry_dict.get("timestamp"),
            }
            history_summary.append(summary)

        # Format prompt for finalization (9-step protocol)
        system_prompt = self.format_prompt(context=activity_context, history=history_summary)

        user_message = f"""
Execute Finalize Protocol V2 for: {context.user_input}

FINALIZE PROTOCOL V2 - 9 STEPS:

1. VERIFY ALL TODOs COMPLETE:
   - Check all open TODOs are done
   - Mark any remaining as cancelled with explanation
   - No loose ends

2. CREATE SESSION SUMMARY (WORKLOG):
   - Generate comprehensive worklog entry
   - Include: what was done, decisions made, files changed
   - Enhanced with 7 SPECTRA-grade features:
     - Seven-dimensional scoring
     - Time tracking data
     - Problems solved mapping
     - Cosmic index tags
     - Impact quantification
     - Registry updates
     - Related sessions
   - Location: Core/memory/worklog/YYYY-MM-DD-description.md

3. UPDATE REGISTRY:
   - Update VERSION-REGISTRY.json if packages changed
   - Update any relevant trackers (ideas.json, etc.)
   - Ensure all artifacts are registered

4. ORGANIZE DOCUMENTATION:
   - List all docs created this session
   - Ensure they're in correct locations
   - Create index/table of contents if needed

5. EXTRACT LESSONS LEARNED:
   - Identify mistakes caught and corrected
   - Extract principles and rules from session
   - Document in Core/memory/lessons/ by category:
     - technical/ - Dependencies, builds, tools, gotchas
     - architecture/ - Design decisions & patterns
     - process/ - Workflow & methodology improvements
     - platform/ - Fabric, GitHub, Azure specifics
   - Update LESSONS-INDEX.md with new lessons
   - Cross-reference with worklog entry

6. CREATE COMMIT GUIDE:
   - List what needs committing
   - Which repositories
   - Suggested commit messages
   - Testing steps if needed

7. PROVIDE NEXT STEPS:
   - What to do immediately
   - Short-term next steps
   - Long-term roadmap
   - Clear actionable items

8. SAVE CHAT TO SPECSTORY:
   - Note: Manual trigger required (Ctrl+Shift+P → SpecStory: Save AI Chat History)
   - Verify file appears in .spectra/.specstory/history/
   - This preserves conversation context alongside worklog

9. DECLARE STATUS:
   - Session complete? ✅
   - Any blockers? List them
   - Ready for next phase? Confirm
   - Final state summary

AVAILABLE PLAYBOOKS:
{json.dumps(playbook_context.get("available_playbooks", []), indent=2)}

Respond in JSON format with:
- step1_todos: {{"completed": [], "cancelled": [], "summary": str}}
- step2_worklog: {{"title": str, "path": str, "content_summary": str, "seven_features": {{}}}}
- step3_registry_updates: {{"files_updated": [], "changes": []}}
- step4_documentation: {{"docs_created": [], "locations": [], "index_created": bool}}
- step5_lessons: {{"lessons": [{{"category": str, "title": str, "path": str, "principle": str}}], "index_updated": bool}}
- step6_commit_guide: {{"repositories": [], "commit_messages": [], "testing_steps": []}}
- step7_next_steps: {{"immediate": [], "short_term": [], "long_term": []}}
- step8_specstory: {{"manual_trigger_required": bool, "note": str}}
- step9_status: {{"session_complete": bool, "blockers": [], "ready_for_next_phase": bool, "final_summary": str}}
"""

        try:
            # Call LLM for finalization protocol execution
            logger.debug("Calling LLM for Finalize Protocol V2 execution...")
            llm_response = await self.call_llm(system_prompt, user_message, max_tokens=4096)

            # Extract protocol results
            step1_todos = llm_response.get("step1_todos", {})
            step2_worklog = llm_response.get("step2_worklog", {})
            step3_registry_updates = llm_response.get("step3_registry_updates", {})
            step4_documentation = llm_response.get("step4_documentation", {})
            step5_lessons = llm_response.get("step5_lessons", {})
            step6_commit_guide = llm_response.get("step6_commit_guide", {})
            step7_next_steps = llm_response.get("step7_next_steps", {})
            step8_specstory = llm_response.get("step8_specstory", {})
            step9_status = llm_response.get("step9_status", {})

            # Create worklog entry (if path provided)
            worklog_path = None
            if step2_worklog.get("path"):
                worklog_path = workspace_root / step2_worklog["path"]
                worklog_path.parent.mkdir(parents=True, exist_ok=True)
                # Note: Actual worklog content generation would be done here
                # For now, create placeholder file
                worklog_path.write_text(
                    f"# {step2_worklog.get('title', 'Session Summary')}\n\n"
                    f"{step2_worklog.get('content_summary', 'Worklog content to be generated.')}\n",
                    encoding="utf-8"
                )
                logger.info(f"Created worklog entry: {worklog_path}")

            outputs = {
                "step1_todos": step1_todos,
                "step2_worklog": {**step2_worklog, "path": str(worklog_path) if worklog_path else None},
                "step3_registry_updates": step3_registry_updates,
                "step4_documentation": step4_documentation,
                "step5_lessons": step5_lessons,
                "step6_commit_guide": step6_commit_guide,
                "step7_next_steps": step7_next_steps,
                "step8_specstory": step8_specstory,
                "step9_status": step9_status,
            }

            # Update manifest
            manifests_dir = workspace_root / ".spectra" / "manifests"
            manifests_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = manifests_dir / "finalise-manifest.yaml"

            manifest = Manifest(activity="finalise")
            manifest.start()
            self.update_manifest(manifest, outputs)

            # Record quality gates
            manifest.record_quality_gate("step1_todos_verified", len(step1_todos.get("completed", [])) > 0)
            manifest.record_quality_gate("step2_worklog_created", worklog_path is not None)
            manifest.record_quality_gate("step3_registry_updated", len(step3_registry_updates.get("files_updated", [])) > 0)
            manifest.record_quality_gate("step4_documentation_organized", len(step4_documentation.get("docs_created", [])) > 0)
            manifest.record_quality_gate("step5_lessons_extracted", len(step5_lessons.get("lessons", [])) > 0)
            manifest.record_quality_gate("step6_commit_guide_created", len(step6_commit_guide.get("repositories", [])) > 0)
            manifest.record_quality_gate("step7_next_steps_provided", len(step7_next_steps.get("immediate", [])) > 0)
            manifest.record_quality_gate("step8_specstory_note", step8_specstory.get("manual_trigger_required", False))
            manifest.record_quality_gate("step9_status_declared", step9_status.get("session_complete", False))

            manifest.complete(success=step9_status.get("session_complete", False))
            manifest.save(manifest_path)

            logger.info("Finalization complete")
            logger.info(f"Manifest saved to: {manifest_path}")

            # Record history
            history_path = workspace_root / ".spectra" / "history" / "finalise-history.yaml"
            history_path.parent.mkdir(parents=True, exist_ok=True)
            self.record_history(
                history=history,
                decision=llm_response,
                outcome="success" if step9_status.get("session_complete", False) else "partial",
                result=ActivityResult(
                    activity_name="finalise",
                    success=step9_status.get("session_complete", False),
                    outputs=outputs,
                    errors=[],
                ),
                context=activity_context,
            )
            history.save(history_path)
            logger.debug(f"History saved to: {history_path}")

            return ActivityResult(
                activity_name="finalise",
                success=step9_status.get("session_complete", False),
                outputs=outputs,
                errors=[],
            )

        except Exception as e:
            logger.error(f"Finalise activity failed: {e}", exc_info=True)
            return ActivityResult(
                activity_name="finalise",
                success=False,
                outputs={},
                errors=[str(e)],
            )

    def format_prompt(self, context: Dict, history: Optional[list] = None) -> str:
        """
        Format system prompt for finalise activity.

        Args:
            context: Context dictionary
            history: Optional history entries

        Returns:
            Formatted system prompt
        """
        prompt_parts = [
            "You are a SPECTRA Finalization Specialist - an expert in executing Finalize Protocol V2.",
            "",
            "YOUR MISSION:",
            "Execute the 9-step Finalize Protocol V2 following SPECTRA standards.",
            "",
            "FINALIZE PROTOCOL V2 - OVERVIEW:",
            "- 9 systematic steps for complete session finalization",
            "- Comprehensive worklog with 7 SPECTRA-grade features",
            "- Lessons extraction for institutional memory",
            "- Registry updates for artifact tracking",
            "- Commit guide for version control",
            "- Next steps for continued progress",
            "",
            "WORKLOG STANDARDS:",
            "- Location: Core/memory/worklog/YYYY-MM-DD-description.md",
            "- Enhanced with 7 features: scoring, time tracking, problems solved, cosmic tags, impact, registry, related sessions",
            "- Comprehensive summary of work done",
            "",
            "LESSONS EXTRACTION:",
            "- Category: technical, architecture, process, platform",
            "- Location: Core/memory/lessons/{category}/",
            "- Update LESSONS-INDEX.md",
            "- Cross-reference with worklog",
            "",
            "REGISTRY UPDATES:",
            "- VERSION-REGISTRY.json for packages",
            "- ideas.json for ideas queue",
            "- service-catalog.yaml for services",
            "- All artifacts registered",
            "",
        ]

        if context.get("specification_summary"):
            prompt_parts.append(f"SPECIFICATION SUMMARY:\n{context['specification_summary']}\n")
        if context.get("manifest_summary"):
            prompt_parts.append(f"MANIFEST SUMMARY:\n{context['manifest_summary']}\n")

        if history:
            prompt_parts.extend([
                "",
                "RECENT HISTORY (last 5 entries for comprehensive context):",
                json.dumps(history[-5:], indent=2),
            ])

        prompt_parts.extend([
            "",
            "OUTPUT FORMAT:",
            "Respond in JSON format with step1_todos through step9_status fields, covering all 9 steps of the protocol.",
        ])

        return "\n".join(prompt_parts)
