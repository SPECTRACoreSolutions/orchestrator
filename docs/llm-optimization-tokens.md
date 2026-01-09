# LLM Token Optimization Guide

## What Are Tokens?

**Tokens are the unit of measurement for LLM input and output.**

### Technical Definition
- Tokens are chunks of text that the LLM processes
- Not characters, not words - **tokens**
- The model sees tokens, not raw text
- Input is tokenized → Model processes → Output is detokenized

### Rough Conversions (English Text)
- **1 token ≈ 4 characters** (rough average)
- **1 token ≈ 0.75 words** (rough average)
- Examples:
  - "Hello" = 1 token
  - "Hello, world!" = 3 tokens
  - "A centralized logging service" = 6 tokens
  - This sentence = ~15 tokens

### Why Tokens Matter

**1. Context Window Limits**
- Every LLM has a maximum context window (total tokens)
- Input tokens + Output tokens ≤ Context Window
- Example: Mistral-7B-Instruct has ~8k token context window
- If you use 7k tokens for input, you only have ~1k tokens for output

**2. Cost/Billing (for commercial APIs)**
- OpenAI charges per token (input + output)
- Different rates for input vs output
- Example: GPT-4 might be $0.03 per 1k input tokens, $0.06 per 1k output tokens

**3. Performance**
- More tokens = slower processing
- Longer outputs take more time
- GPU memory limits affect how many tokens can be processed simultaneously

**4. Quality Control**
- Token limits prevent runaway responses
- Ensures responses stay focused
- Prevents infinite loops or overly verbose outputs

## Current Alana Configuration

### Model: Mistral-7B-Instruct-v0.3
- **Context Window**: ~8,000 tokens (8k)
- **Max Model Length** (vLLM setting): 2,048 tokens
- **Max Sequences**: 16 concurrent requests
- **GPU Memory**: RTX 5090 (32GB VRAM), 85% utilization

### Current Orchestrator Settings
```python
# From discover.py
model_context_chars = 8000 * 4  # ~32k chars (actually 8k tokens)
max_response_tokens = min(4096, available_for_response)
```

**Problem**: We're trying to get 4096 tokens of output, but:
- Input prompt is ~2000-4000 tokens
- Context window is only 8k tokens
- 8k - 4k input = only 4k available for output ✅ (this works!)
- BUT: vLLM `--max-model-len 2048` limits us to 2048 tokens total!

**The Real Limit**: vLLM's `--max-model-len 2048` is the bottleneck!

## Understanding Our Token Budget

### Token Budget Breakdown

**Total Available**: 8,000 tokens (Mistral context window)

**Used for Input**:
- System prompt: ~1,500 tokens
- User message: ~500 tokens
- Context (specification, manifest, history): ~1,000 tokens
- **Total Input**: ~3,000 tokens

**Available for Output**: 8,000 - 3,000 = **5,000 tokens**

**BUT**: vLLM `--max-model-len 2048` means:
- Total sequence length (input + output) ≤ 2,048 tokens
- With 3,000 token input, we can't fit any output!

**This is why responses are truncated!**

## Solution: Increase vLLM max-model-len

### Option 1: Increase to Full Context Window (Recommended)

```yaml
# docker-compose.yml
command: >
  vllm serve mistralai/Mistral-7B-Instruct-v0.3
  --dtype auto
  --api-key token-irrelevant
  --port 8000
  --max-model-len 8192  # Use full 8k context window
  --tensor-parallel-size 1
  --host 0.0.0.0
  --max-num-seqs 8  # Reduce from 16 (trade-off: less concurrent, but more tokens per request)
  --gpu-memory-utilization 0.90  # Increase from 0.85
```

**Benefits**:
- Can fit 3k input + 5k output = 8k total ✅
- Comprehensive discovery responses
- All discovery dimensions fully explored

**Trade-offs**:
- Slightly less concurrent requests (8 vs 16)
- Slightly more GPU memory usage (90% vs 85%)

### Option 2: Optimize Input Size (Alternative)

Reduce input tokens to fit within current 2048 limit:
- Shorter system prompt: ~800 tokens
- Minimal context: ~500 tokens
- Total input: ~1,300 tokens
- Available output: ~700 tokens

**Not recommended** - We lose context and quality!

### Option 3: Use Larger Model (Future)

For production, consider:
- **Mistral-7B-Instruct** (8k) ✅ Current
- **Mixtral-8x7B-Instruct** (32k) - Better for comprehensive discovery
- **Llama-2-70B** (4k) - More capable
- **GPT-4** (8k/32k) - Best quality, but requires API key

