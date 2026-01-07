# Activity History & Self-Learning

**Status**: Draft  
**Last Updated**: 2026-01-06

## Overview

Each activity maintains history of past executions, enabling self-learning and pattern recognition.

## History System

- Stored per-activity (e.g., `.spectra/history/discover-history.yaml`)
- Records: decisions made, context used, outcomes (success/failure), results
- Used as context for future decisions (LLM learns from past)
- Enables self-improvement and pattern recognition

## History Format

```yaml
entries:
  - timestamp: "2026-01-06T12:00:00Z"
    decision: {...}
    context: {...}
    outcome: "success"
    result: {...}
```

## Learning Pattern

LLM sees history in context: "In similar situations, X worked well, Y failed"


