"""
Discover Activity - Comprehensive problem understanding and solution validation

SPECTRA-Grade discovery that deeply understands:
- Problem (what, who, impact, root cause)
- Current state (what exists, pain points, gaps)
- Desired state (vision, success criteria, goals)
- Stakeholders (users, decision-makers, beneficiaries)
- Constraints (technical, business, time, budget, compliance)
- Requirements (functional, non-functional)
- Risks (technical, business, implementation)
- Alternatives (other options, why this solution)
- Solution validation (does it solve the problem?)
- Next steps (pipeline progression)

Note: Maturity assessment is handled by Assess activity.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Optional

from ..activity import Activity, ActivityContext, ActivityResult
from ..registry import RegistryCheck
from ..state import ActivityHistory, Manifest

logger = logging.getLogger(__name__)


class Discover(Activity):
    """
    Discover - Problem/idea validation activity.

    Uses LLM to analyse user input and discover:
    - Service name (mononymic, validated)
    - Problem statement
    - Idea validation

    Note: Maturity assessment will move to Assess activity (planned).
    """

    async def execute(self, context: ActivityContext) -> ActivityResult:
        """
        Execute discover activity with comprehensive discovery analysis.

        Args:
            context: Activity context

        Returns:
            ActivityResult with discovery outputs
        """
        logger.info(f"Executing Discover activity for: {context.user_input}")

        workspace_root = self.context_builder.workspace_root

        # STEP 1: Registry Check (always run first - safety)
        registry_check = RegistryCheck(workspace_root)
        service_exists, service_info = registry_check.check_service(context.service_name or "unknown")

        if service_exists and registry_check.should_block(service_info):
            logger.error(f"Service '{context.service_name}' already exists and is healthy - BLOCKED")
            return ActivityResult(
                activity_name="discover",
                success=False,
                outputs={
                    "service_name": context.service_name,
                    "registry_check": {
                        "service_exists": True,
                        "action": "blocked",
                        "reason": "service already healthy - zero tolerance for duplicates",
                        "service_info": service_info,
                    },
                },
                errors=[f"Service '{context.service_name}' already exists and is healthy"],
            )

        # Load/build context (optimized - summarized)
        activity_context = self.context_builder.build_activity_context(
            activity_name="discover",
            service_name=context.service_name,
            specification=context.specification,
            manifest=context.manifest,
            tools=context.tools,
        )

        # Load history
        history = self.load_history()

        # Format comprehensive prompt (with strict size limits)
        recent_history = history.get_recent(2)  # Only last 2 entries
        # Summarize history entries to prevent huge prompts
        history_summary = []
        for entry in recent_history:
            entry_dict = entry.__dict__
            # Only include key fields, limit size
            summary = {
                "decision": str(entry_dict.get("decision", ""))[:200] if entry_dict.get("decision") else None,
                "outcome": entry_dict.get("outcome"),
                "timestamp": entry_dict.get("timestamp"),
            }
            history_summary.append(summary)

        system_prompt = self.format_prompt(
            context=activity_context,
            history=history_summary,
        )

        # Enforce strict prompt size limit
        max_prompt_chars = 4000  # Strict limit
        if len(system_prompt) > max_prompt_chars:
            logger.warning(f"System prompt too long ({len(system_prompt)} chars), truncating to {max_prompt_chars}...")
            system_prompt = system_prompt[:max_prompt_chars] + "\n\n[Context truncated for length - use summaries]"

        # User message with comprehensive discovery request
        user_message = f"""
Conduct comprehensive discovery on: {context.user_input}

IMPORTANT - SERVICE NAME EXTRACTION:
- Extract the SPECIFIC service name, not abstract concepts
- If user mentions "X service", extract "X" as the service name
- Example: "monitoring service" → extract "monitoring" (NOT "observability")
- Example: "logging service" → extract "logging" (NOT "observability")
- Abstract concepts (like "observability") are umbrella terms, not service names
- Prefer concrete service names: monitoring, logging, notifications, etc.

