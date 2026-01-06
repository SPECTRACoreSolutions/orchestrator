"""
Discover Activity - Problem/idea validation using LLM

Uses LLM to:
- Extract service name
- Extract problem statement
- Validate idea
- Assess maturity level
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

from ..activity import Activity, ActivityContext, ActivityResult
from ..state import ActivityHistory, Manifest

logger = logging.getLogger(__name__)


class DiscoverActivity(Activity):
    """
    Discover activity - Problem/idea validation.
    
    Uses LLM to analyse user input and discover:
    - Service name
    - Problem statement
    - Idea validation
    - Maturity assessment
    """

    async def execute(self, context: ActivityContext) -> ActivityResult:
        """
        Execute discover activity.
        
        Args:
            context: Activity context
            
        Returns:
            ActivityResult with discovery outputs
        """
        logger.info(f"Executing Discover activity for: {context.user_input}")
        
        # Load/build context
        activity_context = self.context_builder.build_activity_context(
            activity_name="discover",
            service_name=context.service_name,
            specification=context.specification,
            manifest=context.manifest,
            tools=context.tools,
        )
        
        # Load history
        history = self.load_history()
        
        # Format prompt
        system_prompt = self.format_prompt(
            context=activity_context,
            history=[entry.__dict__ for entry in history.get_recent(10)],
        )
        
        user_message = f"""
Run discovery on this: {context.user_input}

Analyse the user input and the context provided.
Extract the service name, problem statement, validate the idea, and assess maturity.

Respond in JSON format:
{{
    "service_name": "extracted service name",
    "problem": {{
        "statement": "clear problem statement",
        "impact": "high|medium|low"
    }},
    "idea": {{
        "name": "service name",
        "type": "service|tool|package|concept",
        "priority": "critical|important|nice-to-have"
    }},
    "validation": {{
        "problem_solved": true|false,
        "reasoning": "why this idea solves the problem"
    }},
    "maturity_assessment": {{
        "level": "L1|L2|L3|L4|L5|L6|L7",
        "target": "what maturity level to aim for",
        "reasoning": "why this level"
    }},
    "next_steps": "what should happen next in the pipeline"
}}
"""
        
        try:
            # Call LLM
            logger.debug("Calling LLM for discovery analysis...")
            llm_response = await self.call_llm(system_prompt, user_message)
            
            # Extract discovery results
            service_name = llm_response.get("service_name", context.service_name or "unknown")
            problem = llm_response.get("problem", {})
            idea = llm_response.get("idea", {})
            validation = llm_response.get("validation", {})
            maturity = llm_response.get("maturity_assessment", {})
            next_steps = llm_response.get("next_steps", "")
            
            # Build outputs
            outputs = {
                "service_name": service_name,
                "problem": problem,
                "idea": idea,
                "validation": validation,
                "maturity_assessment": maturity,
                "next_steps": next_steps,
            }
            
            # Update manifest
            workspace_root = self.context_builder.workspace_root
            manifests_dir = workspace_root / ".spectra" / "manifests"
            manifests_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = manifests_dir / "discover-manifest.yaml"
            
            manifest = Manifest(activity="discover")
            manifest.start()
            self.update_manifest(manifest, outputs)
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
        Format system prompt for discover activity.
        
        Args:
            context: Context dictionary
            history: Optional history entries
            
        Returns:
            Formatted system prompt
        """
        prompt_parts = [
            "You are the Discover activity agent for SPECTRA orchestrator.",
            "",
            "YOUR TASK:",
            "Run discovery on the user's input to understand the problem and validate the idea.",
            "",
            "CONTEXT:",
            json.dumps(context, indent=2),
        ]
        
        if history:
            prompt_parts.extend([
                "",
                "HISTORY (past discovery decisions/outcomes):",
                json.dumps(history, indent=2),
            ])
        
        prompt_parts.extend([
            "",
            "SPECTRA STANDARDS:",
            "- Service naming: Services must be kebab-case, lowercase, no spaces",
            "- Maturity levels: L1-MVP through L7-Autonomous",
            "- Service types: service, tool, package, concept",
            "- Discovery goal: Understand the problem and validate the idea solves it",
        ])
        
        return "\n".join(prompt_parts)

