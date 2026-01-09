# 🚀 Configure Orchestrator to Use OpenAI API

**User has existing OpenAI subscription - let's use it!**

---

## 🎯 Quick Setup

### **Step 1: Get Your OpenAI API Key**

1. Go to https://platform.openai.com/api-keys
2. Copy your API key (or create new one)
3. Should look like: `sk-proj-...`

---

### **Step 2: Configure Orchestrator**

**Option A: Environment Variable (Recommended)**

Add to your `.env` file:
```bash
# In C:\Users\markm\OneDrive\SPECTRA\.env

# Orchestrator LLM Configuration
ORCHESTRATOR_LLM_URL=https://api.openai.com/v1/chat/completions
ORCHESTRATOR_LLM_API_KEY=sk-proj-YOUR-KEY-HERE
ORCHESTRATOR_LLM_MODEL=gpt-4o-mini
```

**Option B: Direct Config**

Edit `Core/orchestrator/src/orchestrator/llm_client.py`:
```python
# Line 41-46 (defaults)
self.api_url = api_url or os.getenv(
    "ORCHESTRATOR_LLM_URL", "https://api.openai.com/v1/chat/completions"
)
self.api_key = api_key or os.getenv("ORCHESTRATOR_LLM_API_KEY", "your-key")
self.model = model or os.getenv(
    "ORCHESTRATOR_LLM_MODEL", "gpt-4o-mini"
)
```

---

## 🎯 Model Recommendations

### **GPT-4o-mini** (Recommended) 🏆
- **Cost:** $0.15 input / $0.60 output per million tokens
- **Speed:** Very fast
- **Reliability:** ~90%
- **Cost per build:** ~$0.03
- **Best for:** Everything! Fast + cheap + reliable

### **GPT-4o** (If you need absolute best)
- **Cost:** $2.50 input / $10 output per million tokens
- **Speed:** Fast
- **Reliability:** ~95%
- **Cost per build:** ~$0.50
- **Best for:** Critical builds only

### **GPT-4 Turbo**
- **Cost:** $10 input / $30 output per million tokens
- **Speed:** Medium
- **Reliability:** ~95%
- **Cost per build:** ~$1.50
- **Best for:** Not worth it vs gpt-4o

---

## 💰 Cost Estimate (gpt-4o-mini)

**Typical service build:**
- Input: ~20K tokens (prompt + context)
- Output: ~5K tokens (code generation)
- **Cost:** ~$0.03 per build

**Monthly (assuming 100 builds):**
- **Total:** ~$3/month

**You're already paying for OpenAI, so this is basically free!** ✅

---

## 🔧 Implementation

**Let me update your config now!**

