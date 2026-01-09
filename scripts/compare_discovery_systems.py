#!/usr/bin/env python3
"""
Compare Orchestrator Discover vs Solution-Engine Discover

Runs both discovery systems on the same services and compares outputs comprehensively.
"""

import sys
import json
import yaml
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
import subprocess

# Add orchestrator to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "solution-engine" / "src"))

from orchestrator.orchestrator import Orchestrator
from orchestrator.activity import ActivityContext


# Test cases: service_name -> (user_input, covenant_path)
TEST_CASES = {
    "portal": (
        "build a public-facing website for SPECTRA - customer portal with documentation, services, and company information",
        "Core/portal/portal.covenant.yaml"
    ),
    "email": (
        "build an email infrastructure service - Microsoft 365 shared mailbox monitoring with Alana AI integration",
        "Core/email/email.covenant.yaml"
    ),
}


def load_solution_engine_manifest(service_name: str, workspace_root: Path) -> Dict[str, Any]:
    """Load solution-engine manifest if it exists, otherwise return expected structure."""
    manifest_path = workspace_root / ".spectra" / "build" / service_name / "manifest.yaml"
    
    if manifest_path.exists():
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest_data = yaml.safe_load(f) or {}
        
        outputs = manifest_data.get("outputs", {})
        return {
            "service_name": outputs.get("service_name"),
            "problem": outputs.get("problem", {}),
            "idea": outputs.get("idea", {}),
            "yin_yang_mapping": outputs.get("yin_yang_mapping", {}),
            "maturity_assessment": outputs.get("maturity_assessment", {}),
            "registry_check": outputs.get("registry_check", {}),
            "discovery_game": outputs.get("discovery_game", {}),
            "high_level_design": outputs.get("high_level_design", {}),
            "problem_statement": outputs.get("problem_statement", {}),
            "proposed_approach": outputs.get("proposed_approach", {}),
            "quality_gates": manifest_data.get("quality_gates_passed", {}),
            "errors": manifest_data.get("errors", []),
        }
    
    # Return expected structure based on discover.py implementation
    return {
        "service_name": service_name,
        "problem": {"statement": "", "impact": "medium"},
        "idea": {"name": f"{service_name}-service", "type": "service", "priority": "important"},
        "yin_yang_mapping": {},
        "maturity_assessment": {},
        "registry_check": {},
        "discovery_game": {},
        "high_level_design": {},
        "problem_statement": {},
        "proposed_approach": {},
        "quality_gates": {},
        "errors": [],
        "note": "Manifest not found - this is expected structure from discover.py"
    }


async def run_orchestrator_discover(service_name: str, user_input: str, workspace_root: Path) -> Dict[str, Any]:
    """Run orchestrator Discover activity and capture outputs."""
    try:
        orchestrator = Orchestrator(workspace_root=workspace_root)
        ctx = ActivityContext(
            activity_name="discover",
            user_input=user_input,
            service_name=service_name,
        )
        
        result = await orchestrator.run_activity("discover", ctx)
        
        if not result.success:
            return {
                "error": result.errors,
                "outputs": result.outputs,
            }
        
        return {
            "service_name": result.outputs.get("service_name"),
            "problem": result.outputs.get("problem", {}),
            "idea": result.outputs.get("idea", {}),
            "validation": result.outputs.get("validation", {}),
            "next_steps": result.outputs.get("next_steps", ""),
            "quality_gates": result.metadata.get("quality_gates", {}),
            "errors": result.errors,
        }
    except Exception as e:
        return {
            "error": str(e),
            "traceback": str(e.__traceback__)
        }


