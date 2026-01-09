# Prompt Optimization Analysis - 2026-01-08

**Question**: Is prompt truncation the right approach? Are we doing this efficiently?

**Answer**: ❌ **No. Truncation is a workaround, not a solution.** We should use **multi-turn selection** or **semantic filtering** instead.

---

## Current Problem

### What We're Doing Wrong

1. **Loading ALL playbook metadata into prompt** (even with "limit to 20")
   - 20 playbooks × ~200 chars metadata = ~4,000 chars
   - Plus system prompt (~2,000 chars)
   - Plus user message (~1,000 chars)
   - Plus context summaries (~2,000 chars)
   - **Total: ~9,000 chars = ~2,250 tokens** (approaching limits)

2. **Truncating when too large** (losing context)
   - Throws away information
   - LLM may select wrong playbooks due to incomplete context
   - Not scalable as playbook registry grows

3. **Single-turn approach** (everything in one prompt)
   - Forces us to include all context upfront
   - No opportunity for iterative refinement
   - One-shot decision making

### Root Cause

**We're treating the LLM as if it has tool/RAG access, but it doesn't.** The `LLMClient` is a simple HTTP chat completion API - no tool calling, no RAG, no autonomous file access.

---

## Better Solutions

### Option 1: Multi-Turn Playbook Selection (RECOMMENDED)

**Pattern**: Two-phase LLM interaction
1. **Phase 1 (Selection)**: LLM selects playbook(s) from minimal metadata
2. **Phase 2 (Execution)**: Load selected playbook content, LLM executes

**Benefits**:
- ✅ Minimal tokens in selection phase (only top 5-10 playbooks)
- ✅ No truncation needed
- ✅ Scalable to 100+ playbooks
- ✅ LLM gets full context only for selected playbooks

**Implementation**:

```python
# Phase 1: Selection (minimal metadata)
playbook_context = {
    "available_playbooks": [
        {"name": "railway.001-create-service", "description": "Create Railway service"},
        {"name": "github.001-create-repo", "description": "Create GitHub repo"},
        # ... only top 5-10 most relevant (filtered by activity/domain)
    ]
}

# LLM selects: ["railway.001-create-service"]
selected_playbooks = await llm.select_playbooks(context)

# Phase 2: Execution (load selected playbook content)
for playbook_name in selected_playbooks:
    playbook_content = load_playbook_file(playbook_name)
    # Include full playbook content in next LLM call
    execution_result = await llm.execute_with_playbook(playbook_content, task)
```

**Token Savings**:
- Selection phase: ~500-1000 tokens (vs. 2000-4000 with all playbooks)
- Execution phase: ~2000 tokens (one playbook at a time)
- **Total: ~2500-3000 tokens** (vs. 4000+ with truncation)

---

### Option 2: Semantic Playbook Filtering (BETTER)

**Pattern**: Pre-filter playbooks using LLM before including in prompt

**Benefits**:
- ✅ Only relevant playbooks in prompt
- ✅ Still single-turn (if preferred)
- ✅ More accurate selection

**Implementation**:

```python
# Step 1: Semantic filtering (LLM filters playbooks)
all_playbooks = registry.discover_playbooks(activity_name)
filter_prompt = f"""
Task: {user_input}
Available playbooks: {[pb.name for pb in all_playbooks]}

Select the 5 most relevant playbooks for this task.
Return JSON: {{"relevant_playbooks": ["playbook1", "playbook2", ...]}}
"""
relevant_playbook_names = await llm.filter_playbooks(filter_prompt)

# Step 2: Include only relevant playbooks in main prompt
relevant_playbooks = [pb for pb in all_playbooks if pb.name in relevant_playbook_names]
playbook_context = {
    "available_playbooks": [
        {"name": pb.name, "description": pb.description, ...}
        for pb in relevant_playbooks[:5]  # Only top 5
    ]
}

# Step 3: LLM selects and executes (now with manageable context)
result = await llm.execute_with_context(playbook_context, task)
```

**Token Savings**:
- Filter phase: ~500 tokens (one-time cost)
- Main phase: ~1500 tokens (only 5 playbooks)
- **Total: ~2000 tokens** (vs. 4000+ with truncation)

---

### Option 3: Summarized Playbook Lists (GOOD COMPROMISE)

**Pattern**: Summarize playbook list, LLM requests specific playbooks if needed

**Benefits**:
- ✅ Minimal tokens
- ✅ Single-turn
- ✅ LLM can request more details if needed (multi-turn fallback)

