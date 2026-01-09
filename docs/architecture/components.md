# Component Architecture

**Status**: In Progress  
**Last Updated**: 2026-01-06

---

## Component Overview

The Orchestrator consists of six core components:

1. **Orchestrator Class** - Main orchestration engine
2. **Activity Framework** - Base class and execution model for activities
3. **LLM Client** - OpenAI-compatible API client
4. **Context Builder** - Context loading and formatting
5. **Playbook Registry** - Playbook discovery and execution
6. **State Management** - Specification, Manifest, and History models

---

## 1. Orchestrator Class

### Purpose

Main entry point for orchestration. Manages activity execution, sequencing, and result aggregation.

### Responsibilities

- Activity registration and discovery
- Activity sequencing (determines which activities to run)
- Error aggregation and reporting
- Result collection

### Interface

```python
class Orchestrator:
    async def run(
        user_input: str,
        activities: Optional[List[str]] = None,
        service_name: Optional[str] = None,
    ) -> OrchestrationResult
    
    async def run_activity(
        activity_name: str,
        context: ActivityContext,
    ) -> ActivityResult
    
    def determine_activities(user_input: str) -> List[str]
```

### Design Decisions

- **Activity Registration**: Activities registered in `__init__` (can be extended via plugin system)
- **Sequential Execution**: Activities run sequentially (future: parallel execution)
- **Error Isolation**: One activity failure doesn't stop others (continues with remaining activities)

---

## 2. Activity Framework

### Purpose

Base class and execution model for all activities. Activities are AI agents that use LLM to make autonomous decisions.

### Responsibilities

- Abstract execution interface
- Context loading helpers
- Prompt formatting helpers
- Response parsing helpers
- Playbook execution helpers
- Manifest update helpers
- History recording helpers

### Interface

```python
class Activity(ABC):
    @abstractmethod
    async def execute(context: ActivityContext) -> ActivityResult
    
    def format_prompt(context: Dict, history: Optional[List[Dict]]) -> str
    async def call_llm(system_prompt: str, user_message: str) -> Dict
    async def execute_playbook(name: str, args: Optional[Dict]) -> Dict
    def update_manifest(manifest: Manifest, outputs: Dict)
    def record_history(history: ActivityHistory, decision: Dict, outcome: str, result: ActivityResult)
```

### Execution Model

1. **Load Context**: Specification, Manifest, Tools, History
2. **Format Prompt**: Inject context into system prompt
3. **Call LLM**: Send prompt to LLM, receive JSON response
4. **Parse Response**: Extract decisions from LLM response
5. **Execute Playbooks**: Run playbooks based on LLM decisions
6. **Update Manifest**: Record outputs in manifest
7. **Record History**: Save decision/outcome for self-learning

### Design Decisions

- **Abstract Base Class**: Forces consistent interface across activities
- **Template Methods**: Common operations (format_prompt, call_llm) provided by base class
- **Hook Methods**: Activities override execute() for custom logic
- **Self-Learning**: History recording enables pattern recognition

---

## 3. LLM Client

### Purpose

Generic client for OpenAI-compatible APIs. Supports local LLM (Alana) and cloud APIs (OpenAI, Anthropic via proxy).

### Responsibilities

- HTTP client management (async httpx)
- Chat completion API calls
- Health check functionality
- Error handling and retries

### Interface

```python
class LLMClient:
    def __init__(
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    )
    
    async def chat_completion(
        system_prompt: str,
        user_message: str,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> str
    
    async def health_check() -> bool
```

### Configuration

- **Default URL**: `http://localhost:8001/v1/chat/completions` (local Alana LLM)
- **Configurable**: Via environment variables (`ORCHESTRATOR_LLM_URL`, `ORCHESTRATOR_LLM_API_KEY`, `ORCHESTRATOR_LLM_MODEL`)
- **LLM-Agnostic**: Works with any OpenAI-compatible API

### Design Decisions

- **OpenAI-Compatible**: Uses OpenAI API format for maximum compatibility
- **Async I/O**: httpx async client for non-blocking calls
- **Configurable**: Environment variable configuration for flexibility
- **Health Checks**: Enables service availability checking

---

## 4. Context Builder

### Purpose

Builds context for activity prompts. Loads specification, manifest, tools, and history from workspace.

### Responsibilities

- Workspace root discovery
- Specification loading
- Manifest loading
- Tool/playbook loading
- History loading
- Context dictionary construction

### Interface

