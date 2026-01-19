# API Key & Provider Troubleshooting Guide

## Issue Summary

You saw these errors in your logs:
```
INFO:httpx:HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 401 Unauthorized"
INFO:httpx:HTTP Request: POST https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent "HTTP/1.1 404 Not Found"
```

**This guide explains why these occur and how to fix them.**

---

## OpenAI 401 Error

### Root Cause
- **401 Unauthorized** means either:
  1. `OPENAI_API_KEY` is missing from `.env`
  2. `OPENAI_API_KEY` is invalid or expired
  3. Your OpenAI account has no active credits/billing

### How We Fixed It
- ✓ Updated `utils.py` to **skip OpenAI if `OPENAI_API_KEY` is not set** (no spurious 401 attempts)
- ✓ Added early `.env` loading to ensure keys are available before creating clients
- ✓ Reduced httpx logging to WARNING level (less noise in INFO logs)

### What You Should Do
**Option 1: Use Local Models Only (Recommended)**
- Comment out or remove OpenAI from `LLM_PRIORITY` in `config.yaml`:
  ```yaml
  LLM_PRIORITY:
    - ollama
    - llama_cpp
    - huggingface
    # - openai         # Skip cloud, use local only
  ```
- Install and start **Ollama**: https://ollama.ai
  ```bash
  ollama pull llama2
  ollama serve
  ```

**Option 2: Fix Your OpenAI Key**
1. Go to https://platform.openai.com/account/api-keys
2. Create or regenerate your API key
3. Update `.env`:
   ```dotenv
   OPENAI_API_KEY=sk-proj-YOUR_NEW_KEY_HERE
   ```
4. Restart your app

---

## Google Gemini 404 Error

### Root Cause (Complex!)
The 404 occurs due to **langchain-google-genai SDK compatibility**:
- The SDK routes all calls through **`/v1beta`** endpoint
- `/v1beta` only supports the deprecated `gemini-pro` model
- Newer models (`gemini-1.5-flash`, `gemini-1.5-pro`) are **not available** on `/v1beta`
- Result: **404 Not Found** even with a valid API key

### Why We Disabled Google by Default
- `config.yaml` now **comments out Google** from `LLM_PRIORITY`
- Local providers (Ollama, HuggingFace) are more reliable and don't have this issue

### How to Fix It (If You Want Google)

**Option 1: Upgrade langchain-google-genai (Best)**
```bash
pip install --upgrade langchain-google-genai
```
- Recent versions support multiple API versions
- Check the latest docs: https://github.com/langchain-ai/langchain-google

**Option 2: Use Older Gemini Model**
- Enable Google in `config.yaml`:
  ```yaml
  LLM_PRIORITY:
    # ... local models first ...
    - google
  ```
- Update `config.yaml` model name to:
  ```yaml
  MODELS:
    google:
      llm_model: "gemini-pro"  # Use legacy model that v1beta supports
      embedding_model: "models/embedding-001"
  ```
- Note: `gemini-pro` is **older and slower** than `gemini-1.5-*`

**Option 3: Use Local Models (Recommended)**
- Stick with Ollama + `gemini-1.5-*` is NOT needed
- Install Ollama:
  ```bash
  ollama pull llama2
  ollama pull mistral
  ollama serve
  ```
- The system will automatically find and use Ollama models

---

## Google Embeddings 404

### Same Issue
The Gemini embeddings endpoint has the same routing problem.

### Solution
- ✓ System already falls back to **HuggingFace BGE embeddings** first (top of `EMBEDDINGS_PRIORITY`)
- ✓ Google is lower priority, so local models are used
- No action needed; the fallback works automatically

---

## How the System Handles These Now

### Flow for LLM Selection
```
Try LLM providers in order:
1. Ollama (LOCAL) ✓ No API key needed
   ├─ DeepSeek-R1, Qwen, Llama, Mistral, etc.
   └─ If running, succeeds. If not, tries next.

2. llama.cpp (LOCAL) ✓ No API key needed
   ├─ Loads GGUF models from disk
   └─ If files exist, succeeds. If not, tries next.

3. HuggingFace (LOCAL) ✓ No API key needed
   ├─ TinyLlama, DialoGPT, GPT-2, etc.
   └─ Always available; smallest fallback

4. OpenAI (CLOUD) ⚠️ Requires valid OPENAI_API_KEY
   ├─ If key missing → skipped (no 401 attempt)
   ├─ If key invalid → raises error → tries next
   └─ If key valid & quota available → success ✓

5. Perplexity (CLOUD) ⚠️ Requires valid PERPLEXITY_API_KEY
   └─ Similar to OpenAI flow

6. Google (CLOUD) ✓ Now commented out (SDK issue)
   └─ Re-enable after upgrading langchain-google-genai
```

