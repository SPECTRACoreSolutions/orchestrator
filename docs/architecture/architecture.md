# Orchestrator Architecture

**Status**: In Progress  
**Last Updated**: 2026-01-06  
**Version**: 0.1.0

---

## Executive Summary

The SPECTRA Orchestrator is an AI-agent-based orchestration system that replaces solution-engine with a more flexible, autonomous architecture. Activities (AI agents) use LLM (configurable, OpenAI-compatible API) to make autonomous decisions, dynamically orchestrating playbooks and tools to achieve goals.

**Key Capabilities:**
- Autonomous decision-making via LLM agents
- Dynamic playbook orchestration
- Context-aware execution (specification, manifest, history)
- Self-learning through activity history
- Flexible, composable activity architecture

**Business Value:**
- Reduces hardcoded logic and brittleness
- Enables autonomous adaptation to new technologies
- Supports "company as code" with LLM-agnostic design
- Improves maintainability through separation of concerns

---

## Architecture Principles

### SPECTRA-Grade Compliance

- **Sacred Geometry Alignment**: Aligns with SPECTRA's 7-pillar structure
- **Registry-Driven**: Playbook registry as single source of truth
- **Reversible**: Audit trail, idempotency, undo capability
- **Observable**: Structured logging, metrics, tracing
- **Testable**: TDD approach, comprehensive test coverage
- **Documented**: Comprehensive Markdown documentation (British English)
- **Code-Based**: Python, version-controlled, Git-native

### Core Design Principles

- **AI-Agent Architecture**: Activities are AI agents, not hardcoded logic
- **LLM-Agnostic**: Works with any OpenAI-compatible API (local LLM, OpenAI, Anthropic, etc.)
- **Context Injection**: All context (specification, manifest, tools, history) injected into prompts
- **Playbook-Based**: Activities orchestrate playbooks/tools, don't execute directly
- **Self-Learning**: Activity history enables pattern recognition and improvement
- **Composable**: Activities can be invoked independently or composed into pipelines
- **Local Execution**: Activities run in-process (not deployed services)

---

## System Context

### External Dependencies

```
┌─────────────────────────────────────────────────────────┐
│                  SPECTRA Orchestrator                    │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   User CLI   │  │  LLM Service │  │   Playbooks  │ │
│  │   (click)    │  │ (local/API)  │  │  (registry)  │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                  │                  │         │
│         └──────────────────┼──────────────────┘         │
│                            │                            │
│  ┌─────────────────────────▼─────────────────────────┐ │
│  │            Orchestrator Core                      │ │
│  │  • Activity Framework                             │ │
│  │  • Context Builder                                │ │
│  │  • State Management                               │ │
│  │  • Playbook Registry                              │ │
│  └───────────────────────────────────────────────────┘ │
│                            │                            │
│  ┌─────────────────────────▼─────────────────────────┐ │
│  │         Workspace File System                     │ │
│  │  • Specifications (YAML)                          │ │
│  │  • Manifests (YAML)                               │ │
│  │  • History (YAML)                                 │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Boundaries

- **In Scope**: Orchestration, activity execution, context management, playbook discovery
- **Out of Scope**: Playbook implementation (in `operations/playbooks/`), LLM service itself, deployment infrastructure

---

## High-Level Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Orchestrator                            │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Orchestrator │  │   Activity   │  │   Activity   │     │
│  │    Class     │──│  Framework   │──│   Registry   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                  │                  │             │
│         │                  │                  │             │
│  ┌──────▼──────────────────▼──────────────────▼──────────┐ │
│  │         Activities (AI Agents)                        │ │
│  │  • Discover                                            │ │
│  │  • Assess (planned)                                   │ │
│  │  • Build (planned)                                    │ │
│  │  • Test (planned)                                     │ │
│  │  • Deploy (planned)                                   │ │
│  └───────────────────────────────────────────────────────┘ │
│         │                  │                  │             │
│  ┌──────▼──────────────────▼──────────────────▼──────────┐ │
│  │         Core Services                                 │ │
│  │  • LLMClient (OpenAI-compatible)                      │ │
│  │  • ContextBuilder                                     │ │
│  │  • PlaybookRegistry                                   │ │
│  │  • StateManager (Specification/Manifest/History)      │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Input
    ↓
Orchestrator.run()
    ↓
Activity Selection (determine_activities)
    ↓
For each Activity:
    ├── Activity.execute()
    │   ├── Load Context (Specification, Manifest, Tools, History)
    │   ├── Format Prompt (with context injection)
    │   ├── Call LLM (chat_completion)
    │   ├── Parse Response (JSON decisions)
    │   ├── Execute Playbooks (based on LLM decisions)
    │   ├── Update Manifest (with outputs)
    │   └── Record History (decision, outcome, result)
    ↓
OrchestrationResult
```

---

## Technology Stack

### Core Technologies

- **Language**: Python 3.11+
- **HTTP Client**: httpx (async, for LLM API calls)
- **CLI Framework**: Click
- **Data Format**: YAML (for specifications, manifests, history)
- **Package Manager**: setuptools, pyproject.toml

