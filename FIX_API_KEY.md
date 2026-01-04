# Fix: OpenAI API Key Error (401 Unauthorized)

## Error Message

```
HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 401 Unauthorized"
Error code: 401 - Incorrect API key provided
```

## What This Means

Your OpenAI API key is **invalid, expired, or incorrectly formatted**. The system is trying to use OpenAI for embeddings but the authentication is failing.

## Good News! ✅

**The system automatically handles this!** After this error, it will:
1. Try Perplexity (if you have that key)
2. Try Google Gemini (if you have that key)
3. Fall back to **local HuggingFace models** (no API key needed)

You should see this in your logs:
```
WARNING:utils:OpenAI embeddings failed: ...
WARNING:utils:langchain-perplexity not installed. Trying Google Gemini...
WARNING:utils:Google Gemini embeddings failed: ...
INFO:utils:Successfully loaded HuggingFace BGE embeddings
```

## Solutions

### Option 1: Use Local Models (Recommended - No API Keys Needed)

**Just remove or don't set the OpenAI API key:**

```bash
# Remove the invalid key from .env file
# Or unset the environment variable
unset OPENAI_API_KEY
```

The system will automatically use HuggingFace local models, which work perfectly fine!

### Option 2: Fix Your OpenAI API Key

#### Step 1: Get a Valid API Key

1. Go to: https://platform.openai.com/api-keys
2. Sign in to your OpenAI account
3. Click "Create new secret key"
4. Copy the key (it starts with `sk-proj-` or `sk-`)

#### Step 2: Update Your API Key

**Method A: Update .env file**
```bash
# Edit .env file
nano .env
# or
vim .env
```

Update the line:
```env
OPENAI_API_KEY=sk-proj-YOUR_NEW_VALID_KEY_HERE
```

**Method B: Set environment variable**
```bash
export OPENAI_API_KEY="sk-proj-YOUR_NEW_VALID_KEY_HERE"
```

**Method C: Remove the key entirely (use local models)**
```bash
# Comment out or remove the line in .env:
# OPENAI_API_KEY=...
```

#### Step 3: Verify the Key

```bash
# Check if the key is set
echo $OPENAI_API_KEY

# Should show your key (starts with sk-proj- or sk-)
```

### Option 3: Check Your API Key Format

Valid OpenAI API keys:
- Start with `sk-proj-` (newer format)
- Or start with `sk-` (older format)
- Are about 50+ characters long
- Don't have spaces or extra characters

**Common mistakes:**
- ❌ Extra spaces: `sk-proj- abc123...`
- ❌ Missing characters: `sk-proj-abc...` (incomplete)
- ❌ Wrong prefix: `sk_` or `api-key-`
- ❌ Expired/revoked keys

## What Happens Next

After you fix (or remove) the API key:

1. **If you set a valid key:** System will use OpenAI embeddings
2. **If you remove the key:** System will use local HuggingFace models automatically

Both options work perfectly! Local models are:
- ✅ Free (no API costs)
- ✅ Private (no data sent to external services)
- ✅ Fast (runs on your machine)
- ✅ Reliable (no API rate limits)

## Verify It's Working

After fixing, run:
```bash
python main.py
```

You should see:
```
INFO:utils:Successfully loaded OpenAI embeddings
```
OR
```
INFO:utils:Successfully loaded HuggingFace BGE embeddings
```

Both are fine! ✅

## Quick Commands

```bash
# Check current API key
echo $OPENAI_API_KEY

# Remove invalid key (use local models)
unset OPENAI_API_KEY

# Set new valid key
export OPENAI_API_KEY="sk-proj-YOUR_VALID_KEY"

# Test the key (optional)
python -c "from langchain_openai import OpenAIEmbeddings; e = OpenAIEmbeddings(); print('✓ Valid key')"
```

## Summary

- **Error:** Invalid OpenAI API key
- **Impact:** None - system automatically falls back to local models
- **Fix:** Either get a valid key OR remove the key to use local models
- **Recommendation:** Use local models (no API costs, more private)

The system is designed to work without API keys! 🚀

