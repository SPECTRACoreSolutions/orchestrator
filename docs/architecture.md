# Orchestrator Architecture

**Status**: Draft  
**Last Updated**: 2026-01-06

## System Overview

The Orchestrator is an AI-agent-based orchestration system that replaces solution-engine. Activities are AI agents that use LLM (configurable, OpenAI-compatible API) to make autonomous decisions.

## Core Concepts

### Activities

Activities are AI agents that:
- Use LLM to make decisions (not hardcoded logic)
- Load context (specification, manifest, tools, history)
- Format prompts with injected context
- Call LLM for decision-making
- Execute playbooks/tools based on LLM decisions
- Update manifest with results
- Record history for self-learning

### Specification

User's goal/requirements (adapted from solution-engine covenant system). Single source of truth for what needs to be built.

### Manifest

Activity execution results (simplified, activity-specific). Records what was actually done.

### Playbook Registry

Registry-driven playbook discovery. `operations/playbooks/playbooks-registry.yaml` is the single source of truth.

## Data Flow

```
User Input
    ↓
Orchestrator.run()
    ↓
Activity.execute()
    ├── Load Context (Specification, Manifest, Tools, History)
    ├── Format Prompt
    ├── Call LLM
    ├── Parse Response
    ├── Execute Playbooks
    ├── Update Manifest
    └── Record History
```

## Components

See individual documentation:
- `docs/activities.md` - Activity system
- `docs/playbooks.md` - Playbook registry
- `docs/history.md` - Self-learning system

