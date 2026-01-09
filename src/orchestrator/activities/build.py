"""
Build Activity - Code generation and compilation

SPECTRA-Grade build activity.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Optional

from ..activity import Activity, ActivityContext, ActivityResult
from ..state import ActivityHistory, Manifest

logger = logging.getLogger(__name__)


class Build(Activity):
    """
    Build - Code generation and compilation activity.

    Uses LLM and playbooks to generate code and build services.
    """

    async def call_llm_raw(self, system_prompt: str, user_message: str, max_tokens: int = 2048) -> str:
        """
        Call LLM and return raw text response (not JSON).

        Args:
            system_prompt: System prompt
            user_message: User message
            max_tokens: Maximum tokens

        Returns:
            Raw text response from LLM
        """
        try:
            response = await self.llm_client.chat_completion(
                system_prompt=system_prompt,
                user_message=user_message,
                max_tokens=max_tokens,
                temperature=0.3,
            )
            return response
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return ""

    async def _generate_file_code(
        self,
        file_info: Dict,
        service_dir: Path,
        context: ActivityContext,
    ) -> str:
        """
        Generate actual code for a single file using LLM.

        Args:
            file_info: File information dict
            service_dir: Service directory path
            context: Activity context

        Returns:
            Generated code content
        """
        file_path = file_info.get("path", "")
        file_type = file_info.get("type", "source")
        purpose = file_info.get("purpose", "Unknown")
        dependencies = file_info.get("dependencies", [])

        system_prompt = f"""You are a SPECTRA Code Generator. Generate COMPLETE, WORKING code.

FILE: {file_path}
PURPOSE: {purpose}
TYPE: {file_type}
DEPENDENCIES: {', '.join(dependencies) if dependencies else 'None'}

REQUIREMENTS:
- Generate full implementation (not stubs or placeholders)
- Include comprehensive error handling
- Add logging using Python logging module
- Follow SPECTRA standards (mononymic, kebab-case, docstrings)
- Include type hints (Python 3.9+)
- Add comprehensive docstrings

CODE QUALITY:
- No placeholder comments like "... implementation here"
- No TODO comments - implement everything
- Production-ready code
- SPECTRA-grade quality"""

        user_message = f"""Generate complete implementation code for: {file_path}

Project Context: {context.user_input}

Specification:
{context.specification[:800] if context.specification else 'Build robust, production-ready implementation'}

Requirements:
1. Full implementation (no stubs)
2. Error handling for all operations
3. Logging for key operations
4. Type hints for all functions
5. Comprehensive docstrings

Return ONLY the Python code (no JSON, no markdown fences, no explanatory text).
Start with imports, then code."""

        logger.info(f"Generating code for: {file_path} (priority: critical)")
        code = await self.call_llm_raw(system_prompt, user_message, max_tokens=2048)

        # Clean up any markdown fences if LLM included them
        if code.startswith("```"):
            lines = code.split("\n")
            # Remove first and last lines if they're fences
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            code = "\n".join(lines)

        return code.strip()

    def _generate_template(self, file_info: Dict) -> str:
        """
        Generate template code for normal priority files.

        Args:
            file_info: File information dict

        Returns:
            Template code content
        """
        file_path = file_info.get("path", "")
        file_type = file_info.get("type", "source")
        purpose = file_info.get("purpose", "")

        if file_path.endswith(".py"):
            module_name = Path(file_path).stem
            return f'''"""
{module_name} - {purpose}

