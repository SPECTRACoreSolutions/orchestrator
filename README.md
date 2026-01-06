# Orchestrator

**Repository**: `SPECTRACoreSolutions/orchestrator` (GitHub)  
**Workspace Path**: `Core/orchestrator/`

SPECTRA Orchestrator - AI-agent-based orchestration system using LLM for autonomous decision-making.

## SPECTRA-Grade Principles

- **Registry-driven**: Playbook registry YAML is single source of truth
- **Reversible**: Audit trail, idempotency, undo capability
- **Observable**: Structured logging, metrics, tracing
- **Testable**: TDD approach, unit/integration tests, coverage requirements
- **Documented**: Comprehensive Markdown documentation (British English)
- **Code-based**: Python, version-controlled

## Architecture Overview

The Orchestrator replaces solution-engine with an AI-agent-based architecture:

```
User Input
    ↓
Orchestrator
    ↓
Activity.execute() [AI Agent]
    ├── Load Context (Specification, Manifest, Tools, History)
    ├── Format Prompt with Context + History
    ├── Call LLM (OpenAI-compatible API)
    ├── Parse Response (JSON decisions)
    ├── Execute Playbooks/Tools
    ├── Update Manifest
    └── Record History (decision, outcome, result)
```

**Key Differences from solution-engine:**

- Activities are AI agents (not hardcoded logic)
- LLM makes decisions (not if/else statements)
- Context injection (specification + manifest + tools → prompt)
- Playbook-based execution (activities orchestrate playbooks)
- Dynamic and adaptive (AI chooses approach)
- LLM-agnostic (works with any OpenAI-compatible API)

## Quick Start

### Install

```bash
cd Core/orchestrator
pip install -e .
```

### Configure LLM

Set environment variables (optional - defaults to local LLM):

```bash
export ORCHESTRATOR_LLM_URL="http://localhost:8001/v1/chat/completions"
export ORCHESTRATOR_LLM_API_KEY="token-irrelevant"  # Optional
export ORCHESTRATOR_LLM_MODEL="mistralai/Mistral-7B-Instruct-v0.3"  # Optional
```

### Run

```bash
# Run discovery activity
orchestrator discover "logging service"

# Check status
orchestrator status
```

## Core Components

- **Activities**: AI agents that use LLM to make decisions
- **LLM Client**: Generic OpenAI-compatible HTTP client (configurable)
- **Context Builder**: Loads specification, manifest, tools, history
- **Playbook Registry**: Registry-driven playbook discovery and execution
- **State System**: Specification/Manifest/History (adapted from solution-engine)

## Development

See `docs/` for detailed documentation:

- `docs/architecture.md` - System architecture
- `docs/activities.md` - Activity development guide
- `docs/playbooks.md` - Playbook development guide
- `docs/history.md` - Self-learning/history system
- `docs/api/` - API documentation

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=orchestrator --cov-report=html
```

## Status

**Version**: 0.1.0  
**Status**: Development  
**Milestone**: First Alana LLM response with context injection (2026-01-06)

---

**Created**: 2026-01-06  
**Repository**: SPECTRACoreSolutions/orchestrator

