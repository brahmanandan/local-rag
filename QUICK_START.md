# Quick Start - Run Successfully

## Fix All Errors and Run in 3 Steps

### Step 1: Install Missing Packages

```bash
# Install all required packages (including unstructured)
pip install -r requirements.txt
```

This will install:
- ✅ `unstructured` (for DOCX and PPTX files)
- ✅ All other dependencies

### Step 2: Fix API Key Issue (Choose One Option)

#### Option A: Use Local Models (Recommended - No API Keys Needed)

```bash
# Don't set any API keys - system will use local HuggingFace models
# Just proceed to Step 3
```

#### Option B: Fix Your OpenAI API Key

```bash
# Get a valid key from: https://platform.openai.com/api-keys
# Then update your .env file:
export OPENAI_API_KEY="sk-proj-YOUR_VALID_KEY_HERE"

# Or edit .env file directly
nano .env
```

### Step 3: Run the System

```bash
# 1. Create the index
python main.py

# 2. Start the chatbot (in a new terminal)
streamlit run rag_cli.py
```

---

## What Was Fixed

✅ **Added `unstructured` package** to requirements.txt  
✅ **Improved PDF corruption handling** - MuPDF syntax errors are now caught and skipped  
✅ **Added image files to skip list** - JPG, PNG, etc. are automatically skipped (not supported)  
✅ **Added archives to skip list** - ZIP, RAR, etc. are automatically skipped  
✅ **Better error messages** - Clear instructions when packages are missing  
✅ **Improved logging** - Shows supported formats and progress  

---

## Expected Output

When you run `python main.py`, you should see:

```
============================================================
Starting document indexing process
============================================================
Starting to load documents from: ./rag-data/AI-Books/data
Supported formats: PDF, DOCX, PPTX, TXT, URL, YouTube
Unsupported formats (images, archives, etc.) will be skipped automatically
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

**Note:** 
- Skipped files (images, archives) are normal - they're not supported
- PDF corruption warnings are normal - corrupted PDFs are automatically skipped
- The system will use local HuggingFace models if API keys are invalid/missing

---

## Supported File Formats

✅ **Supported:**
- PDF (.pdf)
- Word (.docx) - requires `unstructured`
- PowerPoint (.pptx) - requires `unstructured`
- Text (.txt)
- URL (.url)
- YouTube (.youtube)

❌ **Not Supported (automatically skipped):**
- Images: JPG, PNG, GIF, BMP, etc.
- Archives: ZIP, RAR, 7Z, TAR, etc.
- Code files: .py, .js, .java, etc.
- Data files: .csv, .xlsx, .mat, etc.

---

## Troubleshooting

### Still seeing "unstructured package not found"?

```bash
# Make sure you installed it
pip install unstructured

# Verify it's installed
pip list | grep unstructured
```

### Still seeing API key errors?

**Use local models instead:**
- Don't set any API keys
- The system automatically uses HuggingFace local models
- No API keys needed!

### PDF errors?

- Corrupted PDFs are automatically skipped
- You'll see warnings but indexing continues
- This is normal behavior

---

## Full Documentation

- **SETUP_GUIDE.md** - Detailed troubleshooting guide
- **README.md** - Complete documentation
- **doc/index.html** - HTML version of documentation

---

## Success! 🎉

Once you see "✓ Indexing complete!", you're ready to use the chatbot:

```bash
streamlit run rag_cli.py
```

The web interface will open and you can start asking questions!