SPECTRA-grade implementation.
"""

import logging

logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    logger.info("{module_name} initialized")
    pass


if __name__ == "__main__":
    main()
'''
        elif file_path.endswith(".md"):
            return f"# {Path(file_path).stem}\n\n{purpose}\n\n## Overview\n\nTODO: Add documentation\n"
        else:
            return f"# {Path(file_path).name}\n# {purpose}\n"

    def _generate_config(self, file_info: Dict) -> str:
        """
        Generate config/data files for low priority items.

        Args:
            file_info: File information dict

        Returns:
            Config file content
        """
        file_path = file_info.get("path", "")

        if file_path.endswith(".json"):
            return "{}\n"
        elif file_path.endswith(".yaml") or file_path.endswith(".yml"):
            return "# SPECTRA configuration\n"
        elif file_path.endswith(".ini"):
            return "[DEFAULT]\n"
        elif file_path.endswith(".txt"):
            return ""
        else:
            return f"# {Path(file_path).name}\n"

    async def execute(self, context: ActivityContext) -> ActivityResult:
        """
        Execute build activity.

        Args:
            context: Activity context

        Returns:
            ActivityResult with build outputs
        """
        logger.info(f"Executing Build activity for: {context.user_input}")

        workspace_root = self.context_builder.workspace_root

        # Build context for building
        activity_context = self.context_builder.build_activity_context(
            activity_name="build",
            service_name=context.service_name,
            specification=context.specification,
            manifest=context.manifest,
        )

        # Get playbook metadata for building
        # Use semantic filtering to get most relevant playbooks
        filtered_playbooks = await self.playbook_registry.filter_relevant_playbooks(
            activity_name="build",
            task=context.user_input,
            llm_client=self.llm_client,
            max_playbooks=5,
        )

        # Get playbook context with filtered playbooks
        playbook_context = self.playbook_registry.get_playbook_context_for_llm(
            activity_name="build",
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

        # Format prompt for code generation and building
        system_prompt = self.format_prompt(context=activity_context, history=history_summary)

        user_message = f"""
Generate code structure for: {context.user_input}

CRITICAL: Code generation happens in TWO PHASES:
- Phase 1 (now): Generate file structure and categorize files
- Phase 2 (next): Generate actual code for each critical file

PHASE 1 TASK - File Structure & Categorization:
1. Design service code structure following SPECTRA 7-folder pattern
2. List ALL files needed with metadata
3. Categorize each file by priority:
   - "critical": Main source files (need full code generation)
   - "normal": Supporting files (can use templates)
   - "low": Config/data files (can auto-generate)

AVAILABLE PLAYBOOKS:
{json.dumps(playbook_context.get("available_playbooks", []), indent=2)}

SPECTRA STANDARDS:
- Canonical 7-folder structure: src/, tests/, docs/, scripts/, config/, data/, tools/
- Naming conventions: mononymic, kebab-case
- Python/PySpark: Mandatory default language
- Code quality: Linting must pass, zero errors

