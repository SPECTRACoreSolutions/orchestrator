"""
Test Activity - Test execution and validation

SPECTRA-Grade testing activity.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Optional

from ..activity import Activity, ActivityContext, ActivityResult
from ..state import ActivityHistory, Manifest

logger = logging.getLogger(__name__)


class Test(Activity):
    """
    Test - Test execution and validation activity.

    Uses LLM and playbooks to execute tests and validate quality.
    """

    async def execute(self, context: ActivityContext) -> ActivityResult:
        """
        Execute test activity.

        Args:
            context: Activity context

        Returns:
            ActivityResult with test outputs
        """
        logger.info(f"Executing Test activity for: {context.user_input}")

        workspace_root = self.context_builder.workspace_root

        # Build context for testing
        activity_context = self.context_builder.build_activity_context(
            activity_name="test",
            service_name=context.service_name,
            specification=context.specification,
            manifest=context.manifest,
        )

        # Get playbook metadata for testing
        # Use semantic filtering to get most relevant playbooks
        filtered_playbooks = await self.playbook_registry.filter_relevant_playbooks(
            activity_name="test",
            task=context.user_input,
            llm_client=self.llm_client,
            max_playbooks=5,
        )

        # Get playbook context with filtered playbooks
        playbook_context = self.playbook_registry.get_playbook_context_for_llm(
            activity_name="test",
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

        # Format prompt for test execution
        system_prompt = self.format_prompt(context=activity_context, history=history_summary)

        user_message = f"""
Execute tests and validate quality for: {context.user_input}

TESTING TASKS:
1. Test Strategy Determination:
   - Determine appropriate test strategy (unit, integration, e2e)
   - Identify test suites to execute
   - Determine coverage requirements

2. Test Execution:
   - Execute unit tests (pytest)
   - Run integration tests if applicable
   - Execute end-to-end tests if applicable

3. Test Results Analysis:
   - Parse test results
   - Calculate coverage metrics
   - Identify test failures

4. Validation:
   - Verify all tests pass
   - Validate coverage thresholds met
   - Confirm no critical failures

AVAILABLE PLAYBOOKS:
{json.dumps(playbook_context.get("available_playbooks", []), indent=2)}

SPECTRA TESTING STANDARDS:
- pytest: Primary test framework
- Coverage threshold: Minimum 80% code coverage
- Test organization: tests/ directory mirroring src/ structure
- TDD/BDD: Test-driven development for critical features

