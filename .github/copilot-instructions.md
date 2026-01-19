# Copilot Instructions - Local RAG System with Docling & Ollama

Follow the guidelines in AGENT.md for contributing to this project.

## Project Overview

**Local-first Retrieval-Augmented Generation (RAG) system** supporting 36+ file formats with:
- **Docling**: Unified document conversion (PDF, DOCX, images with OCR, videos, audio)
- **Ollama**: Local LLM inference (DeepSeek-R1:14b primary, with intelligent fallbacks)
- **FAISS**: Vector similarity search for document retrieval
- **LangChain**: Framework integration with version-aware APIs (0.1.x → 0.3.x compatible)
- **Streamlit**: Web interface for interactive Q&A

**Goal**: Process mixed-media documents locally with zero cloud dependency for raw data.

---

## Critical Architecture Decisions

### 1. **Docling as Single-Entry Point** (`docling_utils.py`)
- **Why**: Multiple loaders (PyMuPDF, UnstructuredWordLoader, YoutubeLoader) were fragile and format-specific
- **Implementation**: `DoclingConverter` wraps Docling with graceful fallbacks; `process_directory()` handles batch processing with skip patterns
- **Conservative defaults**: `do_ocr=False`, `do_table_structure=False` to avoid model loading issues (rt_detr_v2 model incompatibility)
- **Pattern**: Disable advanced features by default → users explicitly enable them

### 2. **Multi-Provider LLM/Embedding Fallback Chain** (`utils.py`)
- **Why**: Single provider dependency = system brittleness
- **Order Matters**:
  ```
  LLM: Ollama → llama_cpp → HuggingFace → OpenAI → Perplexity → Google
  Embeddings: HuggingFace BGE → HuggingFace (general) → OpenAI → Perplexity → Google
  ```
- **Key Pattern**: Each provider tries its model list in order; stops on first success
- **Detection**: `detect_device()` returns "mps" (Apple Silicon) → handles torch_dtype deprecation & device assignment

### 3. **LangChain Version Agility** (`rag_cli.py`)
- **Problem**: Chain import locations changed: `langchain.chains` (0.2+) → `langchain_core.chains` (deprecated) → LCEL (0.3.1+)
- **Solution**: Build chain manually with LCEL (LangChain Expression Language) using `|` composition:
  ```python
  chain = (
      {"context": retriever_lambda | format_docs, "input": input_lambda}
      | prompt
      | llm
      | StrOutputParser()
  )
  ```
- **Retriever quirk**: `VectorStoreRetriever` uses `.invoke(str)` not `.get_relevant_documents(str)`

### 4. **Conservative Document Processing**
- **Skip patterns**: `.git`, `__pycache__`, `.venv` (configured in `docling_utils.py`)
- **File format filtering**: Only process known extensions to avoid crashes on binaries
- **Error resilience**: Single file failure doesn't halt batch; logged with context for retry

---

## Project Structure & Key Files

```
.
├── main.py                    # Document indexing pipeline
│   └── load_docs_with_docling() → process_directory() → FAISS index
├── rag_cli.py                 # Streamlit web interface (load_chain() + query loop)
├── docling_utils.py           # Docling wrapper API (DoclingConverter, process_directory())
├── utils.py                   # Embedding/LLM provider fallback logic (get_embeddings_model, get_llm_model)
├── config.yaml                # Provider priority lists + model-specific configs
├── requirements.txt           # Docling, LangChain 0.3.1+, FAISS, sentence-transformers
└── rag-data/                  # Document storage
    ├── data/                  # Place documents here (all formats)
    └── index/                 # Generated FAISS index (index.faiss + index.pkl)
```

---

## Developer Workflows

### **Indexing Documents**
```bash
# Process files in ./rag-data/*/data/ and create FAISS index
python main.py

# Inspect logs for format support status, error recovery
# FAISS index written to ./rag-data/*/index/
```

**Key code**: `main.py:load_docs_with_docling()` → `docling_utils.py:process_directory()` → chunks via `RecursiveCharacterTextSplitter` → embeddings via `get_embeddings_model()` → FAISS via `FAISS.from_documents()`

### **Running Chat Interface**
```bash
streamlit run rag_cli.py
# Loads FAISS + LLM via load_chain() → invokes chain on each query
```

**Interactive debugging**: Streamlit reloads on file change; use `st.write()` for introspection

### **Testing Format Support**
```python
from docling_utils import get_supported_formats, is_format_supported
formats = get_supported_formats()  # Returns nested dict by category
is_format_supported("video.mp4")   # Checks extension
```

### **Stress-Testing LLM Fallbacks**
Edit `config.yaml` to test chain:
```yaml
LLM_PRIORITY:
  - bad_provider    # Will fail
  - ollama          # Falls back here
```
Run `python -c "from utils import get_llm_model; llm = get_llm_model()"` to trace provider attempts

---

## Critical Patterns & Conventions

### **1. Graceful Degradation**
- Docling: PipelineOptions with conservative defaults; fallback to basic converter if custom fails
- LLM: Try each provider; log warnings, continue to next
- **Anti-pattern**: Hardcoded model names or APIs; prefer config-driven lists