## Optimizing for Comprehensive Discovery

### Current Settings Analysis

**What We Have**:
```python
max_response_tokens = min(4096, available_for_response)
```

**What We Need**:
- Comprehensive discovery = ~3000-4000 tokens
- All 10 dimensions fully explored
- Detailed problem analysis
- Complete stakeholder analysis
- Full requirements breakdown
- Comprehensive risk assessment

**Recommended Settings**:

```python
# From discover.py - OPTIMIZED
model_context_tokens = 8000  # Mistral context window
prompt_tokens_estimate = (len(system_prompt) + len(user_message)) // 4  # Rough estimate

# Reserve 1000 tokens buffer for safety
available_for_response = model_context_tokens - prompt_tokens_estimate - 1000

# For comprehensive discovery, we need substantial output
max_response_tokens = min(4096, max(2000, available_for_response))

# Log for debugging
logger.info(f"Token budget: {model_context_tokens} total, ~{prompt_tokens_estimate} input, {max_response_tokens} available for output")
```

### Prompt Optimization

**Current**: ~4000 character system prompt = ~1000 tokens

**Optimized**: 
- Remove redundancy
- Use bullet points instead of paragraphs
- Summarize history more aggressively
- **Target**: ~2000 characters = ~500 tokens

**Benefit**: More tokens available for comprehensive output

## Token Usage Monitoring

### Why Measure Tokens?

**1. Cost Management** (for commercial APIs)
- Track usage per request
- Budget planning
- Identify expensive operations

**2. Performance Optimization**
- Identify bottlenecks
- Optimize prompts
- Balance input vs output

**3. Quality Control**
- Ensure responses aren't truncated
- Verify comprehensive outputs
- Detect context window issues

### How to Monitor

```python
# Add to llm_client.py
async def chat_completion(self, system_prompt, user_message, max_tokens):
    # Estimate input tokens
    input_text = system_prompt + user_message
    estimated_input_tokens = len(input_text) // 4
    
    # Make request
    response = await self.client.post(...)
    data = response.json()
    
    # Extract usage (if API provides it)
    usage = data.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", estimated_input_tokens)
    completion_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
    
    logger.info(f"Token usage: {prompt_tokens} input + {completion_tokens} output = {total_tokens} total")
    
    return response
```

## Recommendations for Alana

### Immediate Fix (Required)

**1. Increase vLLM max-model-len**:
```yaml
--max-model-len 8192  # Use full context window
```

**2. Optimize max_tokens calculation**:
```python
# Use full available budget
max_response_tokens = min(4096, model_context_tokens - prompt_tokens_estimate - 1000)
```

**3. Add token monitoring**:
- Log token usage per request
- Track when we hit limits
- Monitor for truncation

### Medium Term (Quality Improvements)

**1. Prompt optimization**:
- Reduce system prompt from ~4000 to ~2000 chars
- More concise instructions
- Aggressive history summarization

**2. Context optimization**:
- Only include relevant context
- Summarize specifications more
- Limit history to essential entries

**3. Response structure guidance**:
- Explicitly request comprehensive responses
- Guide LLM to use full token budget
- Request specific detail levels

### Long Term (Infrastructure)

**1. Consider larger model**:
- Mixtral-8x7B (32k context) for comprehensive discovery
- Better quality for complex analysis

**2. Fine-tuning**:
- Train on SPECTRA discovery examples
- Optimize for comprehensive outputs
- Reduce prompt size through learned patterns

## Summary

**Tokens = Measurement Unit for LLM Usage**

- **Input tokens**: Your prompt (system + user message + context)
- **Output tokens**: LLM's response
- **Total tokens**: Input + Output (must fit in context window)

**Current Issue**: 
- vLLM `--max-model-len 2048` is too restrictive
- We need 3k input + 4k output = 7k tokens
- **Solution**: Increase to 8192 (full context window)

**Why Tokens Exist**:
1. Context window limits (technical)
2. Billing/usage tracking (commercial)
3. Performance optimization (speed)
4. Quality control (focused responses)

**For Comprehensive Discovery**:
- Need ~3000-4000 output tokens
- Requires full 8k context window
- Optimize prompts to reduce input size
- Monitor usage to ensure quality

---

**Next Steps**:
1. Update docker-compose.yml `--max-model-len 8192`
2. Restart Alana
3. Test discovery with full token budget
4. Monitor token usage
5. Optimize prompts for efficiency

