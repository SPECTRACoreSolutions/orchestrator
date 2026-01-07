# Discovery Activity Gap Analysis

## Overview

This document compares the **Orchestrator Discover activity** (Alana-powered) with the **Solution-Engine Discover stage** to identify missing features and capabilities.

## Comparison Matrix

| Feature | Solution-Engine | Orchestrator | Status |
|---------|----------------|--------------|--------|
| **Service Name Extraction** | ✅ Pattern-based | ✅ LLM-powered | ✅ **Working** |
| **Service Name Validation** | ✅ Rules-based | ✅ Rules-based | ✅ **Working** |
| **Problem Statement Extraction** | ✅ Pattern-based | ⚠️ LLM (truncated) | ⚠️ **Partial** |
| **Idea Validation** | ✅ Yin-yang mapping | ✅ Validation JSON | ✅ **Working** |
| **Maturity Assessment** | ✅ In discover | ✅ Separate Assess activity | ✅ **OK** |
| **Registry Check** | ✅ Anti-duplication | ❌ Not implemented | ❌ **Missing** |
| **Discovery Game (7x7)** | ✅ 49 questions | ❌ Not implemented | ❌ **Missing** |
| **High-Level Design** | ✅ Extracted from game | ❌ Not implemented | ❌ **Missing** |
| **Problem Statement Doc** | ✅ Generated | ❌ Not implemented | ❌ **Missing** |
| **Proposed Approach Doc** | ✅ Generated | ❌ Not implemented | ❌ **Missing** |

## Detailed Feature Analysis

### ✅ Working Features

#### 1. Service Name Extraction & Validation
- **Solution-Engine**: Pattern-based extraction with validation rules
- **Orchestrator**: LLM-powered extraction with validation rules
- **Result**: Both work correctly. Orchestrator correctly identifies and normalizes service names (e.g., `portal`, `email`, `graph`, `assistant`)

#### 2. Idea Validation
- **Solution-Engine**: Yin-yang mapping (problem ↔ idea)
- **Orchestrator**: JSON validation structure with reasoning
- **Result**: Similar functionality, different structure. Orchestrator's approach is more flexible.

### ⚠️ Partial Features

#### 3. Problem Statement Extraction
- **Solution-Engine**: Pattern-based extraction with fallback logic
- **Orchestrator**: LLM extraction, but responses are truncated due to prompt size
- **Issue**: Prompt context is too large (9M+ chars), causing JSON truncation
- **Impact**: Problem statements are empty in orchestrator outputs
- **Fix Needed**: Optimize context loading, increase max_tokens, improve JSON parsing

### ❌ Missing Features

#### 4. Registry Check (Anti-Duplication)
**Solution-Engine Implementation:**
```python
# Checks service registry (Core/registries/service-catalog.yaml)
# Prevents duplicate services from being created
# Blocks if service exists and is healthy
# Allows redeploy if service is unhealthy
```

**What's Missing:**
- No registry integration in orchestrator
- No duplicate detection
- No service existence checks

**Recommendation:**
- Create `RegistryCheck` playbook or tool
- Integrate with service catalog
- Add to Discover activity or as separate validation step

#### 5. Discovery Game (7x7 - 49 Questions)
**Solution-Engine Implementation:**
- Runs 7x7 discovery game (49 questions across 7 dimensions)
- Generates comprehensive discovery document
- Uses SPECTRA 7x7 methodology

**What's Missing:**
- No discovery game framework
- No 7x7 methodology integration
- No comprehensive question-based discovery

**Recommendation:**
- Integrate discovery game as optional playbook/tool
- Allow Discover activity to choose when to run it
- Use LLM to determine if discovery game is needed

#### 6. High-Level Design Extraction
**Solution-Engine Implementation:**
- Extracts architecture from discovery game document
- Identifies technology stack
- Lists key components

**What's Missing:**
- No design extraction
- No architecture inference
- No technology stack identification

**Recommendation:**
- Add design extraction playbook
- Use LLM to infer architecture from discovery game or user input
- Generate high-level design structure

#### 7. Problem Statement Document Generation
**Solution-Engine Implementation:**
- Generates client-facing problem statement document
- Includes problem, impact, current state, pain points

**What's Missing:**
- No document generation
- No client-facing artifacts

**Recommendation:**
- Add document generation playbook
- Use LLM to generate professional problem statements
- Save to appropriate location (Data/{service}/source/)

#### 8. Proposed Approach Document Generation
**Solution-Engine Implementation:**
- Generates client-facing proposed approach document
- Includes solution overview, architecture, benefits

**What's Missing:**
- No document generation
- No solution proposal artifacts

**Recommendation:**
- Add document generation playbook
- Use LLM to generate professional proposals
- Integrate with high-level design

## Implementation Priority

### High Priority (Critical for MVP)
1. **Registry Check** - Prevents duplicate services
2. **Fix Problem Statement Extraction** - Currently broken due to truncation

### Medium Priority (Important for Production)
3. **Discovery Game Integration** - Comprehensive discovery
4. **High-Level Design Extraction** - Architecture understanding
5. **Document Generation** - Client-facing artifacts

### Low Priority (Nice to Have)
6. **Enhanced Validation** - More sophisticated validation logic
7. **Discovery History** - Track discovery patterns over time

## Recommended Approach

### Option 1: Playbook-Based (Recommended)
Make missing features available as playbooks that the Discover activity can choose to invoke:

```python
# Discover activity can invoke:
- registry_check playbook
- discovery_game playbook
- extract_design playbook
- generate_problem_statement playbook
- generate_proposed_approach playbook
```

**Pros:**
- Maintains AI autonomy (activity chooses tools)
- Flexible and composable
- Aligns with orchestrator architecture

**Cons:**
- LLM must decide when to use each tool
- May require prompt improvements

### Option 2: Always-Run Tools
Run certain tools (like registry check) automatically before LLM analysis:

```python
# Always run these first:
1. Registry check (block if duplicate)
2. Then LLM discovery
3. Then optional tools (discovery game, etc.)
```

**Pros:**
- Guarantees critical checks run
- Simpler decision making

**Cons:**
- Less flexible
- Hardcoded sequence

### Option 3: Hybrid
Critical checks (registry) run automatically, optional tools (discovery game) are playbooks:

```python
# Automatic:
- Registry check (block if duplicate)

# AI-chosen playbooks:
- Discovery game
- Design extraction
- Document generation
```

**Pros:**
- Best of both worlds
- Safety + flexibility

**Cons:**
- More complex implementation

## Next Steps

1. **Immediate**: Fix problem statement extraction (optimize context, increase max_tokens)
2. **Short-term**: Implement registry check (as automatic step or playbook)
3. **Medium-term**: Integrate discovery game as optional playbook
4. **Long-term**: Add document generation playbooks

## Test Results

From `compare_discovery_systems.py`:

**Service Name Accuracy**: 100% (4/4 services correctly identified)
- ✅ portal
- ✅ email  
- ✅ graph
- ✅ assistant

**Problem Statement**: 0% (all empty due to truncation)

**Idea Validation**: Partial (structure exists but content truncated)

## Conclusion

The Orchestrator Discover activity successfully extracts and validates service names, which was the primary goal. However, several features from solution-engine are missing:

1. **Critical**: Registry check (anti-duplication)
2. **Important**: Problem statement extraction (currently broken)
3. **Enhancement**: Discovery game, design extraction, document generation

The recommended approach is **Option 3 (Hybrid)**: run registry check automatically, then let the AI activity choose optional tools as playbooks. This maintains safety while preserving AI autonomy.


