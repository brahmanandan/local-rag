# 🚀 Ollama Setup Guide - DeepSeek-R1:14b

## Current Status ✅

**Ollama Service**: Running at `http://127.0.0.1:11434`

**Available Models**:
```
DeepSeek-R1:14b (PRIMARY) - Advanced reasoning, 9.0 GB
qwen2.5-coder:14b (Fallback) - Code-focused, 9.0 GB  
qwen2.5-coder:7b (Fallback) - Lighter coder, 4.7 GB
nomic-embed-text:latest (Embeddings) - 274 MB
```

---

## Configuration ✅

### config.yaml - Updated
Your `config.yaml` now includes:
```yaml
ollama:
  models: 
    - "DeepSeek-R1:14b"     # Primary
    - "qwen2.5-coder:14b"   # Fallback 1
    - "qwen2.5-coder:7b"    # Fallback 2
    - "llama2"              # Fallback 3
    - "mistral"             # Fallback 4
  temperature: 0.2
  timeout: 60
```

### How It Works

1. **Primary Model**: `DeepSeek-R1:14b`
   - Advanced reasoning capabilities
   - Optimized for complex queries
   - Better for document analysis
   - ~14B parameters, Q4_K_M quantized

2. **Automatic Fallbacks**:
   - If DeepSeek fails → tries qwen2.5-coder:14b
   - If that fails → tries qwen2.5-coder:7b
   - If all fail → tries legacy models

3. **Timeout**: 60 seconds per request

---

## Testing Your Setup

### 1. Verify Ollama is Running
```bash
curl http://127.0.0.1:11434/api/tags
```

Expected: Shows list of available models (should see DeepSeek-R1:14b)

### 2. Test DeepSeek-R1:14b Directly
```bash
curl -X POST http://127.0.0.1:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "DeepSeek-R1:14b",
    "prompt": "What is RAG?",
    "stream": false
  }'
```

### 3. Test with Python
```python
from utils import get_llm_model

llm = get_llm_model()
print(f"LLM loaded: {llm}")

response = llm.invoke("Explain RAG in 100 words")
print(response)
```

### 4. Run Full RAG Chatbot
```bash
# Index documents
python main.py

# Launch chat interface
streamlit run rag_cli.py
```

---

## Performance Expectations

### Model: DeepSeek-R1:14b
- **Response Time**: 5-30 seconds (depending on query complexity)
- **Memory Usage**: ~10-12 GB VRAM
- **Accuracy**: Very high (enterprise-grade)
- **Best For**: Complex reasoning, multi-step analysis

### Model: qwen2.5-coder:14b (Fallback)
- **Response Time**: 3-15 seconds
- **Memory Usage**: ~10 GB VRAM
- **Accuracy**: High
- **Best For**: Code understanding, programming questions

### Model: qwen2.5-coder:7b (Fallback)
- **Response Time**: 2-10 seconds
- **Memory Usage**: ~5-6 GB VRAM
- **Accuracy**: Good
- **Best For**: Lightweight inference, coding

---

## Environment Setup

### .env File Configuration

Your `.env` file is already set up correctly. It contains:
```properties
USER_AGENT="rag-chatbot/1.0 (brahmanandan@gmail.com)"
OPENAI_API_KEY="sk-proj-..."        # For API fallback
PERPLEXITY_API_KEY="pplx-..."       # For API fallback
GOOGLE_API_KEY="AIzaSy..."          # For API fallback
```

**Note**: Ollama doesn't require API keys - it runs locally.

---

## Troubleshooting

### Issue: "Connection refused" error
**Solution**: Start Ollama
```bash
ollama serve
# Or on macOS, open the Ollama app
```

### Issue: "Model not found"
**Solution**: Pull the model
```bash
ollama pull DeepSeek-R1:14b
```

### Issue: "Out of memory" error
**Solution**: Use smaller model
```yaml
# In config.yaml, move qwen2.5-coder:7b to top of list
models:
  - "qwen2.5-coder:7b"    # Lighter model
  - "DeepSeek-R1:14b"     # Fallback to heavier model
```

### Issue: Slow responses
**Solution**: Check system load
```bash
# macOS
top -l 1 | head -20

# If CPU-bound: Use smaller model
# If GPU-bound: Clear other applications
```

---

## API Fallback Chain

If Ollama fails, the system automatically tries in this order:
1. ✅ **Ollama** (DeepSeek-R1:14b) - Your primary
2. ✅ **Ollama** (qwen2.5-coder:14b) - Your fallback
3. ✅ **Ollama** (qwen2.5-coder:7b) - Your fallback
4. ✅ **OpenAI** (gpt-3.5-turbo) - Cloud API
5. ✅ **Perplexity** (mistral-7b-instruct) - Cloud API
6. ✅ **Google Gemini** (gemini-1.5-flash) - Cloud API
7. ✅ **HuggingFace** (TinyLlama) - Cloud models
8. ✅ **llama.cpp** (GGUF models) - Local files

