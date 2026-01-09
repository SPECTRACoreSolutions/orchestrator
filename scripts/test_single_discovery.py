#!/usr/bin/env python3
"""Quick test of a single discovery to debug the 400 error."""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orchestrator.orchestrator import Orchestrator
from orchestrator.activity import ActivityContext


async def test():
    orchestrator = Orchestrator(workspace_root=Path(__file__).parent.parent.parent)
    ctx = ActivityContext(
        activity_name="discover",
        user_input="build a portal website",
        service_name="portal"
    )
    
    print("Running discovery...")
    result = await orchestrator.run_activity("discover", ctx)
    
    print(f"\nSuccess: {result.success}")
    print(f"Errors: {result.errors}")
    if result.outputs:
        print(f"\nOutputs: {list(result.outputs.keys())}")


if __name__ == "__main__":
    asyncio.run(test())

