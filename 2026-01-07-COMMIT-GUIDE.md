# Commit Guide - Discovery Portfolio Finalisation

**Date:** 2026-01-07  
**Session:** Discovery Portfolio Finalisation

---

## Repositories to Commit

### 1. Core/orchestrator

**Files to Commit:**
- `src/orchestrator/service_locator.py` (NEW)
- `src/orchestrator/document_generator.py` (MODIFIED - 8 new methods)
- `src/orchestrator/activities/discover.py` (MODIFIED - portfolio generation)
- `src/orchestrator/context.py` (MODIFIED - state management)
- `src/orchestrator/llm_client.py` (MODIFIED - timeout increase)
- `docs/DISCOVERY-PORTFOLIO-FINALISATION-2026-01-07.md` (NEW)
- `docs/QUICK-REFERENCE-DISCOVERY-PORTFOLIO.md` (NEW)
- `docs/discovery-portfolio-structure.md` (NEW)
- `.orchestrator/` directory (NEW - orchestrator state)

**Commit Message:**
```
feat(discover): Expand portfolio generation to 11 comprehensive documents

- Add ServiceLocator for codebase awareness and document placement
- Add 8 new document generation methods (current state, desired state, stakeholders, requirements, constraints, risks, alternatives, validation)
- Refactor orchestrator state to .orchestrator/ directory
- Expand discovery portfolio from 3 to 11 documents (~32 KB total)
- Increase LLM context window to 8192 and response tokens to 4096
- Increase HTTP timeouts to 600s for long LLM responses
- Update portfolio index to list all 11 documents
- Add comprehensive session documentation

BREAKING: Orchestrator state moved from .spectra/ to .orchestrator/
```

**Testing:**
```bash
cd Core/orchestrator
python -m orchestrator.cli discover "I need a test service"
# Verify 11 documents generated in {service_dir}/docs/discovery/
```

---

### 2. Core/labs/alana-llm

**Files to Commit:**
- `scripts/api_gateway.py` (MODIFIED - timeout increase)
- `docker/docker-compose.yml` (MODIFIED - context window increase)

**Commit Message:**
```
feat: Increase LLM capacity and timeouts for comprehensive responses

- Increase context window from 2048 to 8192 tokens
- Increase max-num-seqs from 4 to 8
- Increase HTTP timeout from 120s to 600s (10 minutes)
- Support longer, more comprehensive LLM responses
```

**Testing:**
- Restart Alana LLM service
- Verify no timeout errors during discovery runs

---

### 3. Core/memory

**Files to Commit:**
- `worklog/2026-01-07-discovery-portfolio-finalisation.md` (NEW)
- `lessons/process/discovery-portfolio-comprehensive-output.md` (NEW)
- `lessons/architecture/orchestrator-state-management.md` (NEW)

**Commit Message:**
```
docs: Add worklog and lessons for discovery portfolio finalisation

- Document comprehensive portfolio generation requirement
- Document orchestrator state management principles
- Add session summary with 7-dimensional scoring
```

---

## Commit Order

1. **Core/labs/alana-llm** (infrastructure changes first)
2. **Core/orchestrator** (main feature changes)
3. **Core/memory** (documentation last)

---

## Post-Commit Verification

1. Restart Alana LLM service
2. Run discovery test: `python -m orchestrator.cli discover "test service"`
3. Verify all 11 documents generated
4. Verify documents in correct location (`{service_dir}/docs/discovery/`)
5. Verify orchestrator state in `.orchestrator/` directory

---

**Status:** Ready to commit  
**Testing:** Required before production use