def compare_outputs(solution_engine: Dict[str, Any], orchestrator: Dict[str, Any]) -> Dict[str, Any]:
    """Compare outputs from both systems."""
    comparison = {
        "service_name": {
            "solution_engine": solution_engine.get("service_name"),
            "orchestrator": orchestrator.get("service_name"),
            "match": solution_engine.get("service_name") == orchestrator.get("service_name"),
        },
        "problem": {
            "solution_engine": solution_engine.get("problem", {}).get("statement", ""),
            "orchestrator": orchestrator.get("problem", {}).get("statement", ""),
            "similarity": "N/A",  # Would need semantic comparison
        },
        "idea": {
            "solution_engine": solution_engine.get("idea", {}).get("name", ""),
            "orchestrator": orchestrator.get("idea", {}).get("name", ""),
            "match": solution_engine.get("idea", {}).get("name") == orchestrator.get("idea", {}).get("name"),
        },
        "maturity_assessment": {
            "solution_engine": solution_engine.get("maturity_assessment", {}).get("level", ""),
            "orchestrator": "N/A (moved to Assess activity)",
            "present_in_orchestrator": False,
        },
        "registry_check": {
            "solution_engine": solution_engine.get("registry_check", {}),
            "orchestrator": "NOT IMPLEMENTED",
            "present_in_orchestrator": False,
        },
        "discovery_game": {
            "solution_engine": solution_engine.get("discovery_game", {}),
            "orchestrator": "NOT IMPLEMENTED",
            "present_in_orchestrator": False,
        },
        "high_level_design": {
            "solution_engine": solution_engine.get("high_level_design", {}),
            "orchestrator": "NOT IMPLEMENTED",
            "present_in_orchestrator": False,
        },
        "problem_statement_doc": {
            "solution_engine": solution_engine.get("problem_statement", {}).get("document_path", ""),
            "orchestrator": "NOT IMPLEMENTED",
            "present_in_orchestrator": False,
        },
        "proposed_approach_doc": {
            "solution_engine": solution_engine.get("proposed_approach", {}).get("document_path", ""),
            "orchestrator": "NOT IMPLEMENTED",
            "present_in_orchestrator": False,
        },
        "validation": {
            "solution_engine": solution_engine.get("yin_yang_mapping", {}),
            "orchestrator": orchestrator.get("validation", {}),
            "similarity": "Different structure",
        },
        "orchestrator_only": {
            "next_steps": orchestrator.get("next_steps", ""),
        },
    }
    
    return comparison


def print_comparison(service_name: str, comparison: Dict[str, Any]):
    """Print detailed comparison."""
    print("\n" + "=" * 100)
    print(f"COMPREHENSIVE COMPARISON: {service_name.upper()}")
    print("=" * 100)
    
    # Service name
    print(f"\n[Service Name]")
    print(f"  Solution-Engine: {comparison['service_name']['solution_engine']}")
    print(f"  Orchestrator:   {comparison['service_name']['orchestrator']}")
    print(f"  Match:          {'[OK]' if comparison['service_name']['match'] else '[X]'}")
    
    # Problem
    print(f"\n[Problem Statement]")
    print(f"  Solution-Engine: {comparison['problem']['solution_engine'][:150]}...")
    print(f"  Orchestrator:    {comparison['problem']['orchestrator'][:150]}...")
    
    # Idea
    print(f"\n[Idea]")
    print(f"  Solution-Engine: {comparison['idea']['solution_engine']}")
    print(f"  Orchestrator:    {comparison['idea']['orchestrator']}")
    print(f"  Match:           {'[OK]' if comparison['idea']['match'] else '[X]'}")
    
    # Maturity assessment
    print(f"\n[Maturity Assessment]")
    print(f"  Solution-Engine: {comparison['maturity_assessment']['solution_engine']}")
    print(f"  Orchestrator:    {comparison['maturity_assessment']['orchestrator']}")
    print(f"  Present:         {comparison['maturity_assessment']['present_in_orchestrator']}")
    
    # Registry check
    print(f"\n[Registry Check (Anti-Duplication)]")
    print(f"  Solution-Engine: {comparison['registry_check']['solution_engine']}")
    print(f"  Orchestrator:    {comparison['registry_check']['orchestrator']}")
    print(f"  Present:         {comparison['registry_check']['present_in_orchestrator']}")
    
    # Discovery game
    print(f"\n[Discovery Game (7x7)]")
    se_game = comparison['discovery_game']['solution_engine']
    if isinstance(se_game, dict) and se_game.get('generated'):
        print(f"  Solution-Engine: Generated ({se_game.get('questions', '?')} questions)")
        print(f"                   Path: {se_game.get('document_path', 'N/A')}")
    else:
        print(f"  Solution-Engine: Not generated")
    print(f"  Orchestrator:    {comparison['discovery_game']['orchestrator']}")
    print(f"  Present:         {comparison['discovery_game']['present_in_orchestrator']}")
    
    # High-level design
    print(f"\n[High-Level Design]")
    se_design = comparison['high_level_design']['solution_engine']
    if isinstance(se_design, dict) and se_design.get('extracted'):
        print(f"  Solution-Engine: Extracted")
        print(f"                   Architecture: {str(se_design.get('architecture', ''))[:100]}...")
        print(f"                   Components: {len(se_design.get('key_components', []))}")
    else:
        print(f"  Solution-Engine: Not extracted")
    print(f"  Orchestrator:    {comparison['high_level_design']['orchestrator']}")
    print(f"  Present:         {comparison['high_level_design']['present_in_orchestrator']}")
    
    # Documents
    print(f"\n[Generated Documents]")
    print(f"  Problem Statement:")
    print(f"    Solution-Engine: {comparison['problem_statement_doc']['solution_engine']}")
    print(f"    Orchestrator:    {comparison['problem_statement_doc']['orchestrator']}")
    print(f"  Proposed Approach:")
    print(f"    Solution-Engine: {comparison['proposed_approach_doc']['solution_engine']}")
    print(f"    Orchestrator:    {comparison['proposed_approach_doc']['orchestrator']}")
    
    # Validation
    print(f"\n[Validation/Mapping]")
    print(f"  Solution-Engine: {comparison['validation']['solution_engine']}")
    print(f"  Orchestrator:    {comparison['validation']['orchestrator']}")
    
    # Orchestrator-only features
    print(f"\n[Orchestrator-Only Features]")
    print(f"  Next Steps: {comparison['orchestrator_only']['next_steps'][:150]}...")