### Dependencies

```
orchestrator/
├── pyyaml>=6.0          # YAML parsing
├── click>=8.1.0          # CLI interface
└── httpx>=0.25.0         # HTTP client (LLM API)
```

### Development Dependencies

```
dev/
├── pytest>=7.4.0         # Testing framework
├── pytest-cov>=4.1.0     # Coverage reporting
├── black>=23.0.0          # Code formatting
└── ruff>=0.1.0            # Linting
```

---

## Deployment Architecture

### Runtime Environment

- **Execution Model**: Local, in-process Python application
- **Installation**: `pip install -e .` (editable install)
- **Entry Point**: `orchestrator` CLI command
- **Configuration**: Environment variables (LLM URL, API key, model)

### Configuration

```bash
# LLM Configuration (optional - defaults to local LLM)
export ORCHESTRATOR_LLM_URL="http://localhost:8001/v1/chat/completions"
export ORCHESTRATOR_LLM_API_KEY="token-irrelevant"
export ORCHESTRATOR_LLM_MODEL="mistralai/Mistral-7B-Instruct-v0.3"
```

### Workspace Structure

```
.spectra/
├── manifests/
│   └── {activity}-manifest.yaml
├── history/
│   └── {activity}-history.yaml
└── {service}.specification.yaml
```

---

## Key Design Decisions

See [Architecture Decision Records](decisions/) for detailed rationale:

1. **ADR-001**: AI-Agent Architecture (activities use LLM, not hardcoded logic)
2. **ADR-002**: LLM-Agnostic Design (OpenAI-compatible API)
3. **ADR-003**: Local In-Process Execution (not deployed services)
4. **ADR-004**: Context Injection Pattern (specification + manifest + tools + history → prompt)
5. **ADR-005**: Separate Assess Activity (maturity assessment extracted from Discover)
6. **ADR-006**: Registry-Driven Playbooks (YAML registry as single source of truth)
7. **ADR-007**: Self-Learning via History (activity history enables pattern recognition)

---

## Security Architecture

### Input Validation

- Service name validation (mononymic, kebab-case, no action verbs)
- LLM response parsing with error handling
- Playbook execution isolation (subprocess)

### Prompt Injection Mitigation

- Structured prompt formatting (system/user message separation)
- Context sanitization (YAML validation)
- LLM response validation (JSON schema validation planned)

### Data Protection

- Local file system (no cloud storage)
- Version-controlled artifacts (Git)
- Audit trail (manifest records all changes)

---

## Scalability & Performance

### Current Limitations

- Single-threaded execution (Python asyncio)
- Sequential activity execution (no parallelization yet)
- LLM API latency (network calls to LLM service)

### Optimization Strategies

- Async I/O for LLM calls (httpx async)
- Context caching (future: cache loaded specifications/manifests)
- Batch playbook execution (future: parallel playbook execution)

---

## Reliability & Resilience

### Error Handling

- Activity-level error isolation (one activity failure doesn't stop others)
- LLM retry logic (planned)
- Playbook execution error handling (subprocess error capture)

### Idempotency

- Manifest-based state tracking (can re-run activities safely)
- Idempotent playbooks (playbook responsibility)
- Reversible operations (manifest audit trail)

### Recovery

- Manifest records all changes (audit trail)
- History enables learning from failures
- Manual intervention supported (activities can be re-run)

---

## Observability

### Logging

- Structured logging (Python logging module)
- Log levels: DEBUG, INFO, WARNING, ERROR
- Activity execution logging (start, end, duration, outcomes)
- LLM request/response logging (prompt length, tokens, latency)

### Metrics (Planned)

- Activity success rate
- LLM latency (p50, p95, p99)
- Playbook execution time
- Error rates by activity

### Tracing (Planned)

- Correlation IDs for activity execution
- Request tracing through LLM calls
- Playbook execution tracing

---

## Evolution

### Migration from solution-engine

- **Coexistence**: Both systems can exist simultaneously
- **Gradual Migration**: Activities can be migrated one at a time
- **Data Compatibility**: Specification adapted from covenant, Manifest adapted from solution-engine manifest

### Future Enhancements

- **Additional Activities**: Build, Test, Deploy, Provision activities
- **RAG Integration**: Retrieval-augmented generation for knowledge bases
- **Parallel Execution**: Parallel activity execution where possible
- **Distributed Execution**: Remote activity execution (future)
- **Advanced Self-Learning**: Pattern recognition across activity history

---

## Related Documentation

- [Component Architecture](components.md) - Deep dive into components
- [Data Architecture](data.md) - Data models and flows
- [Activity Architecture](activities.md) - Activity system design
- [Integration Architecture](integrations.md) - External integrations
- [Sequence Diagrams](sequences.md) - Critical workflows
- [Architecture Decision Records](decisions/) - Design rationale
- [Non-Functional Requirements](nfr.md) - Performance, reliability, security