Explore all discovery dimensions:
1. Problem: What problem? Who has it? Impact? Root cause?
2. Current State: What exists? Pain points? Gaps?
3. Desired State: Vision? Success criteria? Goals?
4. Stakeholders: Users? Decision-makers? Beneficiaries?
5. Constraints: Technical? Business? Time? Budget? Compliance?
6. Requirements: Functional? Non-functional?
7. Risks: Technical? Business? Implementation?
8. Alternatives: Other options? Why this solution?
9. Validation: Does solution solve problem? How?
10. Next Steps: What happens next?

Respond in comprehensive JSON format (see specification for structure).
"""

        try:
            # Call LLM with appropriate max_tokens for comprehensive discovery
            logger.debug("Calling LLM for comprehensive discovery analysis...")
            prompt_size_estimate = len(system_prompt) + len(user_message)
            logger.debug(f"Prompt size estimate: {prompt_size_estimate} chars")

            # Calculate safe max_tokens (model context ~8k tokens, 1 token ≈ 4 chars)
            # Reserve space for prompt, use remaining for response
            model_context_chars = 8000 * 4  # ~32k chars
            available_for_response = max(1000, (model_context_chars - prompt_size_estimate) // 4)

            # Cap at reasonable maximum
            max_response_tokens = min(2048, available_for_response)
            logger.debug(f"Using max_tokens: {max_response_tokens}")

            llm_response = await self.call_llm(system_prompt, user_message, max_tokens=max_response_tokens)

            # Extract and validate service name
            service_name_raw = llm_response.get("service_name", context.service_name or "unknown")
            service_name = self._normalize_service_name(service_name_raw)

            # Validate service name (but be lenient - normalize instead of rejecting)
            if not self._validate_service_name(service_name):
                # Try to normalize to a valid name instead of failing
                logger.warning(f"Service name '{service_name}' doesn't meet strict validation, normalizing...")
                # Extract key words and create shorter name
                parts = service_name.split('-')
                # Keep first 2-3 meaningful parts (skip common words like 'service', 'management')
                meaningful_parts = [p for p in parts if p not in ['service', 'management', 'client', 'catalog']]
                if len(meaningful_parts) >= 2:
                    service_name = '-'.join(meaningful_parts[:2])  # Keep first 2 meaningful parts
                elif len(meaningful_parts) == 1:
                    service_name = meaningful_parts[0]
                else:
                    # Fallback: use first part only
                    service_name = parts[0] if parts else "service"

                # Re-validate after normalization
                if not self._validate_service_name(service_name):
                    logger.warning(f"Could not normalize service name, using fallback: service-catalog")
                    service_name = "service-catalog"  # Safe fallback

            # Extract comprehensive discovery results
            problem = llm_response.get("problem", {})
            current_state = llm_response.get("current_state", {})
            desired_state = llm_response.get("desired_state", {})
            stakeholders = llm_response.get("stakeholders", {})
            constraints = llm_response.get("constraints", {})
            requirements = llm_response.get("requirements", {})
            risks = llm_response.get("risks", {})
            alternatives = llm_response.get("alternatives", {})
            idea = llm_response.get("idea", {})
            # Normalize idea name as well
            if idea.get("name"):
                idea["name"] = self._normalize_service_name(idea["name"])
            validation = llm_response.get("validation", {})
            recommended_tools = llm_response.get("recommended_tools", [])
            next_steps = llm_response.get("next_steps", "")

            # Build comprehensive outputs
            outputs = {
                "service_name": service_name,
                "problem": problem,
                "current_state": current_state,
                "desired_state": desired_state,
                "stakeholders": stakeholders,
                "constraints": constraints,
                "requirements": requirements,
                "risks": risks,
                "alternatives": alternatives,
                "idea": idea,
                "validation": validation,
                "recommended_tools": recommended_tools,
                "next_steps": next_steps,
                "registry_check": {
                    "service_exists": service_exists,
                    "action": "blocked" if (service_exists and registry_check.should_block(service_info)) else ("redeploy" if service_exists else "deploy_new"),
                    "service_info": service_info,
                },
            }

            # Update manifest
            workspace_root = self.context_builder.workspace_root
            manifests_dir = workspace_root / ".spectra" / "manifests"
            manifests_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = manifests_dir / "discover-manifest.yaml"

            manifest = Manifest(activity="discover")
            manifest.start()
            self.update_manifest(manifest, outputs)

            # Record comprehensive quality gates
            manifest.record_quality_gate("problem_identified", bool(problem.get("statement")))
            manifest.record_quality_gate("idea_generated", bool(idea))
            manifest.record_quality_gate("problem_idea_mapped", bool(validation.get("problem_solved")))
            manifest.record_quality_gate("service_name_validated", self._validate_service_name(service_name))
            manifest.record_quality_gate("current_state_understood", bool(current_state.get("what_exists")))
            manifest.record_quality_gate("desired_state_defined", bool(desired_state.get("vision")))
            manifest.record_quality_gate("stakeholders_identified", bool(stakeholders.get("users")))
            manifest.record_quality_gate("constraints_documented", bool(constraints))
            manifest.record_quality_gate("risks_assessed", bool(risks))
            manifest.record_quality_gate("validation_complete", bool(validation.get("reasoning")))
            manifest.record_quality_gate("no_duplicate_service", not (service_exists and registry_check.should_block(service_info)))

            manifest.complete(success=True)
            manifest.save(manifest_path)

            logger.info(f"Discovery complete: {service_name}")
            logger.info(f"Manifest saved to: {manifest_path}")

            # Record history
            history_path = workspace_root / ".spectra" / "history" / "discover-history.yaml"
            history_path.parent.mkdir(parents=True, exist_ok=True)
            self.record_history(
                history=history,
                decision=llm_response,
                outcome="success",
                result=ActivityResult(
                    activity_name="discover",
                    success=True,
                    outputs=outputs,
                    errors=[],
                ),
                context=activity_context,
            )
            history.save(history_path)
            logger.debug(f"History saved to: {history_path}")

            return ActivityResult(
                activity_name="discover",
                success=True,
                outputs=outputs,
                errors=[],
            )

        except Exception as e:
            logger.error(f"Discover activity failed: {e}", exc_info=True)
            return ActivityResult(
                activity_name="discover",
                success=False,
                outputs={},
                errors=[str(e)],
            )

    def format_prompt(self, context: Dict, history: Optional[list] = None) -> str:
        """
        Format comprehensive system prompt for discover activity.

        Args:
            context: Context dictionary (summarized)
            history: Optional history entries

        Returns:
            Formatted system prompt
        """
        prompt_parts = [
            "You are a SPECTRA Discovery Analyst - an expert in problem understanding and solution validation.",
            "",
            "YOUR MISSION:",
            "Conduct deep, comprehensive discovery to understand the problem, current state, desired state,",
            "stakeholders, constraints, risks, and validate the proposed solution.",
            "",
            "DISCOVERY DIMENSIONS TO EXPLORE:",
            "1. Problem: What problem are we solving? Who has it? Impact? Root cause?",
            "2. Current State: What exists now? Pain points? Gaps? Blockers?",
            "3. Desired State: Vision? Success criteria? Goals?",
            "4. Stakeholders: Users? Decision-makers? Beneficiaries? Affected parties?",
            "5. Constraints: Technical? Business? Time? Budget? Compliance?",
            "6. Requirements: Functional? Non-functional? Quality?",
            "7. Risks: Technical? Business? Implementation?",
            "8. Alternatives: Other options? Why this solution?",
            "9. Validation: Does solution solve problem? How? Confidence? Assumptions?",
            "10. Next Steps: What happens next in the pipeline?",
            "",
            "SPECTRA STANDARDS:",
            "- Service naming: MONONYMIC (single word or hyphenated), kebab-case, lowercase, no spaces",
            "- No 'spectra-' prefix or '-service' suffix",
            "- Examples: 'logging', 'monitoring', 'user-auth', 'data-processor'",
            "- Invalid: 'spectra-logging-service', 'logging-service', action verbs, prepositions",
            "- Service types: service, tool, package, concept",
            "- Maturity levels: L1-MVP through L7-Self-Communicating (handled by Assess activity)",
            "",
            "SERVICE NAME EXTRACTION RULES:",
            "- Extract the SPECIFIC service name, not abstract concepts",
            "- If user says 'monitoring service', extract 'monitoring' (not 'observability')",
            "- If user says 'logging service', extract 'logging' (not 'observability')",
            "- Abstract concepts like 'observability' are umbrella terms, not service names",
            "- Prioritize explicit service mentions: 'X service' → extract 'X'",
            "- Prefer concrete service names over abstract concepts",
            "- In SPECTRA: 'logging' and 'monitoring' are separate services under 'observability' concept",
            "",
            "AVAILABLE TOOLS (recommend if needed):",
            "- registry_check: Check if service already exists (already checked)",
            "- discovery_game: Run 7x7 discovery game (49 questions, comprehensive architecture)",
            "- extract_design: Infer architecture and technology stack",
            "- generate_documents: Create problem statement and proposed approach documents",
            "",
        ]

        # Add summarized context (not full dump)
        if context.get("specification_summary"):
            prompt_parts.append(f"SPECIFICATION SUMMARY:\n{context['specification_summary']}\n")
        if context.get("manifest_summary"):
            prompt_parts.append(f"MANIFEST SUMMARY:\n{context['manifest_summary']}\n")
        if context.get("tools"):
            prompt_parts.append(f"AVAILABLE TOOLS: {len(context['tools'])} tools available\n")
        if context.get("history_count", 0) > 0:
            prompt_parts.append(f"HISTORY: {context['history_count']} recent entries available\n")

        if history:
            # Limit history to last 2 entries, summarize
            history_text = json.dumps(history[-2:], indent=2)
            if len(history_text) > 500:  # Limit history size
                history_text = json.dumps(history[-1:], indent=2)  # Just last one
            prompt_parts.extend([
                "",
                "RECENT HISTORY (past discovery decisions/outcomes):",
                history_text,
            ])

        prompt_parts.extend([
            "",
            "OUTPUT FORMAT:",
            "Provide comprehensive discovery results in JSON format covering all 10 dimensions.",
            "Include: service_name, problem, current_state, desired_state, stakeholders,",
            "constraints, requirements, risks, alternatives, idea, validation, recommended_tools, next_steps.",
        ])

        return "\n".join(prompt_parts)

    def _normalize_service_name(self, name: str) -> str:
        """
        Normalize service name by removing common mistakes.

        Removes:
        - 'spectra-' prefix
        - '-service' suffix
        - Trailing/leading whitespace

        Args:
            name: Service name from LLM

        Returns:
            Normalized service name
        """
        if not name:
            return name

        normalized = name.strip().lower()

        # Remove 'spectra-' prefix
        if normalized.startswith("spectra-"):
            normalized = normalized[8:]  # len("spectra-") = 8

        # Remove '-service' suffix
        if normalized.endswith("-service"):
            normalized = normalized[:-8]  # len("-service") = 8

        # Remove 'service' suffix (if standalone word)
        if normalized.endswith("-service"):
            normalized = normalized[:-8]

        return normalized.strip()

    def _validate_service_name(self, name: str) -> bool:
        """
        Validate service name meets SPECTRA naming standards.

        Rules:
        - Must be lowercase
        - Must start with letter
        - Can contain letters, numbers, hyphens
        - No spaces
        - No action verbs
        - No prepositions
        - No 'service', 'app', 'application', 'system'

        Args:
            name: Service name to validate

        Returns:
            True if valid, False otherwise
        """
        if not name:
            return False

        # Check format: lowercase, kebab-case
        if not re.match(r"^[a-z][a-z0-9-]*$", name):
            return False

        # Check for invalid words
        invalid_words = {
            # Action verbs
            "deploy", "build", "create", "make", "add", "setup", "configure",
            "install", "run", "execute", "start", "stop", "launch",
            # Prepositions
            "to", "from", "in", "on", "at", "for", "with", "by",
            # Other reserved
            "service", "app", "application", "system",
        }

        # Check each component (split by hyphen)
        parts = name.split("-")
        for part in parts:
            if part in invalid_words:
                return False

        return True

