# Build Activity Code Generation Enhancement Plan

**Problem:** LLM generates file structure but not actual implementation code

**Root Cause:** Prompt asks for `files_to_create` but doesn't emphasize full code generation

---

## 🔍 Current Behavior Analysis

### What Happens Now:
1. LLM is prompted: `files_to_create: [{"path": str, "content": str, "type": str}]`
2. LLM responds with paths but empty `content` fields
3. Build activity creates files with placeholders (lines 154-161)

### Why It Fails:
- Prompt doesn't explicitly request **full implementation code**
- `max_tokens=4096` is too small for 53 files
- LLM optimizes for brevity → omits code content

---

## 💡 Enhancement Strategy

### **Approach: Chunked File-by-File Generation**

**Phase 1: Structure Generation** (current behavior)
- LLM generates directory structure
- LLM lists files needed
- Creates skeleton directories

**Phase 2: File-by-File Code Generation** (NEW)
- For each critical file, make separate LLM call
- Provide file-specific context (purpose, dependencies)
- Request full implementation code
- Write actual code to disk

**Phase 3: Batch Non-Critical Files** (NEW)
- Config files, data files → use templates
- Documentation → generate from code
- Scripts → generate from patterns

---

## 🏗️ Implementation Plan

### **1. Enhanced Prompt (Structure Phase)**
```python
user_message = f"""
Generate code structure for: {context.user_input}

CRITICAL: You will generate code in TWO PHASES:
Phase 1 (now): Provide file structure and list
Phase 2 (next): Generate actual code for each file

For Phase 1, respond with:
- code_structure: {{"directories": [], "file_categories": {{}}}}
- files_to_create: [
    {{
      "path": "src/service.py",
      "type": "source",
      "priority": "critical",  # critical|normal|low
      "purpose": "Main service implementation",
      "dependencies": ["fastapi", "pydantic"]
    }}
  ]

CATEGORIZE FILES:
- critical: Main source files (need full LLM generation)
- normal: Supporting files (can use templates)
- low: Config/data files (can auto-generate)
"""
```

### **2. File-by-File Generation (NEW method)**
```python
async def _generate_file_code(
    self,
    file_info: Dict,
    service_dir: Path,
    context: ActivityContext
) -> str:
    """Generate actual code for a single file."""

    system_prompt = f"""
You are a SPECTRA Code Generator. Generate COMPLETE, WORKING code.

FILE: {file_info['path']}
PURPOSE: {file_info.get('purpose', 'Unknown')}
TYPE: {file_info.get('type', 'source')}
DEPENDENCIES: {file_info.get('dependencies', [])}

REQUIREMENTS:
- Generate full implementation (not stubs)
- Include error handling
- Add logging
- Follow SPECTRA standards
- Add docstrings
"""

    user_message = f"""
Generate complete implementation code for: {file_info['path']}

Context: {context.user_input}

Specification summary:
{context.specification[:1000] if context.specification else 'None'}

Return ONLY the code content (no JSON, no markdown fences).
"""

    # Call LLM with higher token limit for individual file
    code = await self.call_llm_raw(system_prompt, user_message, max_tokens=2048)
    return code
```

### **3. Orchestrate Generation**
```python
# In execute() method, after structure generation:

# Phase 1: Structure (current code)
llm_response = await self.call_llm(system_prompt, user_message, max_tokens=4096)
files_to_create = llm_response.get("files_to_create", [])

# Phase 2: Generate critical files (NEW)
files_created = []
for file_info in files_to_create:
    priority = file_info.get("priority", "normal")
    file_path = service_dir / file_info["path"]
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if priority == "critical":
        # Generate actual code
        logger.info(f"Generating code for: {file_path}")
        code = await self._generate_file_code(file_info, service_dir, context)
        file_path.write_text(code, encoding="utf-8")
    elif priority == "normal":
        # Use template or minimal implementation
        code = self._generate_template(file_info)
        file_path.write_text(code, encoding="utf-8")
    else:  # low priority
        # Auto-generate (configs, data)
        code = self._generate_config(file_info)
        file_path.write_text(code, encoding="utf-8")

    files_created.append(str(file_path))
```

### **4. Add Helper Methods**
```python
async def call_llm_raw(self, system_prompt: str, user_message: str, max_tokens: int = 2048) -> str:
    """Call LLM and return raw text (not JSON)."""
    # Similar to call_llm but expects plain text response
    pass

def _generate_template(self, file_info: Dict) -> str:
    """Generate template code for normal priority files."""
    # Return basic structure based on file type
    pass

def _generate_config(self, file_info: Dict) -> str:
    """Generate config/data files."""
    # Return default configs
    pass
```

---

## 📊 Expected Improvements

### **Before (Current):**
- 53 files created
- All with placeholders: `"... (code)"`
- Zero working implementations

### **After (Enhanced):**
- ~10 critical files with full LLM-generated code
- ~30 normal files with template-based code
- ~13 low priority files auto-generated
- **Actual working code**

---

## ⚠️ Considerations

### **Token Usage:**
- Structure phase: 4K tokens
- Each critical file: 2K tokens
- Total for 10 files: ~24K tokens (acceptable)

### **Time:**
- Current: ~1 minute (all placeholders)
- Enhanced: ~3-5 minutes (actual code)
- Worth it: ✅ Yes!

### **LLM Calls:**
- Current: 1 call
- Enhanced: 1 + N calls (N = critical files)
- Cost: Higher but necessary

---

## 🎯 Success Criteria

✅ **Critical files contain actual implementations**
✅ **Code compiles/runs without errors**
✅ **No placeholder comments**
✅ **Quality gates pass**

---

## 📝 Implementation Steps

1. ✅ Analyze current behavior
2. Add `call_llm_raw()` method
3. Add `_generate_file_code()` method
4. Add `_generate_template()` helper
5. Add `_generate_config()` helper
6. Update `execute()` to use chunked generation
7. Test on small example
8. Re-run full Orchestrator

---

**Ready to implement!** 🚀

