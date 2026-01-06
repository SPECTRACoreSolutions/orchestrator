# Orchestrator API

**Status**: Draft  
**Last Updated**: 2026-01-06

## Overview

API documentation for Orchestrator classes and methods.

## Orchestrator Class

Main orchestrator class for running activities.

```python
from orchestrator import Orchestrator

orchestrator = Orchestrator()
result = await orchestrator.run(user_input="build logging service")
```

## Activity Classes

See `docs/activities.md` for activity development.

