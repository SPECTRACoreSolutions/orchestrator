# Activity Development Guide

**Status**: Draft  
**Last Updated**: 2026-01-06

## Overview

Activities are AI agents that use LLM to make autonomous decisions. Each activity extends the `Activity` base class and implements the `execute()` method.

## Creating an Activity

1. Create activity file in `src/orchestrator/activities/`
2. Extend `Activity` base class
3. Implement `execute()` method
4. Use context injection for prompts
5. Execute playbooks based on LLM decisions

## Activity Base Class

```python
from orchestrator.activity import Activity

class MyActivity(Activity):
    async def execute(self, context: ActivityContext) -> ActivityResult:
        # Load context (specification, manifest, tools, history)
        # Format prompt with context
        # Call LLM
        # Parse response
        # Execute playbooks
        # Update manifest
        # Record history
        pass
```

## Context Injection

Activities receive context:
- Specification (user's goals/requirements)
- Manifest (current state/outputs)
- Tools (available playbooks)
- History (past decisions/outcomes)

## Testing Activities

See `tests/test_discover_activity.py` for example.