CRITICAL: Respond with ONLY raw JSON. No markdown fences (```json), no explanation text, 
no preamble, no "Here is the JSON:" text. Start your response with {{ and end with }}. 
Pure JSON only - nothing else.

Expected JSON format:
{{
  "code_structure": {{
    "directories": [],
    "file_categories": {{
      "critical": [],
      "normal": [],
      "low": []
    }}
  }},
  "files_to_create": [
    {{
      "path": "src/main.py",
      "type": "source",
      "priority": "critical",
      "purpose": "Main service implementation",
      "dependencies": ["fastapi", "pydantic"],
      "estimated_lines": 150
    }}
  ],
  "build_commands": [{{"command": str, "description": str}}],
  "build_results": {{
    "build_successful": bool,
    "artifacts": [],
    "errors": []
  }},
  "validation": {{
    "structure_complete": bool,
    "build_passed": bool,
    "linting_passed": bool
  }}
}}

IMPORTANT: 
- Categorize files accurately - critical files will get full LLM generation!
- Your response must be ONLY the JSON object above, nothing else!
"""

        try:
            # Call LLM for code generation and building
            logger.debug("Calling LLM for code generation and build analysis...")
            # Use OpenAI response_format if available (forces JSON output)
            # Check if we're using OpenAI API (contains "api.openai.com" or model starts with "gpt")
            import os
            api_url_lower = self.llm_client.api_url.lower()
            model_lower = self.llm_client.model.lower()
            is_openai = (
                "api.openai.com" in api_url_lower
                or "openai" in api_url_lower
                or model_lower.startswith("gpt")
                or "gpt-" in model_lower
                or "gpt4" in model_lower
            )
            response_format = None
            if is_openai:
                response_format = {"type": "json_object"}
                logger.debug("Using OpenAI response_format to enforce JSON output")
            llm_response = await self.call_llm(
                system_prompt, 
                user_message, 
                max_tokens=4096,
                response_format=response_format,
            )

            # Extract build results
            code_structure = llm_response.get("code_structure", {})
            files_to_create = llm_response.get("files_to_create", [])
            build_commands = llm_response.get("build_commands", [])
            build_results = llm_response.get("build_results", {})
            validation = llm_response.get("validation", {})

            # Determine service name and directory
            service_name = context.service_name or "powerapp-service-catalog"
            service_dir = workspace_root / "Core" / service_name

            # CREATE service directory if it doesn't exist
            service_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Service directory: {service_dir}")

            # Phase 2: Generate files with chunked approach
            files_created = []
            for file_info in files_to_create:
                file_path = service_dir / file_info.get("path", "")
                file_path.parent.mkdir(parents=True, exist_ok=True)

                priority = file_info.get("priority", "normal")

                try:
                    if priority == "critical":
                        # Generate actual code using LLM
                        logger.info(f"Generating code for critical file: {file_path}")
                        code = await self._generate_file_code(file_info, service_dir, context)
                        if code and len(code) > 50:  # Sanity check - got real code
                            file_path.write_text(code, encoding="utf-8")
                            logger.info(f"✅ Created critical file: {file_path} ({len(code)} chars)")
                        else:
                            # Fallback to template if LLM failed
                            logger.warning(f"⚠️ LLM generation failed for {file_path}, using template")
                            code = self._generate_template(file_info)
                            file_path.write_text(code, encoding="utf-8")
                    elif priority == "normal":
                        # Use template-based generation
                        logger.info(f"Generating template for normal file: {file_path}")
                        code = self._generate_template(file_info)
                        file_path.write_text(code, encoding="utf-8")
                    else:  # low priority
                        # Auto-generate config/data files
                        logger.info(f"Generating config for low priority file: {file_path}")
                        code = self._generate_config(file_info)
                        file_path.write_text(code, encoding="utf-8")

                    files_created.append(str(file_path))

                except Exception as e:
                    logger.error(f"Failed to generate {file_path}: {e}")
                    # Create minimal file to not block progress
                    file_path.write_text(f"# TODO: Generation failed - {e}\n", encoding="utf-8")
                    files_created.append(str(file_path))

            # Create basic directory structure if LLM provided it
            if code_structure.get("directories"):
                for dir_path in code_structure["directories"]:
                    dir_full_path = service_dir / dir_path
                    dir_full_path.mkdir(parents=True, exist_ok=True)
                    logger.debug(f"Created directory: {dir_full_path}")

            # Execute build commands (gracefully handle missing tools)
            build_outputs = []
            build_errors = []
            if build_commands:
                for cmd_info in build_commands:
                    command = cmd_info.get("command", "")
                    if command:
                        # Skip commands that require files that don't exist
                        if "requirements.txt" in command and not (service_dir / "requirements.txt").exists():
                            logger.warning(f"Skipping command (requirements.txt not found): {command}")
                            continue
                        if "build.sh" in command and not (service_dir / "scripts" / "build.sh").exists():
                            logger.warning(f"Skipping command (build.sh not found): {command}")
                            continue

                        # Normalize command for Windows
                        cmd_parts = command.split()
                        if cmd_parts[0] in ["black", "isort", "pytest"]:
                            # Use python -m for these tools
                            cmd_parts = ["python", "-m"] + cmd_parts

                        try:
                            result = subprocess.run(
                                cmd_parts,
                                cwd=service_dir,
                                capture_output=True,
                                text=True,
                                timeout=300,  # 5 minute timeout
                            )
                            build_outputs.append({
                                "command": command,
                                "stdout": result.stdout[:500],  # Limit output length
                                "stderr": result.stderr[:500],
                                "returncode": result.returncode,
                            })
                            if result.returncode != 0:
                                # Only add to errors if it's a critical failure
                                if "requirements.txt" in command:
                                    build_errors.append(f"Build command failed: {command}\n{result.stderr[:200]}")
                                else:
                                    logger.warning(f"Build command warning (non-critical): {command}")
                        except FileNotFoundError:
                            # Tool not found - log warning but don't fail
                            logger.warning(f"Build tool not found (skipping): {command}")
                        except Exception as e:
                            logger.warning(f"Build command error (non-critical): {command}\n{str(e)}")

            outputs = {
                "code_structure": code_structure,
                "files_created": files_created,
                "build_commands_executed": [cmd.get("command") for cmd in build_commands],
                "build_results": {
                    **build_results,
                    "outputs": build_outputs,
                    "errors": build_errors,
                },
                "validation": validation,
            }

            # Update manifest
            manifests_dir = workspace_root / ".spectra" / "manifests"
            manifests_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = manifests_dir / "build-manifest.yaml"

            manifest = Manifest(activity="build")
            manifest.start()
            self.update_manifest(manifest, outputs)

            # Record quality gates
            manifest.record_quality_gate("code_structure_generated", bool(code_structure))
            manifest.record_quality_gate("files_created", len(files_created) > 0)
            manifest.record_quality_gate("structure_complete", validation.get("structure_complete", False))
            manifest.record_quality_gate("build_passed", validation.get("build_passed", False) and len(build_errors) == 0)
            manifest.record_quality_gate("linting_passed", validation.get("linting_passed", False))

            manifest.complete(success=len(build_errors) == 0)
            manifest.save(manifest_path)

            logger.info("Build complete")
            logger.info(f"Manifest saved to: {manifest_path}")

            # Record history
            history_path = workspace_root / ".spectra" / "history" / "build-history.yaml"
            history_path.parent.mkdir(parents=True, exist_ok=True)
            self.record_history(
                history=history,
                decision=llm_response,
                outcome="success" if len(build_errors) == 0 else "partial",
                result=ActivityResult(
                    activity_name="build",
                    success=len(build_errors) == 0,
                    outputs=outputs,
                    errors=build_errors,
                ),
                context=activity_context,
            )
            history.save(history_path)
            logger.debug(f"History saved to: {history_path}")

            return ActivityResult(
                activity_name="build",
                success=len(build_errors) == 0,
                outputs=outputs,
                errors=build_errors,
            )

        except Exception as e:
            logger.error(f"Build activity failed: {e}", exc_info=True)
            return ActivityResult(
                activity_name="build",
                success=False,
                outputs={},
                errors=[str(e)],
            )

    def format_prompt(self, context: Dict, history: Optional[list] = None) -> str:
        """
        Format system prompt for build activity.

        Args:
            context: Context dictionary
            history: Optional history entries

        Returns:
            Formatted system prompt
        """
        prompt_parts = [
            "You are a SPECTRA Code Generator - an expert in code generation and build systems.",
            "",
            "YOUR MISSION:",
            "Generate service code following SPECTRA standards and execute builds.",
            "",
            "SPECTRA STANDARDS:",
            "- Canonical 7-folder structure: src/, tests/, docs/, scripts/, config/, data/, tools/",
            "- Naming conventions: mononymic, kebab-case",
            "- Code quality: Zero errors, linting must pass",
            "- Test structure: pytest-based organization",
            "- Python/PySpark: Mandatory default language",
            "",
            "CODE GENERATION PRINCIPLES:",
            "- Generate complete, working code (not stubs)",
            "- Follow SPECTRA architecture patterns",
            "- Include comprehensive error handling",
            "- Add observability (logging, metrics)",
            "",
            "BUILD PROCESS:",
            "- Execute build/compilation commands",
            "- Run linting and code quality checks",
            "- Validate build artifacts",
            "- Handle build errors gracefully",
            "",
        ]

        if context.get("specification_summary"):
            prompt_parts.append(f"SPECIFICATION SUMMARY:\n{context['specification_summary']}\n")
        if context.get("manifest_summary"):
            prompt_parts.append(f"MANIFEST SUMMARY:\n{context['manifest_summary']}\n")
        if context.get("architecture"):
            prompt_parts.append(f"ARCHITECTURE:\n{json.dumps(context['architecture'], indent=2)}\n")

        if history:
            prompt_parts.extend([
                "",
                "RECENT HISTORY:",
                json.dumps(history[-2:], indent=2),
            ])

        prompt_parts.extend([
            "",
            "OUTPUT FORMAT:",
            "Respond in JSON format with code_structure, files_to_create, build_commands, build_results, and validation fields.",
        ])

        return "\n".join(prompt_parts)
