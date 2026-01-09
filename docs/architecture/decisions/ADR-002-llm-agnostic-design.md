# ADR-002: LLM-Agnostic Design

**Status**: Accepted  
**Date**: 2026-01-06  
**Deciders**: Architecture Team

---

## Context

SPECTRA uses a local LLM (Alana) running via vLLM, but may want to:
- Switch to different LLMs (OpenAI, Anthropic, etc.)
- Support "company as code" where different LLMs can be used
- Test with different models

---

## Decision

Use OpenAI-compatible API format for LLM client. This enables:
- Local LLM (Alana via vLLM)
- Cloud APIs (OpenAI, Anthropic via proxy)
- Any OpenAI-compatible endpoint

Configuration via environment variables:
- `ORCHESTRATOR_LLM_URL`
- `ORCHESTRATOR_LLM_API_KEY`
- `ORCHESTRATOR_LLM_MODEL`

---

## Consequences

### Positive

- **Flexibility**: Can use any OpenAI-compatible LLM
- **Portability**: Works across different LLM providers
- **Testing**: Easy to switch LLMs for testing
- **Company as Code**: Supports different LLM backends

### Negative

- **API Compatibility**: Limited to OpenAI-compatible APIs
- **Feature Parity**: Some LLM-specific features may not be available

---

## Implementation

`LLMClient` uses httpx to call OpenAI-compatible API:

```python
class LLMClient:
    def __init__(
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_url = api_url or os.getenv(
            "ORCHESTRATOR_LLM_URL", 
            "http://localhost:8001/v1/chat/completions"
        )
```

---

## Notes

OpenAI API format is widely adopted (vLLM, Anthropic proxy, etc.), making this a good standard.

