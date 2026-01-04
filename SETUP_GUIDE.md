# Setup Guide - Fixing Common Errors

This guide helps you fix common errors and run the RAG system successfully.

## Quick Fix Checklist

- [ ] Install missing packages: `pip install -r requirements.txt`
- [ ] Fix invalid API keys (if using cloud providers)
- [ ] Verify supported file formats
- [ ] Run indexing: `python main.py`
- [ ] Start chatbot: `streamlit run rag_cli.py`

---

## Error 1: Missing `unstructured` Package

**Error Message:**
```
ERROR: unstructured package not found, please install it with `pip install unstructured`
```

**Solution:**
```bash
# Install all requirements (recommended)
pip install -r requirements.txt

# Or install just unstructured
pip install unstructured
```

**Note:** The `unstructured` package is required for:
- DOCX files (Word documents)
- PPTX files (PowerPoint presentations)

---

## Error 2: Invalid OpenAI API Key

**Error Message:**
```
HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 401 Unauthorized"
Error code: 401 - Incorrect API key provided
```

**Solution:**

### Option 1: Fix Your API Key

1. **Get a valid API key:**
   - Visit: https://platform.openai.com/api-keys
   - Create a new API key or copy an existing one

2. **Update your API key:**
   ```bash
   # Edit .env file
   nano .env
   # or
   vim .env
   ```
   
   Update the line:
   ```env
   OPENAI_API_KEY=sk-proj-YOUR_VALID_KEY_HERE
   ```

3. **Or set as environment variable:**
   ```bash
   export OPENAI_API_KEY="sk-proj-YOUR_VALID_KEY_HERE"
   ```

### Option 2: Use Local Models (No API Key Needed)

If you don't want to use OpenAI, the system will automatically fall back to local models:

```bash
# Remove or comment out OpenAI API key
# The system will use HuggingFace local models instead
```

**The system will automatically try:**
1. OpenAI (if API key is valid)
2. Perplexity (if API key is set)
3. Google Gemini (if API key is set)
4. Ollama (if installed)
5. llama.cpp (if model path is set)
6. HuggingFace local models (always available)

---

## Error 3: PDF Corruption (MuPDF Syntax Error)

**Error Message:**
```
MuPDF error: syntax error: expected object number
```

**Solution:**

This error occurs when a PDF file is corrupted. The system now handles this automatically:

- **Corrupted PDFs are automatically skipped**
- You'll see a warning message but indexing will continue
- The system processes all other valid PDFs

**If you need to fix a corrupted PDF:**
1. Try opening it in a PDF viewer
2. Re-save or export it as a new PDF
3. Or remove the corrupted file from your data directory

---

## Error 4: Unsupported File Formats

**Messages:**
```
INFO: Skipping unsupported file: .../PHOTO-2025-08-19-09-48-02.jpg
INFO: Skipping unsupported file: .../Multi-Modal-RAG.rar
```

**This is Normal!**

The system automatically skips unsupported file types:
- **Images**: JPG, PNG, GIF, etc. (not supported for text extraction)
- **Archives**: ZIP, RAR, 7Z, etc. (extract files first)
- **Code files**: .py, .js, .java, etc.
- **Data files**: .csv, .xlsx, .mat, etc.

**Supported Formats:**
- ✅ PDF (.pdf)
- ✅ Word documents (.docx)
- ✅ PowerPoint (.pptx)
- ✅ Text files (.txt)
- ✅ URL files (.url)
- ✅ YouTube files (.youtube)

**To process archive files:**
1. Extract the archive (ZIP, RAR, etc.)
2. Place the extracted files in your data directory
3. Re-run indexing

---

## Step-by-Step Setup Instructions

### 1. Install All Dependencies

```bash
# Make sure you're in the project directory
cd /path/to/rag

# Activate virtual environment (if using one)
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Install all requirements
pip install -r requirements.txt
```

### 2. Configure API Keys (Optional)

**For Cloud Providers (OpenAI, Perplexity, Google):**

