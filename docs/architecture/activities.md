# Activity Architecture

**Status**: In Progress  
**Last Updated**: 2026-01-06

---

## Overview

Activities are the core execution units of the Orchestrator. Each activity is an AI agent that uses LLM to make autonomous decisions, orchestrating playbooks and tools to achieve goals.

---

## Activity Pattern

### Base Class Design

```python
class Activity(ABC):
    """Abstract base class for all activities."""
    
    @abstractmethod
    async def execute(context: ActivityContext) -> ActivityResult
```

### Key Characteristics

1. **AI-Driven**: Uses LLM for decision-making (not hardcoded logic)
2. **Context-Aware**: Loads specification, manifest, tools, history
3. **Self-Learning**: Records decisions/outcomes in history
4. **Composable**: Can be invoked independently or in pipelines
5. **Reversible**: Manifest provides audit trail for all changes

---

## Activity Lifecycle

### Execution Flow

```
1. Initialize Activity
   ├── LLM Client (optional override)
   ├── Context Builder (optional override)
   └── Playbook Registry (optional override)

2. Execute Activity
   ├── Load Context (Specification, Manifest, Tools, History)
   ├── Format Prompt (with context injection)
   ├── Call LLM (chat_completion)
   ├── Parse Response (JSON decisions)
   ├── Execute Playbooks (based on LLM decisions)
   ├── Update Manifest (with outputs)
   └── Record History (decision, outcome, result)

3. Return Result
   └── ActivityResult (success, outputs, errors)
```

### State Transitions

```
pending → in_progress → complete
                    ↓
                 failed
```

States tracked in Manifest:
- **pending**: Activity not yet started
- **in_progress**: Activity executing
- **complete**: Activity completed successfully
- **failed**: Activity failed (errors recorded)

---

## Context Injection Pattern

### Context Sources

