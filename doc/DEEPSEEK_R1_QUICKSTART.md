# ⚡ Quick Start - DeepSeek-R1:14b RAG

## 3 Steps to Launch ✅

### Step 1: Verify Ollama
```bash
curl http://127.0.0.1:11434/api/tags | jq '.models[0].name'
# Expected output: "DeepSeek-R1:14b"
```

### Step 2: Index Your Documents
```bash
python main.py
```

Expected output:
```
Docling converter initialized...
Starting to load documents...
Document loading complete:
  - Successfully processed: X files
  - Total documents loaded: X
FAISS index created successfully!
```

### Step 3: Launch Chat Interface
```bash
streamlit run rag_cli.py
```

Then open browser to: **http://localhost:8501**

---

## What Changed ✅

### config.yaml Updated
Your primary LLM is now **DeepSeek-R1:14b**:
```yaml
ollama:
  models: 
    - "DeepSeek-R1:14b"     # ← PRIMARY: Advanced reasoning
    - "qwen2.5-coder:14b"   # Fallback
    - "qwen2.5-coder:7b"    # Fallback
  temperature: 0.2
  timeout: 60
```

### Why DeepSeek-R1:14b?
- ✅ Advanced reasoning capabilities
- ✅ 14.8B parameters (enterprise-grade)
- ✅ Q4_K_M quantized (~9 GB)
- ✅ Best for document analysis & complex queries
- ✅ Automatic fallbacks if issues occur

---

## rag_cli.py Fixed ✅

Fixed import errors:
- ❌ "No module named 'langchain_core.chains'" - FIXED
- ❌ "No module named 'langchain.chains'" - FIXED
- ✅ Using LCEL (LangChain Expression Language) instead

Chain now built with:
- `ChatPromptTemplate` (from langchain_core)
- `RunnablePassthrough` (from langchain_core)
- `StrOutputParser` (from langchain_core)
- Pipe operator (`|`) for composition

---

## Configuration Files Ready ✅

| File | Status | Details |
|------|--------|---------|
| **config.yaml** | ✅ Updated | DeepSeek-R1:14b as primary |
| **rag_cli.py** | ✅ Fixed | Imports and chain building |
| **.env** | ✅ Ready | API keys configured |
| **OLLAMA_SETUP.md** | ✅ Created | Comprehensive guide |

---

## Testing Commands

### Test Ollama Connection
```bash
curl -X POST http://127.0.0.1:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "DeepSeek-R1:14b", "prompt": "test", "stream": false}' | jq .
```

### Test Python Import
```bash
python -c "from utils import get_llm_model; llm = get_llm_model(); print('✅ LLM Loaded:', type(llm).__name__)"
```

### Test Full Chain
```bash
python -c "
from rag_cli import load_chain
chain = load_chain()
print('✅ Chain loaded successfully')
"
```

---

## Expected Behavior

### First Launch
- Takes 10-30 seconds to load DeepSeek-R1:14b
- ~10-12 GB RAM used
- First query may take 30-60 seconds (model warmup)

### Subsequent Queries
- 5-20 seconds per query
- Consistent response time
- Better reasoning on complex questions

### Fallback Triggers
If DeepSeek fails, automatically tries:
1. qwen2.5-coder:14b
2. qwen2.5-coder:7b
3. Legacy Ollama models
4. Cloud APIs (if configured)

---

## Performance Tips

### For Faster Responses
```yaml
# In config.yaml, use smaller model
ollama:
  models:
    - "qwen2.5-coder:7b"       # ~4-10 sec responses
    - "DeepSeek-R1:14b"        # Fallback
```

### For Better Quality
```yaml
# Current setup (recommended)
ollama:
  models:
    - "DeepSeek-R1:14b"        # ~10-30 sec responses
    - "qwen2.5-coder:14b"      # Fallback
  temperature: 0.2             # Deterministic (good for RAG)
```

### For Memory Efficiency
```yaml
# On low-memory systems
ollama:
  models:
    - "qwen2.5-coder:7b"       # 4-6 GB RAM
    - "DeepSeek-R1:14b"        # Fallback
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Connection refused" | Run `ollama serve` |
| "Model not found" | Run `ollama pull DeepSeek-R1:14b` |
| "Out of memory" | Use `qwen2.5-coder:7b` (smaller model) |
| "Slow responses" | Check system load with `top` |
| "Python import error" | Run `python -m py_compile rag_cli.py` |

---

## Next Steps

### Immediate (5 min)
```bash
python main.py
streamlit run rag_cli.py
```

### First Queries
- Ask about your documents
- Test reasoning capabilities
- Note response times

### Optimization (Optional)
- Adjust temperature for different use cases
- Switch models if needed
- Monitor performance

---

## Files Reference

- **OLLAMA_SETUP.md** - Comprehensive setup guide
- **config.yaml** - Configuration file
- **rag_cli.py** - Streamlit chat interface
- **main.py** - Document indexing
- **utils.py** - Model loading logic

---

**Status**: ✅ Ready to Use  
**Primary Model**: DeepSeek-R1:14b  
**All Configuration**: Complete  

Run `python main.py` then `streamlit run rag_cli.py` to start! 🚀