Respond in JSON format with:
- test_strategy: {{unit_tests: bool, integration_tests: bool, e2e_tests: bool}}
- test_suites: [{{name, path, type}}]
- test_results: {{total_tests: int, passed: int, failed: int, skipped: int, coverage_percent: float, failures: []}}
- validation: {{all_passed: bool, coverage_threshold_met: bool, no_critical_failures: bool}}
"""

        try:
            # Call LLM for test strategy
            logger.debug("Calling LLM for test strategy analysis...")
            llm_response = await self.call_llm(system_prompt, user_message, max_tokens=2048)

            # Extract test strategy
            test_strategy = llm_response.get("test_strategy", {})
            test_suites = llm_response.get("test_suites", [])
            test_results = llm_response.get("test_results", {})
            validation = llm_response.get("validation", {})

            # Execute tests (if service directory exists)
            actual_test_results = {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "coverage_percent": 0.0,
                "failures": [],
            }
            service_dir = None
            if context.service_name:
                service_dir = workspace_root / "Core" / context.service_name
                if service_dir.exists() and (service_dir / "tests").exists():
                    # Run pytest
                    try:
                        result = subprocess.run(
                            ["pytest", "tests/", "-v", "--tb=short"],
                            cwd=service_dir,
                            capture_output=True,
                            text=True,
                            timeout=600,  # 10 minute timeout
                        )
                        stdout = result.stdout
                        stderr = result.stderr

                        # Parse pytest output (basic parsing)
                        if "passed" in stdout:
                            # Extract numbers from pytest summary line
                            import re
                            passed_match = re.search(r"(\d+) passed", stdout)
                            failed_match = re.search(r"(\d+) failed", stdout)
                            skipped_match = re.search(r"(\d+) skipped", stdout)

                            actual_test_results["passed"] = int(passed_match.group(1)) if passed_match else 0
                            actual_test_results["failed"] = int(failed_match.group(1)) if failed_match else 0
                            actual_test_results["skipped"] = int(skipped_match.group(1)) if skipped_match else 0
                            actual_test_results["total_tests"] = (
                                actual_test_results["passed"] +
                                actual_test_results["failed"] +
                                actual_test_results["skipped"]
                            )

                        # Extract failures
                        if result.returncode != 0:
                            # Basic failure extraction
                            failure_lines = [line for line in stdout.split("\n") if "FAILED" in line]
                            actual_test_results["failures"] = failure_lines[:10]  # Limit to 10 failures

                        # Run coverage if pytest-cov is available
                        try:
                            cov_result = subprocess.run(
                                ["pytest", "tests/", "--cov=src", "--cov-report=term"],
                                cwd=service_dir,
                                capture_output=True,
                                text=True,
                                timeout=600,
                            )
                            # Extract coverage percentage
                            import re
                            cov_match = re.search(r"TOTAL.*?(\d+)%", cov_result.stdout)
                            if cov_match:
                                actual_test_results["coverage_percent"] = float(cov_match.group(1))
                        except Exception:
                            logger.warning("Coverage calculation failed (pytest-cov may not be installed)")

                    except subprocess.TimeoutExpired:
                        actual_test_results["failures"].append("Test execution timed out")
                    except Exception as e:
                        actual_test_results["failures"].append(f"Test execution error: {str(e)}")

            # Merge LLM results with actual test results
            final_test_results = {**test_results, **actual_test_results}
            final_validation = {
                **validation,
                "all_passed": actual_test_results["failed"] == 0,
                "coverage_threshold_met": actual_test_results["coverage_percent"] >= 80.0,
                "no_critical_failures": len(actual_test_results["failures"]) == 0,
            }

            outputs = {
                "test_strategy": test_strategy,
                "test_suites": test_suites,
                "test_results": final_test_results,
                "validation": final_validation,
            }

            # Update manifest
            manifests_dir = workspace_root / ".spectra" / "manifests"
            manifests_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = manifests_dir / "test-manifest.yaml"

            manifest = Manifest(activity="test")
            manifest.start()
            self.update_manifest(manifest, outputs)

            # Record quality gates
            manifest.record_quality_gate("test_strategy_determined", bool(test_strategy))
            manifest.record_quality_gate("tests_executed", actual_test_results["total_tests"] > 0)
            manifest.record_quality_gate("all_tests_passed", final_validation["all_passed"])
            manifest.record_quality_gate("coverage_threshold_met", final_validation["coverage_threshold_met"])
            manifest.record_quality_gate("no_critical_failures", final_validation["no_critical_failures"])

            manifest.complete(success=final_validation["all_passed"] and final_validation["coverage_threshold_met"])
            manifest.save(manifest_path)

            logger.info("Testing complete")
            logger.info(f"Manifest saved to: {manifest_path}")

            # Record history
            history_path = workspace_root / ".spectra" / "history" / "test-history.yaml"
            history_path.parent.mkdir(parents=True, exist_ok=True)
            self.record_history(
                history=history,
                decision=llm_response,
                outcome="success" if final_validation["all_passed"] else "partial",
                result=ActivityResult(
                    activity_name="test",
                    success=final_validation["all_passed"],
                    outputs=outputs,
                    errors=actual_test_results["failures"],
                ),
                context=activity_context,
            )
            history.save(history_path)
            logger.debug(f"History saved to: {history_path}")

            return ActivityResult(
                activity_name="test",
                success=final_validation["all_passed"],
                outputs=outputs,
                errors=actual_test_results["failures"],
            )

        except Exception as e:
            logger.error(f"Test activity failed: {e}", exc_info=True)
            return ActivityResult(
                activity_name="test",
                success=False,
                outputs={},
                errors=[str(e)],
            )

    def format_prompt(self, context: Dict, history: Optional[list] = None) -> str:
        """
        Format system prompt for test activity.

        Args:
            context: Context dictionary
            history: Optional history entries

        Returns:
            Formatted system prompt
        """
        prompt_parts = [
            "You are a SPECTRA Test Engineer - an expert in test execution and quality validation.",
            "",
            "YOUR MISSION:",
            "Execute tests and validate quality following SPECTRA testing standards.",
            "",
            "SPECTRA TESTING STANDARDS:",
            "- pytest: Primary test framework",
            "- Coverage threshold: Minimum 80% code coverage",
            "- Test organization: tests/ directory mirroring src/ structure",
            "- TDD/BDD: Test-driven development for critical features",
            "",
            "TESTING PRINCIPLES:",
            "- Comprehensive test coverage (unit, integration, e2e)",
            "- Fast feedback loops",
            "- Clear test organization",
            "- Meaningful test assertions",
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
            "Respond in JSON format with test_strategy, test_suites, test_results, and validation fields.",
        ])

        return "\n".join(prompt_parts)