**Implementation**:

```python
# Create summary instead of full metadata
playbook_summary = {
    "railway_playbooks": 5,  # Count only
    "github_playbooks": 3,
    "domain_summaries": {
        "railway": "Deployment and service management (5 playbooks)",
        "github": "Repository creation and management (3 playbooks)",
    },
    "most_relevant": [
        {"name": "railway.001-create-service", "one_line": "Create Railway service"},
        # ... only top 3
    ],
    "instructions": "Select from most_relevant, or request specific domain playbooks for more options."
}

# LLM selects from summary or requests more details
result = await llm.execute_with_summary(playbook_summary, task)
```

**Token Savings**:
- Summary: ~300-500 tokens (vs. 2000-4000 with full metadata)
- **Total: ~1500-2000 tokens**

---

## Comparison

| Approach | Tokens | Scalability | Accuracy | Complexity |
|----------|--------|-------------|----------|------------|
| **Current (Truncation)** | 4000+ (truncated) | ❌ Poor | ⚠️ Reduced (lost context) | Low |
| **Multi-Turn Selection** | 2500-3000 | ✅ Excellent | ✅ High | Medium |
| **Semantic Filtering** | 2000 | ✅ Excellent | ✅ Very High | Medium |
| **Summarized Lists** | 1500-2000 | ✅ Good | ⚠️ Medium | Low |

---

## Recommendation

### 🎯 **Option 2: Semantic Playbook Filtering** (BEST)

**Why**:
1. ✅ **Most efficient**: Only relevant playbooks in prompt
2. ✅ **Most accurate**: LLM filters based on task understanding
3. ✅ **Scalable**: Works with 10 or 1000 playbooks
4. ✅ **Single-turn**: Maintains current architecture pattern
5. ✅ **No truncation needed**: Always within token limits

**Implementation Steps**:

1. **Add semantic filtering method to `PlaybookRegistry`**:
   ```python
   async def filter_relevant_playbooks(
       self,
       activity_name: str,
       task: str,
       llm_client: LLMClient,
       max_playbooks: int = 5
   ) -> List[Playbook]:
       """Use LLM to select most relevant playbooks for task."""
       all_playbooks = self.discover_playbooks(activity_name)
       # LLM filters playbooks based on task
       # Return top N most relevant
   ```

2. **Update activities to use filtered playbooks**:
   ```python
   # Instead of: playbook_context = registry.get_playbook_context_for_llm("provision")
   relevant_playbooks = await registry.filter_relevant_playbooks(
       activity_name="provision",
       task=context.user_input,
       llm_client=self.llm_client,
       max_playbooks=5
   )
   playbook_context = {
       "available_playbooks": [minimal_metadata(pb) for pb in relevant_playbooks]
   }
   ```

3. **Remove truncation logic** (no longer needed)

---

## Alternative: If We Want Tool/RAG Access

**Option 4: Add Tool Calling Support** (FUTURE)

If we want the LLM to autonomously access playbooks via tools:

1. **Upgrade LLMClient to support tool calling**:
   - Add `tools` parameter to `chat_completion()`
   - Support function calling responses
   - Implement tool execution (read_file, codebase_search)

2. **Provide playbooks as tools**:
   ```python
   tools = [
       {
           "type": "function",
           "function": {
               "name": "get_playbook_content",
               "description": "Load full playbook content",
               "parameters": {
                   "type": "object",
                   "properties": {
                       "playbook_name": {"type": "string"}
                   }
               }
           }
       }
   ]
   ```

3. **LLM calls tool when needed**:
   - LLM sees playbook metadata in prompt
   - LLM calls `get_playbook_content("railway.001-create-service")` when needed
   - Tool returns playbook content
   - LLM uses content for execution

**Benefits**:
- ✅ Fully autonomous
- ✅ No truncation
- ✅ Most flexible

**Costs**:
- ⚠️ More complex implementation
- ⚠️ Requires tool calling API support
- ⚠️ Additional latency (tool calls)

---

## Conclusion

**Current approach (truncation) is a workaround, not a solution.**

**Recommended approach**: **Semantic Playbook Filtering** (Option 2)
- More efficient (2000 tokens vs. 4000+ truncated)
- More accurate (LLM filters based on understanding)
- More scalable (works with any number of playbooks)
- Maintains single-turn pattern (if preferred)
- No truncation needed

**Alternative**: **Multi-Turn Selection** (Option 1) if we want iterative refinement.

**Future**: **Tool Calling Support** (Option 4) if we want full autonomy.

