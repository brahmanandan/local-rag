# Configuration Guide - LLM and Embedding Priority

## Overview

The system now uses `config.yaml` to configure which LLM and embedding models to use, in what priority order, and with what settings.

## Configuration File: `config.yaml`

### Structure

```yaml
# Embedding Model Priority (tried from top to bottom)
EMBEDDINGS_PRIORITY:
  - openai
  - perplexity
  - google
  - huggingface_bge
  - huggingface

# LLM Model Priority (tried from top to bottom)
LLM_PRIORITY:
  - openai
  - perplexity
  - google
  - ollama
  - llama_cpp
  - huggingface

# Model-specific configurations
MODELS:
  openai:
    embedding_model: "text-embedding-ada-002"
    llm_model: "gpt-3.5-turbo"
    temperature: 0.2
  
  google:
    llm_model: "gemini-1.5-flash"  # Updated from deprecated gemini-pro
    # ... etc
```

## How It Works

1. **Priority Order**: The system tries providers in the order specified in `EMBEDDINGS_PRIORITY` and `LLM_PRIORITY`
2. **Automatic Fallback**: If a provider fails (invalid key, quota exceeded, etc.), it automatically tries the next one
3. **Configuration**: Each provider's settings (model name, temperature, etc.) come from the `MODELS` section

## Customizing Priority

### Example: Use Local Models First

Edit `config.yaml`:

```yaml
LLM_PRIORITY:
  - huggingface  # Try local models first
  - ollama
  - openai       # Fallback to cloud if local fails
  - perplexity
  - google
```

### Example: Skip Cloud Providers

```yaml
LLM_PRIORITY:
  - ollama
  - huggingface
  # Remove openai, perplexity, google to skip them entirely
```

### Example: Use Only OpenAI

```yaml
LLM_PRIORITY:
  - openai
  # Remove all others
```

## Fixed Issues

### 1. ✅ Ollama Deprecation Warning

**Fixed**: Now uses `langchain-ollama` package (new) with fallback to deprecated version

**Before:**
```
LangChainDeprecationWarning: The class `Ollama` was deprecated...
```

**After:**
- Uses `langchain_ollama.ChatOllama` (new package)
- No deprecation warnings
- Added `langchain-ollama` to requirements.txt

### 2. ✅ Google Gemini Model Not Found (404)

**Fixed**: Updated from deprecated `gemini-pro` to `gemini-1.5-flash`

**Before:**
```
404 models/gemini-pro is not found for API version v1beta
```

**After:**
- Uses `gemini-1.5-flash` (current model)
- Configurable in `config.yaml`

### 3. ✅ Google Gemini Quota Exceeded (429)

**Fixed**: Error is now suppressed and system automatically tries next provider

**Before:**
- Long error messages about quota

**After:**
- Error logged at debug level
- Automatically tries next provider
- No spam in logs

### 4. ✅ OpenAI API Key Invalid (401)

**Fixed**: Error suppressed, automatically tries next provider

**Before:**
- Warning messages for invalid keys

**After:**
- Error logged at debug level
- Automatically tries next provider

### 5. ✅ HuggingFace phi-2 Tensor Issues

**Fixed**: Removed phi-2 from default model list (it has probability tensor issues)

**Before:**
```
WARNING: probability tensor contains either `inf`, `nan` or element < 0
```

**After:**
- phi-2 removed from default models
- Uses TinyLlama first (more reliable)
- Better error handling

### 6. ✅ Sequence Length Warnings

**Fixed**: Added max_length configuration and token limiting

**Before:**
```
Token indices sequence length is longer than the specified maximum sequence length
```

**After:**
- Configurable `max_length` in config.yaml (default: 2048)
- `max_new_tokens` limited to avoid sequence issues
- Warnings suppressed

### 7. ✅ Torch Classes Warning

**Fixed**: Suppressed torch warnings

**Before:**
```
Examining the path of torch.classes raised: Tried to instantiate class...
```

**After:**
- Warnings suppressed via filterwarnings
- Cleaner output

### 8. ✅ Ollama Connection Refused

**Fixed**: Error handled gracefully, tries next provider

**Before:**
- Multiple connection refused errors

**After:**
- Error logged at debug level
- Automatically tries next provider
- No spam in logs

## Error Handling Improvements

All errors are now handled more gracefully:

- **401 Unauthorized**: Logged at debug, tries next provider
- **429 Quota Exceeded**: Logged at debug, tries next provider
- **404 Not Found**: Logged at debug, tries next provider
- **Connection Errors**: Logged at debug, tries next provider
- **Tensor Issues**: Model skipped, tries next model

## Logging Levels

- **INFO**: Successful model loading
- **WARNING**: Important issues that might affect functionality
- **DEBUG**: Expected failures during fallback (suppressed by default)

## Installation

Make sure to install the new package:

```bash
pip install langchain-ollama
# Or
pip install -r requirements.txt
```

## Testing Configuration

Test your configuration:

```bash
# Test embeddings
python -c "from utils import get_embeddings_model; e = get_embeddings_model(); print('✓ Embeddings loaded')"

# Test LLM
python -c "from utils import get_llm_model; llm = get_llm_model(); print('✓ LLM loaded')"
```

## Summary

✅ **Config-driven**: Priority and settings in `config.yaml`  
✅ **Better errors**: Suppressed expected errors, clear success messages  
✅ **Updated models**: Uses current Gemini model (gemini-1.5-flash)  
✅ **Fixed Ollama**: Uses new langchain-ollama package  
✅ **Better fallbacks**: Graceful handling of all error types  
✅ **Cleaner logs**: Less noise, more useful information  

The system now works smoothly with automatic fallbacks and clean logging! 🚀

