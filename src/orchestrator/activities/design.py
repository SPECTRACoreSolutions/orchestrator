"""
Design Activity - LLM-driven architecture generation, Specification creation

SPECTRA-Grade design activity that generates architecture and creates Specifications.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

from ..activity import Activity, ActivityContext, ActivityResult

logger = logging.getLogger(__name__)


class Design(Activity):
    """
    Design - Architecture generation and Specification creation activity.

    Uses LLM to:
    - Generate service architecture
    - Create Specification document
    - Design service structure
    - Generate design artifacts
    """

    async def execute(self, context: ActivityContext) -> ActivityResult:
        """
        Execute design activity.

        Args:
            context: Activity context

        Returns:
            ActivityResult with design outputs
        """
        logger.info(f"Executing Design activity for: {context.user_input}")

        workspace_root = self.context_builder.workspace_root

        # Build context for design
        activity_context = self.context_builder.build_activity_context(
            activity_name="design",
            service_name=context.service_name,
            specification=context.specification,
            manifest=context.manifest,
        )

        # Format prompt for architecture generation
        system_prompt = self.format_prompt(context=activity_context)

        user_message = f"""
Design the architecture and create specification for: {context.user_input}

DESIGN TASKS:
1. Architecture Generation:
   - Design service architecture (components, layers, interactions)
   - Define technology stack
   - Design data models and APIs
   - Define integration points

2. Specification Creation:
   - Create comprehensive Specification document
   - Define requirements and constraints
   - Specify interfaces and contracts
   - Document design decisions

3. Service Structure:
   - Design directory structure
   - Define file organization
   - Specify code organization patterns

4. Design Artifacts:
   - Create architecture diagrams (text descriptions)
   - Document design patterns
   - Define quality gates

SPECTRA STANDARDS:
- Follow canonical 7-folder structure (src/, tests/, docs/, scripts/, config/, data/, tools/)
- Use SPECTRA naming conventions (mononymic, kebab-case)
- Design for MCP-Native architecture
- Include observability (logging, metrics, tracing)
- Plan for The Seven Autonomies

Respond in JSON format with:
- architecture: Object with components, layers, tech_stack, data_models, apis, integrations
- specification: Object with requirements, constraints, interfaces, contracts, design_decisions
- service_structure: Object with directory_structure, file_organization, code_patterns
- design_artifacts: Object with diagrams, patterns, quality_gates
- specification_document: Full specification text (markdown format)
"""

        try:
            # Call LLM for design
            logger.debug("Calling LLM for architecture generation...")
            llm_response = await self.call_llm(system_prompt, user_message, max_tokens=4096)

            # Extract design results
            architecture = llm_response.get("architecture", {})
            specification = llm_response.get("specification", {})
            service_structure = llm_response.get("service_structure", {})
            design_artifacts = llm_response.get("design_artifacts", {})
            specification_document = llm_response.get("specification_document", "")

            # Save specification document if provided
            spec_path = None
            if specification_document and context.service_name:
                workspace_root = self.context_builder.workspace_root or Path.cwd()
                service_dir = workspace_root / "Core" / context.service_name
                service_dir.mkdir(parents=True, exist_ok=True)
                spec_path = service_dir / "SPECIFICATION.md"

                try:
                    spec_path.write_text(specification_document, encoding="utf-8")
                    logger.info(f"Specification saved to: {spec_path}")
                except Exception as e:
                    logger.warning(f"Could not save specification document: {e}")

            outputs = {
                "architecture": architecture,
                "specification": specification,
                "service_structure": service_structure,
                "design_artifacts": design_artifacts,
                "specification_document_path": str(spec_path) if spec_path else None,
            }

            logger.info("Design complete")

            return ActivityResult(
                activity_name="design",
                success=True,
                outputs=outputs,
                errors=[],
            )

        except Exception as e:
            logger.error(f"Design activity failed: {e}", exc_info=True)
            return ActivityResult(
                activity_name="design",
                success=False,
                outputs={},
                errors=[str(e)],
            )

    def format_prompt(self, context: Dict, history: Optional[list] = None) -> str:
        """
        Format system prompt for design activity.

        Args:
            context: Context dictionary
            history: Optional history entries

        Returns:
            Formatted system prompt
        """
        prompt_parts = [
            "You are a SPECTRA Architecture Designer - an expert in service design and specification creation.",
            "",
            "YOUR MISSION:",
            "Design service architecture and create comprehensive Specifications following SPECTRA standards.",
            "",
            "SPECTRA ARCHITECTURE PRINCIPLES:",
            "- MCP-Native: All vendor integrations through SPECTRA MCP Layer",
            "- Canonical Structure: 7-folder structure (src/, tests/, docs/, scripts/, config/, data/, tools/)",
            "- The Seven Autonomies: Self-Documenting, Self-Healing, Self-Optimizing, Self-Scaling,",
            "  Self-Recovering, Self-Upgrading, Self-Reverting",
            "- Observability: Comprehensive logging, metrics, tracing",
            "- SPECTRA-Grade: Zero tech debt, perfect execution",
            "",
            "SPECIFICATION REQUIREMENTS:",
            "- Comprehensive requirements (functional, non-functional)",
            "- Clear constraints and assumptions",
            "- Well-defined interfaces and contracts",
            "- Documented design decisions with rationale",
            "- Quality gates and success criteria",
            "",
            "ARCHITECTURE DESIGN:",
            "- Component-based design",
            "- Layered architecture (presentation, business, data)",
            "- Clear separation of concerns",
            "- Scalable and maintainable structure",
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
            "Provide comprehensive design results in JSON format:",
            "- architecture: Components, layers, tech stack, data models, APIs, integrations",
            "- specification: Requirements, constraints, interfaces, contracts, design decisions",
            "- service_structure: Directory structure, file organization, code patterns",
            "- design_artifacts: Diagrams, patterns, quality gates",
            "- specification_document: Full specification in markdown format",
        ])

        return "\n".join(prompt_parts)

