# Playbook Context Architecture for LLM Execution

**Purpose**: Define how Alana (LLM client) accesses and uses playbook context for autonomous execution.

**Problem**: Playbooks are markdown documentation that LLM needs to understand, but loading all playbooks into context would be prohibitively expensive (token limits, cost, latency).

**Solution**: Registry-driven discovery with **context injection** - Playbook content is provided to LLM via context when needed, using registry metadata for selection.

**Architecture Note**: Alana LLM has **RAG-based codebase access** via `spectra_rag.py`:
- ✅ **Searches codebase** - Uses glob patterns to find relevant files
- ✅ **Reads file content** - Uses `file_path.read_text()` to read markdown files
- ✅ **Injects context** - Adds codebase content to LLM prompt automatically
- ✅ **Query-driven** - Searches based on query terms

**Solution**: Leverage Alana's existing RAG system for playbook access!

---

## SPECTRA-Grade Approach

### Principle: Registry for Discovery, Codebase Access for Execution

**Simple Two-Phase Approach**:

1. **Discovery Phase** (Registry Metadata):
   - Load playbook registry metadata only (name, description, domain, activity, inputs, outputs, **file path**)
   - Use metadata for playbook selection
   - Very fast, minimal tokens (~50-100 per playbook)
   - Provide file paths so Alana can access playbooks via codebase tools

2. **Execution Phase** (Autonomous Codebase Access):
   - Alana uses existing codebase search/read tools to access playbook files
   - No special loading mechanism needed
   - Alana reads playbook content when she needs it
   - Fully autonomous - Alana decides when to read which playbook

### Key Insight

**Alana already has RAG-based codebase access** - leverage existing system!

- ✅ Registry provides metadata + file paths
- ✅ Alana's RAG system (`spectra_rag.py`) can search for playbook files
- ✅ RAG system reads file content and injects into prompt automatically
- ✅ Query-driven: Alana searches for playbooks based on task/query
- ✅ Simpler: Use existing RAG infrastructure, no new tools needed

### Pattern Alignment

This aligns with SPECTRA patterns:
- **Registry Pattern**: Single source of truth for discovery
- **Autonomous Execution**: LLM decides when to access resources
- **Tool-Driven**: Uses existing codebase access tools (no special mechanisms)

---

## Architecture

### 1. Playbook Registry (Single Source of Truth)

**Location**: `Core/operations/playbooks/playbooks-registry.yaml`

**Purpose**: Lightweight metadata for discovery and selection

**Registry Entry Structure**:

```yaml
playbooks:
  - name: "railway.001-create-service"
    domain: "railway"
    activity: "deploy"  # Activities that can use this playbook
    path: "railway/railway.001-create-service.md"
    description: "Create Railway service via API (MCP-Native)"
    summary: "Uses RailwayMCP to create a new Railway service in the cosmos project. Configures basic settings and returns service ID."  # LLM-friendly summary
    inputs:
      - name: "service_name"
        type: "string"
        required: true
        description: "Name of the service to create"
      - name: "project_name"
        type: "string"
        required: false
        default: "cosmos"
        description: "Railway project name"
    outputs:
      - name: "service_id"
        type: "string"
        description: "Created Railway service ID"
      - name: "service_url"
        type: "string"
        description: "Service dashboard URL"
    manual_steps: false
    automation_possible: true
    mcp_native: true  # Uses SPECTRA MCP Layer
    created_at: "2026-01-07T..."
    updated_at: "2026-01-07T..."
```

**Registry Benefits**:

- ✅ **Fast Discovery**: Query by activity/domain in milliseconds
- ✅ **Minimal Tokens**: Only metadata loaded (not full playbook content)
- ✅ **Selection Context**: LLM can select appropriate playbook from metadata
- ✅ **Type Safety**: Structured inputs/outputs for validation

### 2. Playbook Content Access (Two Options)

**Option A: Autonomous Codebase Access** (If Alana has codebase tools)