1. **Specification**: User's goals/requirements (what needs to be built)
2. **Manifest**: Current state/outputs (what's been done)
3. **Tools**: Available playbooks (what can be executed)
4. **History**: Past decisions/outcomes (what worked before)

### Prompt Formatting

```python
def format_prompt(context: Dict, history: Optional[List[Dict]]) -> str:
    prompt_parts = [
        "You are the {activity_name} activity agent for SPECTRA orchestrator.",
        "",
        "CONTEXT:",
        json.dumps(context, indent=2),
    ]
    
    if history:
        prompt_parts.extend([
            "",
            "HISTORY (past decisions/outcomes):",
            json.dumps(history, indent=2),
        ])
    
    return "\n".join(prompt_parts)
```

### Context Dictionary Structure

```python
{
    "activity": "discover",
    "specification": {
        "service": "logging",
        "purpose": "...",
        # ...
    },
    "manifest": {
        "activity": "discover",
        "status": "in_progress",
        "outputs": {...},
        # ...
    },
    "tools": [
        {
            "name": "playbook-name",
            "description": "...",
            # ...
        }
    ],
    "history": [
        {
            "timestamp": "...",
            "decision": {...},
            "outcome": "success",
            # ...
        }
    ]
}
```

---

## LLM Interaction

### Request Format

```python
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_message},
]

payload = {
    "model": self.model,
    "messages": messages,
    "max_tokens": max_tokens,
    "temperature": temperature,
}
```

### Response Parsing

1. Extract JSON from markdown code blocks (if present)
2. Parse JSON response
3. Fallback to raw response if JSON parsing fails

```python
async def call_llm(system_prompt: str, user_message: str) -> Dict:
    response = await self.llm_client.chat_completion(system_prompt, user_message)
    
    # Try to parse JSON from response
    try:
        # Extract JSON from markdown code blocks if present
        json_content = response
        if "```json" in response:
            json_start = response.find("```json") + 7
            json_end = response.find("```", json_start)
            json_content = response[json_start:json_end].strip()
        
        return json.loads(json_content)
    except json.JSONDecodeError:
        # Return raw response as dict
        return {"raw_response": response}
```

---

## Playbook Execution

### Execution Model

Activities orchestrate playbooks, they don't execute directly:

```python
async def execute_playbook(name: str, args: Optional[Dict]) -> Dict:
    playbook = self.playbook_registry.get_playbook(name)
    if not playbook:
        raise ValueError(f"Playbook not found: {name}")
    
    return self.playbook_registry.execute_playbook(playbook, args)
```

### Playbook Types

- **Python Scripts** (`.py`): `python {script} {args}`
- **PowerShell Scripts** (`.ps1`): `pwsh -File {script} {args}`
- **Shell Scripts** (other): `sh {script} {args}`

---

## Manifest Updates

### Output Recording

```python
def update_manifest(manifest: Manifest, outputs: Dict):
    for name, value in outputs.items():
        manifest.add_output(name, value)
```

### Manifest Lifecycle

1. **Create Manifest**: `Manifest(activity="discover")`
2. **Start Activity**: `manifest.start()` (sets status to "in_progress")
3. **Add Outputs**: `manifest.add_output(name, value)`
4. **Complete Activity**: `manifest.complete(success=True)` (sets status to "complete")
5. **Save Manifest**: `manifest.save(path)`

---

## Self-Learning Mechanism

### History Recording

```python
def record_history(
    history: ActivityHistory,
    decision: Dict,
    outcome: str,  # "success" or "failure"
    result: ActivityResult,
    context: Optional[Dict] = None,
):
    history.add_entry(
        decision=decision,
        context=context or {},
        outcome=outcome,
        result={
            "outputs": result.outputs,
            "errors": result.errors,
            **result.metadata,
        },
    )
```

### History Structure

```python
@dataclass
class ActivityHistoryEntry:
    timestamp: str
    decision: Dict[str, Any]      # What LLM decided
    context: Dict[str, Any]       # Context used
    outcome: str                  # "success" or "failure"
    result: Dict[str, Any]        # Actual result
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### Learning Pattern

History entries enable pattern recognition:
- "In similar situations, X worked well, Y failed"
- LLM sees history in context for future decisions
- Enables self-improvement over time

---

## Activity Composition

### Sequential Execution

Activities can be composed into pipelines:

```
Discover → Assess → Design → Build → Test → Deploy
```

### Parallel Execution (Future)

Activities that don't depend on each other can run in parallel:

```
Build → Test (parallel: Unit Tests, Integration Tests)
```

### Conditional Execution

Activities can determine if they should run based on context:

```python
if manifest.get("outputs", {}).get("service_name"):
    # Service already discovered, skip Discover activity
    pass
```

---

## Concrete Activities

### Discover

**Purpose**: Problem/idea validation and service discovery (activity name: "discover")

**Outputs**:
- `service_name`: Extracted service name (mononymic)
- `problem`: Problem statement with impact
- `idea`: Idea validation
- `validation`: Problem-solution mapping
- `next_steps`: Recommended pipeline steps

**Guardrails**:
- Service name validation (mononymic, kebab-case)
- Registry anti-duplication check (planned)

### Assess (Planned)

**Purpose**: Maturity assessment (can be invoked at any point in pipeline)

**Outputs**:
- `maturity_assessment`: Level, target, requirements
- `gap_analysis`: Current vs target state (if applicable)

**Invocation Points**:
- Early: Initial maturity estimate (after Discover)
- Mid: Detailed assessment (after Design)
- Late: Audit current state (post-build/deploy)
- Standalone: On-demand maturity assessment

### Build (Planned)

**Purpose**: Code generation and build orchestration

### Test (Planned)

**Purpose**: Test execution and validation

### Deploy (Planned)

**Purpose**: Deployment orchestration

---

## Error Handling

### Activity-Level Errors

- Errors recorded in `ActivityResult.errors`
- Activity returns `success=False` but doesn't raise exception
- Orchestrator can continue with other activities

### LLM Errors

- Connection errors → retry logic (planned)
- Parse errors → fallback to raw response
- Invalid responses → error recorded in manifest

### Playbook Errors

- Subprocess errors → captured in execution result
- Playbook failures → error recorded in manifest
- Activity can handle gracefully (retry, fallback, etc.)

---

## Related Documentation

- [Component Architecture](components.md) - Activity Framework component
- [Main Architecture](architecture.md) - System overview
- [Data Architecture](data.md) - Manifest and History models