### Flow for Embeddings Selection
```
Try embeddings providers in order:
1. HuggingFace BGE (LOCAL) ✓ No API key needed
   └─ BAAI/bge-small-en-v1.5 (high quality, fast)

2. HuggingFace (LOCAL) ✓ No API key needed
   └─ sentence-transformers/all-MiniLM-L6-v2

3. OpenAI (CLOUD) ⚠️ Requires valid OPENAI_API_KEY
   └─ text-embedding-ada-002

4. Perplexity (CLOUD) ⚠️ Requires valid PERPLEXITY_API_KEY

5. Google (CLOUD) ⚠️ Requires valid GOOGLE_API_KEY
   └─ Now has fallback for multiple model IDs
```

---

## Environment File (.env)

### Required Format
```dotenv
# Required for OpenAI LLM and embeddings
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE

# Required for Perplexity
PERPLEXITY_API_KEY=pplx-YOUR_KEY_HERE

# Required for Google (deprecated due to SDK issues, but still works with gemini-pro)
GOOGLE_API_KEY=AIzaSy-YOUR_KEY_HERE

# User agent (optional)
USER_AGENT=rag-chatbot/1.0
```

### Validation
```bash
# Check if .env is being read
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('OPENAI_API_KEY:', bool(os.getenv('OPENAI_API_KEY')))"
```

---

## Quick Diagnostics

### 1. Check if keys are loaded
```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); \
  print('OpenAI:', bool(os.getenv('OPENAI_API_KEY'))); \
  print('Google:', bool(os.getenv('GOOGLE_API_KEY'))); \
  print('Perplexity:', bool(os.getenv('PERPLEXITY_API_KEY')))"
```

### 2. Check which LLM model loads
```bash
python -c "from utils import get_llm_model; llm=get_llm_model(); print('LLM type:', type(llm).__name__)"
```

### 3. Check which embeddings model loads
```bash
python -c "from utils import get_embeddings_model; emb=get_embeddings_model(); print('Embeddings type:', type(emb).__name__)"
```

### 4. Test with Ollama (if installed)
```bash
# Ensure Ollama is running
ollama serve

# In another terminal, test connection
python -c "from langchain_ollama import ChatOllama; llm=ChatOllama(model='llama2'); print(llm.invoke('ping'))"
```

---

## Recommended Setup

### For Maximum Reliability (Recommended)
Use **local models only** with Ollama:
```yaml
# config.yaml
LLM_PRIORITY:
  - ollama          # ✓ Reliable, fast, no API limits
  - llama_cpp       # ✓ Fallback local
  - huggingface     # ✓ Fallback local
  # Skip cloud providers (no credentials needed, no API call limits)
```

### For Cloud + Local Hybrid
Use cloud for embeddings, local for LLM:
```yaml
EMBEDDINGS_PRIORITY:
  - huggingface_bge # ✓ Fast local
  - openai          # Cloud backup if BGE unavailable
  
LLM_PRIORITY:
  - ollama          # ✓ Local
  - openai          # ✓ Cloud with valid API key
```

### For Full Cloud (Advanced)
Set valid API keys in `.env` and keep all providers in priority.

---

## Getting Help

| Problem | Solution |
|---------|----------|
| 401 Unauthorized (OpenAI) | Check/update `OPENAI_API_KEY` in `.env` or comment out OpenAI from config |
| 404 Not Found (Gemini) | Use local models or upgrade `pip install --upgrade langchain-google-genai` |
| No embeddings available | Install HuggingFace: `pip install sentence-transformers` |
| No LLM available | Install Ollama (https://ollama.ai) or use HuggingFace models locally |
| Slow responses | Use Ollama with smaller models (`ollama pull orca-mini`, `ollama pull qwen:3.5b`) |

---

## Next Steps

1. **Start Ollama** (if not running):
   ```bash
   ollama serve
   ```

2. **Rebuild index** (optional):
   ```bash
   python main.py
   ```

3. **Start the app**:
   ```bash
   streamlit run rag_cli.py
   ```

Done! The system now gracefully falls back through providers and avoids spurious 401/404 logs.