```python
class ContextBuilder:
    def __init__(workspace_root: Optional[Path] = None)
    
    def load_specification(service_name: str) -> Optional[Specification]
    def load_manifest(service_name: str, activity_name: str) -> Optional[Manifest]
    def load_tools(activity_name: str) -> List[Dict]
    def load_history(activity_name: str) -> ActivityHistory
    def build_activity_context(
        activity_name: str,
        service_name: Optional[str] = None,
        specification: Optional[Specification] = None,
        manifest: Optional[Manifest] = None,
        tools: Optional[List[Dict]] = None,
        history: Optional[ActivityHistory] = None,
    ) -> Dict
```

### Workspace Discovery

Strategies (in order):
1. Check for `.spectra` marker in current/parent directories
2. Check for `Core/` directory structure
3. Raise error if not found

### Design Decisions

- **Flexible Loading**: Can load or accept pre-loaded context
- **Workspace Auto-Discovery**: Reduces configuration overhead
- **Lazy Loading**: Context loaded on-demand (not eagerly)

---

## 5. Playbook Registry

### Purpose

Registry-driven playbook discovery and execution. Single source of truth is `operations/playbooks/playbooks-registry.yaml`.

### Responsibilities

- Registry loading (YAML)
- Playbook discovery (filter by activity)
- Playbook execution (Python, PowerShell, shell scripts)
- Execution result handling

### Interface

```python
class PlaybookRegistry:
    def load_registry() -> Dict
    def discover_playbooks(activity_name: str) -> List[Playbook]
    def get_playbook(name: str) -> Optional[Playbook]
    def execute_playbook(playbook: Playbook, args: Optional[Dict]) -> Dict
```

### Registry Format

```yaml
playbooks:
  - name: playbook-name
    description: "What this playbook does"
    path: "operations/playbooks/category/playbook.ps1"
    activity: "discover"  # Which activities can use this
    inputs:
      - name: input1
        type: string
    outputs:
      - name: output1
        type: string
```

### Execution Model

- **Python Scripts** (`.py`): `python {script} {args}`
- **PowerShell Scripts** (`.ps1`): `pwsh -File {script} {args}`
- **Shell Scripts** (other): `sh {script} {args}`

### Design Decisions

- **Registry-Driven**: Single source of truth (YAML), not file system scanning
- **Activity Filtering**: Playbooks scoped to specific activities
- **Subprocess Execution**: Isolated execution environment
- **Version-Controlled**: Registry changes tracked in Git (reversible)

---

## 6. State Management

### Purpose

Manages specification, manifest, and history state. Provides data models and persistence.

### Components

#### Specification

User's goal/requirements (adapted from solution-engine covenant). Single source of truth for what needs to be built.

```python
@dataclass
class Specification:
    service: str
    purpose: str
    maturity: Optional[str] = None
    dependencies: Optional[Dict] = None
    stages: Optional[Dict] = None
    # ...
```

**Storage**: `.spectra/{service}.specification.yaml` or `Core/{service}/{service}.specification.yaml`

#### Manifest

Activity execution results. Records what an activity actually did (outputs, status, timestamps, errors).

```python
@dataclass
class Manifest:
    activity: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    status: str = "pending"  # pending, in_progress, complete, failed
    outputs: Dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    # ...
```

**Storage**: `.spectra/manifests/{activity}-manifest.yaml`

#### ActivityHistory

Historical record of past decisions/outcomes for self-learning.

```python
@dataclass
class ActivityHistory:
    activity: str
    entries: List[ActivityHistoryEntry] = field(default_factory=list)
    
    def add_entry(decision: Dict, context: Dict, outcome: str, result: Dict)
    def get_recent(limit: int = 10) -> List[ActivityHistoryEntry]
```

**Storage**: `.spectra/history/{activity}-history.yaml`

### Design Decisions

- **YAML Format**: Human-readable, version-controllable
- **Activity-Specific**: Each activity has its own manifest/history
- **Audit Trail**: Complete record of all changes (reversible)
- **Self-Learning**: History enables pattern recognition

---

## Component Interactions

```
┌─────────────┐
│Orchestrator │
└──────┬──────┘
       │
       ├──► Activity Framework
       │         │
       │         ├──► LLM Client
       │         ├──► Context Builder
       │         ├──► Playbook Registry
       │         └──► State Management (Specification/Manifest/History)
       │
       └──► Activity Registry
                 │
                 └──► Discover
                 └──► Assess (planned)
                 └──► Build (planned)
                 └──► ...
```

---

## Related Documentation

- [Main Architecture](architecture.md) - System overview
- [Activity Architecture](activities.md) - Activity system deep dive
- [Data Architecture](data.md) - Data models and persistence