### **2. Error Categorization in Logs**
```python
# utils.py pattern:
if "quota" in error_str or "rate_limit" in error_str:
    logger.debug(f"{provider} quota exceeded")  # Expected, try next
elif "401" in error_str:
    logger.debug(f"{provider} auth failed")     # Expected, try next
elif "connection refused" in error_str:
    logger.debug(f"{provider} not running")     # Expected, try next
else:
    logger.warning(f"{provider} unexpected: {e}")  # Debug this
```
**Convention**: Categorize errors to distinguish transient/expected vs. unexpected failures

### **3. Metadata Preservation**
Every `Document` from `docling_utils.convert_file_to_document()` includes:
```python
metadata={
    "source": file_path,
    "format": file_extension,
    "page_content": text
}
```
**Downstream use**: Retriever returns docs with metadata; Streamlit displays source file in UI

### **4. Environment Device Detection**
```python
device = detect_device()  # Returns "mps" (Apple), "cuda", or "cpu"
# Used in HuggingFace model loading to handle torch_dtype & device_map
```
**Convention**: Treat MPS specially (no device_map, explicit .to(device))

---

## Adding New Features

### **Support a New LLM Provider**
1. Add provider name to `LLM_PRIORITY` in `config.yaml`
2. Add elif branch in `utils.py:get_llm_model()`:
   ```python
   elif provider == "my_provider":
       config = model_config.get("my_provider", {})
       llm = MyProviderLLM(
           model=config.get("llm_model", "default"),
           temperature=config.get("temperature", 0.2)
       )
       test_response = llm.invoke("test")  # Quick connectivity check
       logger.info(f"Successfully loaded {provider} LLM")
       return llm
   ```
3. Add config section in `config.yaml`:
   ```yaml
   my_provider:
     llm_model: "my-model-name"
     temperature: 0.2
   ```

### **Support a New File Format**
Docling handles it automatically if:
1. Format is in `docling_utils.py:ALL_SUPPORTED_EXTENSIONS`
2. Docling's `DocumentConverter` recognizes it

To verify: `is_format_supported("file.ext")` returns True

### **Modify Embedding/LLM Behavior**
Edit `config.yaml` to reorder provider priority or adjust model parameters
- **Conservative tuning**: Reduce temperature (0.1) for factual Q&A; increase (0.5) for creative tasks
- **Performance tuning**: Use smaller local models (qwen2.5-coder:7b) vs. advanced (DeepSeek-R1:14b)

---

## Integration Points & Pitfalls

### **LangChain Version Compatibility**
- ✅ Works: LCEL composition with `|` operator (0.2+)
- ❌ Avoid: Direct imports from `langchain.chains` (unreliable); prefer `langchain_core` + compose manually
- **Quirk**: `VectorStoreRetriever.invoke(str)` returns `list[Document]`; some versions expect `.get_relevant_documents()`

### **Ollama Connection**
- Expects Ollama running at `http://127.0.0.1:11434`
- If not running: `ollama serve` or launch macOS app
- Model pull: `ollama pull DeepSeek-R1:14b`

### **FAISS Index Persistence**
- Stored as binary `index.faiss` + pickle metadata `index.pkl`
- Requires **same embedding model** to load (dimension mismatch = crash)
- If rebuilding index: delete old files; re-run `python main.py`

### **GPU Memory on macOS**
- Apple Silicon (MPS): ~10-12 GB for DeepSeek-R1:14b
- Falls back to CPU if memory exhausted (slow but works)
- Monitor with `top -o MEM`

---

## Testing & Validation

### **Syntax & Import Validation**
```bash
python -m py_compile main.py docling_utils.py rag_cli.py utils.py
python -c "from docling_utils import *; from utils import *; print('✅ Imports OK')"
```

### **E2E Workflow Test**
```bash
python main.py                      # Should create FAISS index
streamlit run rag_cli.py            # Should load chain
# Query in UI; check Streamlit logs for provider trace
```

### **Provider Fallback Test**
```bash
# Verify each provider in order attempts to load
python -c "from utils import get_llm_model; get_llm_model()" 2>&1 | grep "Successfully loaded"
```

---

## Documentation Reference

- **Quick setup**: `DEEPSEEK_R1_QUICKSTART.md` (3 steps)
- **Full guide**: `DOCLING_GUIDE.md` (format support, config, troubleshooting)
- **API reference**: Docstrings in `docling_utils.py`, `utils.py`
- **Examples**: `docling_examples.py` (5 runnable examples)

---

## Common Debugging

| Symptom | Cause | Fix |
|---------|-------|-----|
| "rt_detr_v2 model not found" | Docling tried to load OCR model | Already fixed (do_ocr=False); can re-enable after Transformers upgrade |
| "Connection refused" | Ollama not running | `ollama serve` |
| "VectorStoreRetriever has no attribute get_relevant_documents" | LangChain API mismatch | Use `.invoke(str)` instead |
| "FAISS index dimension mismatch" | Embedding model changed | Delete index, re-run `python main.py` |
| "Slow first query" (30-60s) | LLM loading into memory | Expected; subsequent queries faster |

---

## When You're Stuck

1. Check `config.yaml` → provider priorities and model names
2. Trace logs: `grep "Successfully loaded"` to see which provider won
3. Test single component: `python -c "from utils import get_llm_model; print(get_llm_model())"`
4. Run examples: `python docling_examples.py` to isolate issue
5. Refer to `DOCLING_GUIDE.md` § Troubleshooting
