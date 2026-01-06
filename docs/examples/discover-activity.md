# Discover Activity Example

**Status**: Draft  
**Last Updated**: 2026-01-06

## Example

Running discovery on logging service idea:

```bash
orchestrator discover "build a logging service for SPECTRA - we need centralized observability"
```

## What Happens

1. DiscoverActivity loads context (user input, specification, tools, history)
2. Formats prompt with context
3. Calls LLM for analysis
4. LLM returns: service_name, problem, idea, maturity_assessment
5. Activity updates manifest with results
6. Records history for future learning

## Output

Manifest updated with discovery results:
- Service name: "logging"
- Problem statement
- Idea validation
- Maturity assessment (L3-Operational)