---

## Configuration Priority (LLM_PRIORITY in config.yaml)

```yaml
LLM_PRIORITY:
  - ollama          # ← Your local models
  - llama_cpp       
  - huggingface     
  - openai          
  - perplexity      
  - google          
```

This ensures Ollama is tried first, maximizing local inference.

---

## Quick Commands

### Run the Full RAG System
```bash
# 1. Index documents
python main.py

# 2. Launch chat
streamlit run rag_cli.py

# 3. Ask questions in the web interface
```

### Test Individual Components
```bash
# Test embeddings
python -c "from utils import get_embeddings_model; print(get_embeddings_model())"

# Test LLM
python -c "from utils import get_llm_model; llm = get_llm_model(); print(llm.invoke('test'))"

# Test Ollama connection
curl http://127.0.0.1:11434/api/tags | jq '.models[0].name'
```

### Monitor Ollama Usage
```bash
# Check running models
ps aux | grep ollama

# Check Ollama logs (macOS)
tail -f ~/.ollama/logs/server.log

# Check memory usage
top -p $(pgrep -f "ollama serve")
```

---

## Advanced Configuration

### Custom Timeout
Edit `config.yaml`:
```yaml
ollama:
  timeout: 120  # Wait up to 2 minutes
```

### Custom Temperature (Creativity)
```yaml
ollama:
  temperature: 0.5  # Higher = more creative, Lower = more deterministic
```

Current: `0.2` (deterministic, good for RAG)
Recommended range: `0.0 - 0.5` (for Q&A tasks)

### Using Different Model by Default
```yaml
ollama:
  models:
    - "qwen2.5-coder:7b"      # Smaller, faster
    - "DeepSeek-R1:14b"       # Larger, smarter
```

---

## Performance Tuning

### For Faster Responses
1. Use `qwen2.5-coder:7b` (smaller model)
2. Reduce context length in RAG retrieval
3. Run on GPU if available

### For Better Quality
1. Use `DeepSeek-R1:14b` (larger model)
2. Keep temperature low (0.1-0.2)
3. Use full context in RAG retrieval

### For Lower Memory Usage
1. Use `qwen2.5-coder:7b`
2. Reduce batch size
3. Use 4-bit quantization (if available)

---

## System Information

### Your Setup
- **OS**: macOS
- **Ollama Status**: ✅ Running
- **Ollama Address**: http://127.0.0.1:11434
- **Primary Model**: DeepSeek-R1:14b (9.0 GB)
- **RAM Available**: Check with `vm_stat` on macOS

### Model Details

**DeepSeek-R1:14b**
- Architecture: Qwen2 family
- Parameters: 14.8B
- Quantization: Q4_K_M
- Size: 9.0 GB
- Modified: 4 days ago

---

## Next Steps

1. ✅ **Start Indexing** (if not done)
   ```bash
   python main.py
   ```

2. ✅ **Launch Chat Interface**
   ```bash
   streamlit run rag_cli.py
   ```

3. ✅ **Ask Questions**
   - Enter queries about your documents
   - See reasoning from DeepSeek-R1:14b
   - Get source document references

4. ✅ **Monitor Performance**
   - Check response times
   - Adjust temperature if needed
   - Switch models if needed

---

## Support

### Common Questions

**Q: Can I use a different model?**  
A: Yes, edit `config.yaml` and change the model names in the `ollama.models` list.

**Q: Why is the first request slow?**  
A: Model is loading into memory. Subsequent requests are faster.

**Q: Can I use multiple models simultaneously?**  
A: Currently uses one model. Parallel loading coming in future version.

**Q: How do I update the model?**  
A: Run `ollama pull DeepSeek-R1:14b` to get latest version.

**Q: What's the difference between Q4 and Q8 quantization?**  
A: Q4 is smaller/faster, Q8 is larger/more accurate. Q4_K_M is recommended.

---

## System Status Summary

| Component | Status | Details |
|-----------|--------|---------|
| **Ollama Service** | ✅ Running | http://127.0.0.1:11434 |
| **Primary Model** | ✅ Available | DeepSeek-R1:14b (9.0 GB) |
| **Fallback Models** | ✅ Available | qwen2.5-coder (14b & 7b) |
| **Config File** | ✅ Updated | config.yaml ready |
| **Environment** | ✅ Ready | .env configured |
| **RAG System** | ✅ Ready | Ready to use |

---

**Configuration Status**: ✅ Complete  
**Ready to Use**: ✅ Yes  
**Recommended Action**: Run `python main.py` then `streamlit run rag_cli.py`

Enjoy your local RAG system with DeepSeek-R1:14b! 🚀