Create a `.env` file in the project root:
```bash
cat > .env << EOF
OPENAI_API_KEY=sk-proj-YOUR_VALID_KEY
PERPLEXITY_API_KEY=pplx-YOUR_KEY
GOOGLE_API_KEY=YOUR_KEY
EOF
```

**Or use local models (no API keys needed):**
- Just don't set any API keys
- The system will use HuggingFace local models automatically

### 3. Verify Your Data Directory

```bash
# Check config.yaml
cat config.yaml

# Should show:
# DATA_DIR: "./rag-data/AI-Books/data"
# INDEX_DIR: "./rag-data/AI-Books/index"
```

### 4. Run Indexing

```bash
python main.py
```

**Expected Output:**
```
============================================================
Starting document indexing process
============================================================
Starting to load documents from: ./rag-data/AI-Books/data
Supported formats: PDF, DOCX, PPTX, TXT, URL, YouTube
...
Successfully loaded 17001 document chunks from supported files
Loaded 17001 document chunks for indexing.
Splitting documents into chunks...
Created 25000 text chunks from 17001 documents.
Loading embeddings model...
INFO: Successfully loaded HuggingFace BGE embeddings
Creating vector index...
Saving index to: ./rag-data/AI-Books/index
============================================================
✓ Indexing complete!
  - Documents processed: 17001
  - Text chunks created: 25000
  - Index saved to: ./rag-data/AI-Books/index
============================================================
```

### 5. Start the Chatbot

```bash
streamlit run rag_cli.py
```

The web interface will open automatically in your browser.

---

## Troubleshooting

### Issue: "No documents found to index"

**Check:**
1. Data directory exists: `ls -la rag-data/AI-Books/data/`
2. Files have supported extensions (.pdf, .docx, .pptx, .txt, .url, .youtube)
3. Config.yaml points to correct directory

### Issue: "All LLM providers failed"

**Solutions:**
1. **For cloud providers:** Verify API keys are correct
2. **For local models:** Ensure models can be downloaded (internet required first time)
3. **Install Ollama** (recommended for macOS):
   ```bash
   # Install from https://ollama.ai
   ollama pull llama2
   ```

### Issue: Slow Indexing

**Solutions:**
1. Use cloud embeddings (OpenAI) for faster processing
2. Reduce number of documents
3. Use smaller chunk sizes (edit main.py)

### Issue: Memory Errors

**Solutions:**
1. Use cloud providers instead of local models
2. Process fewer documents at once
3. Use smaller models (edit utils.py)

---

## Supported File Formats Summary

| Format | Extension | Requires | Status |
|--------|-----------|---------|--------|
| PDF | .pdf | PyMuPDF | ✅ Supported |
| Word | .docx | unstructured | ✅ Supported |
| PowerPoint | .pptx | unstructured | ✅ Supported |
| Text | .txt | None | ✅ Supported |
| URL | .url | None | ✅ Supported |
| YouTube | .youtube | None | ✅ Supported |
| Images | .jpg, .png, etc. | - | ❌ Not supported |
| Archives | .zip, .rar, etc. | - | ❌ Not supported |

---

## Quick Commands Reference

```bash
# Install dependencies
pip install -r requirements.txt

# Check API keys
echo $OPENAI_API_KEY

# Run indexing
python main.py

# Start chatbot
streamlit run rag_cli.py

# View logs
python main.py 2>&1 | tee indexing.log

# Check index files
ls -la rag-data/AI-Books/index/
```

---

## Getting Help

If you continue to have issues:

1. **Check the logs:** Look for ERROR messages in the output
2. **Verify dependencies:** `pip list | grep -E "(langchain|unstructured|PyMuPDF)"`
3. **Test with a single file:** Place one PDF in data directory and try indexing
4. **Check README.md:** Full documentation available

---

## Success Indicators

You'll know everything is working when you see:

✅ `Successfully loaded X document chunks from supported files`
✅ `Successfully loaded [Provider] embeddings`
✅ `✓ Indexing complete!`
✅ Streamlit interface opens without errors
✅ You can ask questions and get answers

Good luck! 🚀

