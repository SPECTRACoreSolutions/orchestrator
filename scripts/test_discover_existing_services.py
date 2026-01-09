#!/usr/bin/env python3
"""
Test Discover Activity against existing SPECTRA services.

This script:
1. Loads existing covenant files from real SPECTRA services
2. Runs discovery on them as if they were new ideas
3. Compares Alana's discovery output with actual service definitions
4. Reports accuracy and differences
"""

import sys
import json
import yaml
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add orchestrator to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orchestrator.orchestrator import Orchestrator
from orchestrator.activity import ActivityContext
from orchestrator.state import Specification, Manifest


# Test cases: service name -> (user_input, covenant_path)
TEST_CASES = {
    "portal": (
        "build a public-facing website for SPECTRA - customer portal with documentation, services, and company information",
        "Core/portal/portal.covenant.yaml"
    ),
    "email": (
        "build an email infrastructure service - Microsoft 365 shared mailbox monitoring with Alana AI integration",
        "Core/email/email.covenant.yaml"
    ),
    "graph": (
        "build a central nervous system - workspace intelligence graph with GraphQL API for SPECTRA",
        "Core/graph/graph.covenant.yaml"
    ),
    "assistant": (
        "build a production-grade containerized development environment for persona-based remote development - cloud-based, always-on AI development environment",
        "Core/assistant/README.md"  # No covenant, will need to extract from README
    )
}


