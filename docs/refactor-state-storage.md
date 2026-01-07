# Orchestrator State Storage Refactoring

## Summary

Refactored orchestrator to use SPECTRA-grade document structure, following the Service Blueprint specification. Orchestrator now stores its internal state in its own repository (`Core/orchestrator/.orchestrator/`) instead of the workspace root (`.spectra/`).

## Changes

### 1. Orchestrator State Storage

**Before:**
- Manifests: `.spectra/manifests/`
- History: `.spectra/history/`
- Cache: `.spectra/cache/`

**After:**
- Manifests: `Core/orchestrator/.orchestrator/manifests/`
- History: `Core/orchestrator/.orchestrator/history/`
- Cache: `Core/orchestrator/.orchestrator/cache/`

**Rationale:**
- Orchestrator is its own repository with its own state
- `.spectra/` remains as workspace marker (for solution-engine compatibility)
- Each tool/service manages its own state in its own repo

### 2. Specification Storage

**Before:**
- Specifications stored in `.spectra/specifications/` with naming: `{service}-specification.yaml`

**After:**
- Specifications stored in service directories following Service Blueprint: `{org}/{service}/{service}.specification.yaml`
- Example: `Core/monitoring/monitoring.specification.yaml`

**Rationale:**
- Follows SPECTRA Service Blueprint structure
- Service owns its specification
- Easier to locate and version with service code

### 3. Document Structure Metadata

Added `document_structure` field to `Specification` dataclass:

```yaml
document_structure:
  base_path: "Core/monitoring"
  org_folder: "Core"
  specification: "monitoring.specification.yaml"
  discovery:
    base_path: "docs/discovery"
    documents:
      - "01-problem-statement.md"
      - "02-discovery-report.md"
      - "portfolio.md"
```

This metadata:
- Records where documents are stored
- Enables service catalog to link to documents
- Supports PDF generation and GitHub README integration

### 4. Discovery Documents Location

**Before:**
- Discovery documents in `.spectra/docs/discovery/`

**After:**
- Discovery documents in `{org}/{service}/docs/discovery/`
- Example: `Core/monitoring/docs/discovery/01-problem-statement.md`

**Rationale:**
- Client-facing documents belong with the service
- Service catalog can link directly to service docs
- Documents versioned with service code

### 5. Workspace Detection

**Before:**
- Primary: `.spectra` marker
- Fallback: `Core/` directory

**After:**
- Primary: `Core/` directory structure
- Fallback: `.spectra` marker (for solution-engine compatibility)

**Rationale:**
- `Core/` structure is more reliable (always exists)
- `.spectra` is just a marker file
- Still compatible with legacy solution-engine

## File Structure

### Orchestrator Repository
```
Core/orchestrator/
├── .orchestrator/              # Orchestrator internal state (gitignored)
│   ├── manifests/             # Activity execution manifests
│   ├── history/               # Activity execution history
│   └── cache/                 # Temporary cache
├── src/orchestrator/
│   ├── context.py             # Updated to use orchestrator state dir
│   ├── activities/
│   │   └── discover.py        # Updated to save to service directories
│   └── service_locator.py     # Updated specification path method
└── .gitignore                 # Added .orchestrator/
```

### Service Directory (Example)
```
Core/monitoring/
├── monitoring.specification.yaml    # Specification (Service Blueprint)
├── docs/
│   └── discovery/                   # Discovery portfolio
│       ├── 01-problem-statement.md
│       ├── 02-discovery-report.md
│       └── portfolio.md
└── README.md
```

## Code Changes

### `context.py`
- Added `_find_orchestrator_dir()` method
- Added `orchestrator_state_dir` property
- Updated `load_manifest()` to use orchestrator state dir
- Updated `load_history()` to use orchestrator state dir
- Updated `load_specification()` to prefer service directories

### `service_locator.py`
- Updated `get_specification_path()` to return single path (service directory)
- Removed `.spectra/` fallback from specification path

### `discover.py`
- Updated manifest save location to orchestrator state dir
- Updated history save location to orchestrator state dir
- Updated specification save to service directory only
- Added `document_structure` metadata to specification
- Updated document generation to use service directories

### `state.py`
- Added `document_structure` field to `Specification` dataclass
- Updated `to_dict()` to include `document_structure`

## Benefits

1. **SPECTRA-Grade Structure**: Follows Service Blueprint specification
2. **Separation of Concerns**: Orchestrator state separate from service artifacts
3. **Codebase Awareness**: Documents stored in correct service directories
4. **Service Ownership**: Services own their specifications and documents
5. **Version Control**: Service docs versioned with service code
6. **Service Catalog Ready**: Document structure metadata enables catalog integration

## Migration Notes

- Existing manifests/history in `.spectra/` will be loaded (legacy fallback)
- New executions will use orchestrator state dir
- Specifications should be manually migrated from `.spectra/specifications/` to service directories if needed
- Discovery documents should be migrated from `.spectra/docs/discovery/` to service directories

## Testing

Tested with:
```python
from orchestrator.context import ContextBuilder
from orchestrator.service_locator import ServiceLocator

cb = ContextBuilder()
print('Orchestrator state dir:', cb.orchestrator_state_dir)
# Output: C:\Users\markm\OneDrive\SPECTRA\Core\orchestrator\.orchestrator

sl = ServiceLocator(cb.workspace_root)
spec_path = sl.get_specification_path('notifications', 'service')
print('Spec path:', spec_path)
# Output: C:\Users\markm\OneDrive\SPECTRA\Core\notifications\notifications.specification.yaml
```

✅ All paths resolve correctly
✅ Workspace detection works
✅ Service directories identified correctly