**When**: Alana decides autonomously when to read playbook content

**Method**: Alana uses existing codebase access tools (`read_file`, `codebase_search`)

**Context Format**:

```python
# Activity context includes playbook registry metadata with file paths
context = {
    "available_playbooks": [
        {
            "name": "railway.001-create-service",
            "domain": "railway",
            "description": "Create Railway service via API (MCP-Native)",
            "summary": "Uses RailwayMCP to create a new Railway service...",
            "path": "railway/railway.001-create-service.md",  # File path for codebase access
            "full_path": "Core/operations/playbooks/railway/railway.001-create-service.md",  # Full path
            "inputs": [...],
            "outputs": [...]
        },
        # ... more playbook metadata
    ],
    "instructions": "To access a playbook's full content, use the read_file tool with the full_path."
}

# LLM selects playbook based on metadata
selected_playbook = "railway.001-create-service"

# Alana autonomously reads playbook content using codebase tools
# No special loading mechanism - Alana uses read_file() or codebase_search()
# Alana decides when and how to access the playbook content
```

**Option B: Context Injection** (If Alana doesn't have codebase tools)

**When**: After playbook selection, before execution

**Method**: Activity loads playbook content and injects into LLM context

**Context Format**:

```python
# Step 1: Activity provides registry metadata (lightweight)
context = {
    "available_playbooks": [
        {
            "name": "railway.001-create-service",
            "domain": "railway",
            "description": "Create Railway service via API (MCP-Native)",
            "summary": "Uses RailwayMCP to create a new Railway service...",
            "path": "railway/railway.001-create-service.md",
            "full_path": "Core/operations/playbooks/railway/railway.001-create-service.md",
            "inputs": [...],
            "outputs": [...]
        },
        # ... more playbook metadata
    ]
}

# Step 2: LLM selects playbook based on metadata
selected_playbook = "railway.001-create-service"

# Step 3: Activity loads playbook content and injects into context
playbook_content = load_playbook_file(selected_playbook.full_path)

execution_context = {
    **context,
    "selected_playbook": {
        "name": selected_playbook,
        "content": playbook_content  # Full markdown content injected
    }
}
```

**Recommendation**:

- **If Alana has codebase access tools**: Use Option A (autonomous access) - simpler, more natural
- **If Alana doesn't have codebase access**: Use Option B (context injection) - explicit, controlled
- **Hybrid**: Provide metadata + file paths, let LLM request content if it has tools, otherwise inject

### 3. LLM Execution Flow

**Step 1: Discovery & Selection** (Registry Metadata Only)

```
LLM (Alana) receives:
- Task: "Deploy service to Railway"
- Available playbooks: [metadata only - name, description, inputs, outputs, file paths]
- LLM selects: "railway.001-create-service" based on metadata
```

**Step 2: Content Access** (Depends on Alana's Capabilities)

**Alana's RAG System** (Current Implementation):
```
Alana's RAG system searches codebase:
- Query: "deploy service to Railway"
- RAG searches: Core/operations/playbooks/**/*.md
- Finds: railway/railway.001-create-service.md
- Reads file content: file_path.read_text()
- Injects into prompt: Adds playbook content to system prompt
- Alana executes: Understands playbook and executes via tools
```

**Enhancement Option**: Add playbook-specific search patterns to RAG:
```python
# Add to spectra_rag.py SEARCH_PATTERNS
"**/operations/playbooks/**/*.md",  # Playbook search pattern
```

**If Alana doesn't have codebase tools**:
```
Activity loads playbook content:
- Reads file: Core/operations/playbooks/railway/railway.001-create-service.md
- Injects full markdown content into LLM context
- LLM receives playbook content directly
```

**Step 3: Execution** (LLM Understands & Executes)

```
LLM has:
- Full playbook content (via codebase tools OR context injection)
- Inputs: service_name="portal", project_name="cosmos"
- LLM understands playbook instructions
- LLM executes via tools/MCP APIs (RailwayMCP.create_service())
- LLM validates outputs match playbook specification
```

**Key Point**: The mechanism depends on Alana's capabilities, but the outcome is the same - LLM has playbook content when needed.

---

## Implementation

### Enhanced PlaybookRegistry

```python
class PlaybookRegistry:
    """Registry-driven playbook discovery with JIT loading."""

    def discover_playbooks(self, activity_name: str) -> List[Playbook]:
        """
        Discover playbooks for activity (metadata only - lightweight).

        Returns: List of Playbook objects with metadata (no content)
        """
        # Load registry YAML (metadata only)
        registry = self.load_registry()
        playbooks_data = registry.get("playbooks", [])

        # Filter by activity
        matching_playbooks = [
            pb for pb in playbooks_data
            if pb.get("activity") == activity_name
        ]

        # Return Playbook objects with metadata (no content)
        return [Playbook.from_registry_entry(pb) for pb in matching_playbooks]

    def get_playbook_context_for_llm(self, activity_name: str) -> Dict:
        """
        Get optimized context for LLM (metadata only - for selection).

        Returns: Dictionary with playbook metadata suitable for LLM context
        """
        playbooks = self.discover_playbooks(activity_name)

        return {
            "available_playbooks": [
                {
                    "name": pb.name,
                    "domain": pb.domain,
                    "description": pb.description,
                    "summary": pb.metadata.get("summary", pb.description),
                    "path": pb.path,  # Relative path (e.g., "railway/railway.001-create-service.md")
                    "full_path": f"Core/operations/playbooks/{pb.path}",  # Full path for codebase access
                    "inputs": pb.inputs,
                    "outputs": pb.outputs,
                    "mcp_native": pb.metadata.get("mcp_native", False),
                    "manual_steps": pb.metadata.get("manual_steps", False),
                    "automation_possible": pb.metadata.get("automation_possible", True),
                }
                for pb in playbooks
            ],
            "instructions": (
                "To access a playbook's full content, use the read_file tool with the full_path. "
                "You can also use codebase_search to find related playbooks or search for specific instructions."
            )
        }
```

### Activity Integration

```python
class DeployActivity:
    """DEPLOY activity with playbook-driven execution."""

    def __init__(self, registry: PlaybookRegistry):
        self.registry = registry

    def execute(self, task: str, context: Dict) -> Dict:
        """
        Execute DEPLOY activity with playbook-driven execution.

        Flow:
        1. Get playbook metadata from registry (lightweight)
        2. LLM selects appropriate playbook(s)
        3. Load full playbook content just-in-time
        4. LLM understands and executes playbook via tools/MCP
        """
        # Step 1: Get playbook context (metadata only - lightweight)
        playbook_context = self.registry.get_playbook_context_for_llm("deploy")

        # Step 2: LLM selects playbook based on task and metadata
        llm_prompt = f"""
        Task: {task}

        Available playbooks:
        {json.dumps(playbook_context['available_playbooks'], indent=2)}

        Select the most appropriate playbook(s) to execute.
        """

        selected_playbooks = self.llm.select_playbooks(llm_prompt)

        # Step 3: Access playbook content (depends on Alana's capabilities)

        execution_results = []
        for playbook_name in selected_playbooks:
            playbook_metadata = self.registry.get_playbook(playbook_name)

            # Alana's RAG system will search for playbook based on query
            # Option A: Let RAG system find playbook (autonomous)
            # - RAG searches: Core/operations/playbooks/**/*.md
            # - Finds playbook by name/description match
            # - Reads content and injects into prompt

            # Option B: Explicitly guide RAG to playbook (if needed)
            # - Add playbook path to query: "deploy service using railway.001-create-service"
            # - RAG will find and load playbook content

            # Option C: Direct file injection (if RAG doesn't find it)
            # - Load playbook content explicitly
            # - Inject into context alongside RAG results

            # Recommended: Use RAG system (Option A) - most autonomous
            playbook_context = {
                "playbook": playbook_metadata,
                "file_path": playbook_metadata.full_path,
                "rag_query": f"playbook {playbook_metadata.name} {playbook_metadata.description}",  # Guide RAG search
                "instructions": "RAG system will search for and load playbook content automatically"
            }

            # Step 4: LLM understands and executes playbook
            execution_result = self.llm.execute_playbook(
                playbook_context=playbook_context,
                inputs=context.get("inputs", {}),
                tools=self.available_tools  # RailwayMCP, GitHubMCP, etc.
            )

            execution_results.append(execution_result)

        return {"results": execution_results}
```

---

## Context Optimization

### Token Budget Management

**Registry Metadata** (Discovery Phase - Always in Context):
- ~50-100 tokens per playbook
- 10 playbooks = 500-1000 tokens
- Fast, efficient, sufficient for selection
- **Always loaded** - lightweight metadata with file paths

**Playbook Content** (Execution Phase - On-Demand):

**If Alana has codebase tools**:
- ~500-2000 tokens per playbook (varies by complexity)
- **Not loaded into context by default**
- Alana reads playbook content via `read_file` tool when needed
- Content only in context when Alana explicitly reads it
- Alana decides which playbooks to read, when, and how
- **No upfront token cost** - Alana only reads what she needs

**If Alana doesn't have codebase tools**:
- ~500-2000 tokens per playbook (varies by complexity)
- **Loaded into context after selection** (just-in-time)
- Activity injects playbook content into LLM context
- Only selected playbook(s) loaded, not all
- **Minimal token cost** - only selected playbooks loaded

**Total Context** (Typical Deploy Activity):
- Discovery: ~1000 tokens (all available playbooks metadata - always in context)
- Execution: ~1500-3000 tokens (1-2 selected playbooks full content)
- **Total: ~2500-4000 tokens** (vs. ~20,000+ if loading all playbooks upfront)

### Optimization Strategies

1. **Metadata Summaries**: Include `summary` field in registry (LLM-friendly short description)
2. **File Paths**: Provide full file paths so Alana can access via codebase tools
3. **Autonomous Access**: Alana decides when to read playbook content (not pre-loaded)
4. **Tool-Based**: Uses existing codebase access tools (read_file, codebase_search) - no special mechanisms

---

## Benefits

### ✅ SPECTRA-Grade Quality

- **Registry-Driven**: Single source of truth, version-controlled
- **MCP-Native**: Playbooks reference SPECTRA MCP Layer tools
- **Fully Autonomous**: LLM selects playbooks and accesses content independently
- **Tool-Driven**: Uses existing codebase access tools (no special mechanisms)
- **Context-Optimized**: Minimal token usage, on-demand content access
- **Simple & Natural**: Follows normal LLM codebase interaction patterns

### ✅ Best Practices

- **Separation of Concerns**: Registry for discovery, playbooks for execution
- **Autonomous Access**: LLM accesses playbook content when needed (no explicit loading)
- **Tool-Driven**: Uses existing codebase access tools (read_file, codebase_search)
- **LLM-Friendly**: Structured metadata for selection, file paths for access
- **Scalable**: Works with 10 or 1000 playbooks
- **Simple**: No special loading mechanisms - just registry + codebase access

### ✅ Alignment with SPECTRA Patterns

- **Discovery Activity Pattern**: Metadata first, full content on demand via tools
- **Registry Pattern**: Single source of truth, queryable metadata
- **Autonomous Execution**: LLM decides when to access resources (same as cosmic index)
- **Tool-Driven**: Uses existing tools (codebase access) rather than special mechanisms

---

## Example Flow

### Deploy Activity Execution

```
1. DEPLOY activity starts
   └─> Load playbook registry metadata (1000 tokens)

2. LLM receives context:
   - Task: "Deploy portal service to Railway"
   - Available playbooks: [metadata only]
     - railway.001-create-service
     - railway.002-connect-github
     - github.003-push-code
     - health.001-check-endpoint

3. LLM selects playbooks:
   - railway.001-create-service (create Railway service)
   - github.003-push-code (push code to GitHub)
   - health.001-check-endpoint (verify deployment)

4. Alana autonomously accesses playbook content:
   - Uses read_file() tool to read railway.001-create-service.md
   - Uses read_file() tool to read github.003-push-code.md
   - Uses read_file() tool to read health.001-check-endpoint.md
   - Alana decides when to read each playbook (no explicit orchestration)

5. Alana executes playbooks:
   - Has playbook content (read via tools)
   - Understands instructions
   - Calls tools/MCP APIs (RailwayMCP, GitHubMCP)
   - Validates outputs

6. Results returned:
   - Service created: srv_abc123
   - Code pushed: commit_xyz789
   - Health check: passed
```

---

## Registry Enhancement Requirements

### Add to Playbook Registry Schema

```yaml
playbooks:
  - name: "railway.001-create-service"
    domain: "railway"
    activity: "deploy"
    path: "railway/railway.001-create-service.md"
    description: "Create Railway service via API (MCP-Native)"
    summary: "Uses RailwayMCP to create a new Railway service..."  # NEW: LLM-friendly summary
    inputs: [...]  # Structured inputs
    outputs: [...]  # Structured outputs
    mcp_native: true  # NEW: Indicates uses SPECTRA MCP Layer
    manual_steps: false
    automation_possible: true
    created_at: "2026-01-07T..."
    updated_at: "2026-01-07T..."
```

### Update PlaybookRegistry Implementation

- Add `summary` field support
- Add `mcp_native` field support
- Add `full_path` to playbook context (for RAG system)
- Update `get_playbook_context_for_llm()` method to include file paths
- Update `Playbook` dataclass to include new fields

### Enhance Alana's RAG System (Optional)

**Add playbook search patterns to `spectra_rag.py`**:

```python
# Add to SEARCH_PATTERNS
SEARCH_PATTERNS = [
    "**/*SPECTRA*.md",
    "**/README.md",
    "**/*spectra*.md",
    "**/.spectra/**/*.md",
    "**/operations/**/*.md",
    "**/operations/playbooks/**/*.md",  # NEW: Playbook search
]

# Add playbook-specific search function
def find_playbook(playbook_name: str) -> Optional[Dict[str, str]]:
    """Find specific playbook by name."""
    for root in SPECTRA_ROOTS:
        playbook_path = root / "Core" / "operations" / "playbooks" / f"{playbook_name}.md"
        if playbook_path.exists():
            return {
                "path": str(playbook_path.relative_to(root)),
                "content": playbook_path.read_text(encoding="utf-8", errors="ignore"),
                "full_path": str(playbook_path)
            }
    return None
```

**Benefits**:
- ✅ RAG system can find playbooks automatically
- ✅ No changes to Orchestrator needed
- ✅ Leverages existing infrastructure

---

## Conclusion

**This is the SPECTRA-grade approach**:

1. ✅ **Registry for Discovery** - Fast, lightweight, queryable metadata with file paths
2. ✅ **RAG-Based Access** - Leverages Alana's existing RAG system (`spectra_rag.py`)
3. ✅ **Context Optimization** - Minimal tokens (metadata only), RAG loads content on-demand
4. ✅ **LLM-Friendly** - Structured metadata + RAG search patterns
5. ✅ **Fully Autonomous** - LLM selects playbooks, RAG finds and loads content
6. ✅ **MCP-Native** - Playbooks reference SPECTRA MCP Layer tools
7. ✅ **Leverages Existing Infrastructure** - Uses Alana's RAG system, no new tools needed

**This aligns with**:
- Registry pattern (single source of truth)
- Autonomous execution (LLM decides when to access resources)
- Tool-driven approach (uses existing codebase access tools)
- SPECTRA-Grade quality (autonomous, MCP-native, scalable, simple)