def load_covenant(covenant_path: Path) -> Dict[str, Any]:
    """Load covenant YAML file."""
    if not covenant_path.exists():
        return {}
    
    with open(covenant_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def extract_from_readme(readme_path: Path) -> Dict[str, Any]:
    """Extract service information from README."""
    if not readme_path.exists():
        return {}
    
    content = readme_path.read_text(encoding='utf-8')
    
    # Extract purpose (usually after "## Purpose" or "# Purpose")
    purpose = None
    if "## Purpose" in content:
        purpose_section = content.split("## Purpose")[1].split("\n##")[0]
        # Get first paragraph
        purpose = purpose_section.strip().split("\n\n")[0].strip()
    elif "# Purpose" in content:
        purpose_section = content.split("# Purpose")[1].split("\n#")[0]
        purpose = purpose_section.strip().split("\n\n")[0].strip()
    
    return {
        "service": "assistant",
        "purpose": purpose or "Production-grade containerized development environment for persona-based remote development",
        "maturity": None  # Not specified in README
    }


def normalize_service_name(name: str) -> str:
    """Normalize service name for comparison."""
    return name.lower().strip().replace("_", "-")


def compare_discovery(discovery_result: Dict[str, Any], actual_covenant: Dict[str, Any], service_name: str) -> Dict[str, Any]:
    """Compare discovery result with actual covenant."""
    comparison = {
        "service_name": {
            "discovered": discovery_result.get("service_name", ""),
            "actual": actual_covenant.get("service", service_name),
            "match": normalize_service_name(discovery_result.get("service_name", "")) == normalize_service_name(actual_covenant.get("service", service_name))
        },
        "problem": {
            "discovered": discovery_result.get("problem", {}).get("statement", ""),
            "actual": actual_covenant.get("problem", {}).get("statement", "Not specified in covenant"),
            "match": None  # Subjective comparison
        },
        "purpose": {
            "discovered": discovery_result.get("idea", {}).get("description", ""),
            "actual": actual_covenant.get("purpose", "Not specified"),
            "match": None  # Subjective comparison
        },
        "maturity": {
            "discovered": discovery_result.get("maturity_assessment", {}).get("level", ""),
            "actual": actual_covenant.get("maturity", "Not specified"),
            "match": discovery_result.get("maturity_assessment", {}).get("level", "").upper() == str(actual_covenant.get("maturity", "")).upper() if actual_covenant.get("maturity") else None
        },
        "validation": {
            "discovered": discovery_result.get("validation", {}).get("problem_solved", None),
            "actual": "N/A",  # Not in covenant
            "match": None
        }
    }
    
    return comparison


def print_comparison(service_name: str, comparison: Dict[str, Any], discovery_result: Dict[str, Any]):
    """Print comparison results."""
    print("\n" + "=" * 80)
    print(f"COMPARISON: {service_name.upper()}")
    print("=" * 80)
    
    # Service name
    print(f"\n[Service Name]")
    print(f"  Discovered: {comparison['service_name']['discovered']}")
    print(f"  Actual:     {comparison['service_name']['actual']}")
    print(f"  Match:      {'[OK]' if comparison['service_name']['match'] else '[X]'}")
    
    # Problem
    print(f"\n[Problem Statement]")
    print(f"  Discovered: {comparison['problem']['discovered'][:100]}...")
    print(f"  Actual:     {comparison['problem']['actual'][:100]}...")
    
    # Purpose/Idea
    print(f"\n[Purpose/Idea]")
    print(f"  Discovered: {comparison['purpose']['discovered'][:100]}...")
    print(f"  Actual:     {comparison['purpose']['actual'][:100]}...")
    
    # Maturity
    print(f"\n[Maturity]")
    print(f"  Discovered: {comparison['maturity']['discovered']}")
    print(f"  Actual:     {comparison['maturity']['actual']}")
    if comparison['maturity']['match'] is not None:
        print(f"  Match:      {'✓' if comparison['maturity']['match'] else '✗'}")
    
    # Validation
    print(f"\n[Validation]")
    print(f"  Problem Solved: {discovery_result.get('validation', {}).get('problem_solved', 'N/A')}")
    print(f"  Reasoning:      {discovery_result.get('validation', {}).get('reasoning', 'N/A')[:100]}...")
    
    # Next steps
    print(f"\n[Next Steps]")
    print(f"  {discovery_result.get('next_steps', 'N/A')[:150]}...")


async def test_service_discovery(service_name: str, user_input: str, covenant_path: str, workspace_root: Path) -> Tuple[bool, Dict[str, Any], Dict[str, Any]]:
    """Run discovery on a service and compare with actual covenant."""
    print("\n" + "=" * 80)
    print(f"TESTING: {service_name.upper()}")
    print("=" * 80)
    print(f"User Input: {user_input}")
    print(f"Covenant: {covenant_path}")
    
    # Load actual covenant
    covenant_file = workspace_root / covenant_path
    if covenant_file.suffix == ".yaml":
        actual_covenant = load_covenant(covenant_file)
    else:
        actual_covenant = extract_from_readme(covenant_file)
    
    # Run discovery
    try:
        orchestrator = Orchestrator(workspace_root=workspace_root)
        
        # Create activity context
        context = ActivityContext(
            activity_name="discover",
            service_name=service_name,
            user_input=user_input,
        )
        
        # Run discovery
        result = await orchestrator.run_activity("discover", context)
        
        if not result.success:
            print(f"\n[ERROR] Discovery failed: {result.errors}")
            return False, {}, {}
        
        # Extract discovery result from activity outputs
        discovery_result = {
            "service_name": result.outputs.get("service_name", ""),
            "problem": result.outputs.get("problem", {}),
            "idea": result.outputs.get("idea", {}),
            "validation": result.outputs.get("validation", {}),
            "maturity_assessment": result.outputs.get("maturity_assessment", {}),
            "next_steps": result.outputs.get("next_steps", "")
        }
        
        # Compare
        comparison = compare_discovery(discovery_result, actual_covenant, service_name)
        
        # Print results
        print_comparison(service_name, comparison, discovery_result)
        
        return True, discovery_result, comparison
        
    except Exception as e:
        print(f"\n[ERROR] Discovery failed: {e}")
        import traceback
        traceback.print_exc()
        return False, {}, {}


async def main_async():
    """Run discovery tests on existing services (async)."""
    # Get workspace root (go up from scripts/ -> orchestrator/ -> Core/)
    workspace_root = Path(__file__).parent.parent.parent
    
    print("=" * 80)
    print("DISCOVERY ACTIVITY VALIDATION TEST")
    print("Testing Discover activity against existing SPECTRA services")
    print("=" * 80)
    
    results = {}
    summary = {
        "total": len(TEST_CASES),
        "passed": 0,
        "failed": 0,
        "service_name_matches": 0,
        "maturity_matches": 0
    }
    
    for service_name, (user_input, covenant_path) in TEST_CASES.items():
        success, discovery_result, comparison = await test_service_discovery(
            service_name, user_input, covenant_path, workspace_root
        )
        
        results[service_name] = {
            "success": success,
            "discovery": discovery_result,
            "comparison": comparison
        }
        
        if success:
            summary["passed"] += 1
            if comparison.get("service_name", {}).get("match"):
                summary["service_name_matches"] += 1
            if comparison.get("maturity", {}).get("match"):
                summary["maturity_matches"] += 1
        else:
            summary["failed"] += 1
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total services tested: {summary['total']}")
    print(f"Discovery successful: {summary['passed']}")
    print(f"Discovery failed: {summary['failed']}")
    print(f"Service name matches: {summary['service_name_matches']}/{summary['passed']}")
    print(f"Maturity matches: {summary['maturity_matches']}/{summary['passed']}")
    
    # Save results (workspace_root is already Core/, so orchestrator is Core/orchestrator)
    results_file = workspace_root / "orchestrator" / "test_discovery_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            "summary": summary,
            "results": results
        }, f, indent=2, default=str)
    
    print(f"\nResults saved to: {results_file}")
    
    return 0 if summary["failed"] == 0 else 1


def main():
    """Run discovery tests on existing services."""
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())