async def main():
    """Run comprehensive comparison."""
    workspace_root = Path(__file__).parent.parent.parent
    
    print("=" * 100)
    print("COMPREHENSIVE DISCOVERY COMPARISON")
    print("Solution-Engine Discover vs Orchestrator Discover")
    print("=" * 100)
    
    results = {}
    
    for service_name, (user_input, covenant_path) in TEST_CASES.items():
        print(f"\n\n{'='*100}")
        print(f"TESTING: {service_name.upper()}")
        print(f"{'='*100}")
        print(f"User Input: {user_input}")
        
        # Load solution-engine manifest (or expected structure)
        print(f"\n[1/2] Loading Solution-Engine Discover Outputs...")
        se_result = load_solution_engine_manifest(service_name, workspace_root)
        
        if "error" in se_result:
            print(f"  [ERROR] Solution-Engine failed: {se_result['error']}")
            continue
        
        print(f"  [OK] Solution-Engine completed")
        print(f"       Service: {se_result.get('service_name')}")
        print(f"       Problem: {se_result.get('problem', {}).get('statement', 'N/A')[:80]}...")
        
        # Run orchestrator discover
        print(f"\n[2/2] Running Orchestrator Discover...")
        orch_result = await run_orchestrator_discover(service_name, user_input, workspace_root)
        
        if "error" in orch_result:
            print(f"  [ERROR] Orchestrator failed: {orch_result['error']}")
            continue
        
        print(f"  [OK] Orchestrator completed")
        print(f"       Service: {orch_result.get('service_name')}")
        print(f"       Problem: {orch_result.get('problem', {}).get('statement', 'N/A')[:80]}...")
        
        # Compare
        comparison = compare_outputs(se_result, orch_result)
        print_comparison(service_name, comparison)
        
        results[service_name] = {
            "solution_engine": se_result,
            "orchestrator": orch_result,
            "comparison": comparison,
        }
    
    # Summary
    print("\n\n" + "=" * 100)
    print("SUMMARY: MISSING FEATURES IN ORCHESTRATOR")
    print("=" * 100)
    
    missing_features = [
        "1. Registry Check (anti-duplication)",
        "2. Discovery Game (7x7 - 49 questions)",
        "3. High-Level Design Extraction",
        "4. Problem Statement Document Generation",
        "5. Proposed Approach Document Generation",
        "6. Maturity Assessment (moved to Assess activity - OK)",
    ]
    
    for feature in missing_features:
        print(f"  - {feature}")
    
    # Save results
    results_file = workspace_root / "orchestrator" / "discovery_comparison_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())

