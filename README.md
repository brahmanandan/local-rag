# RAG Course Chatbot

A Retrieval-Augmented Generation (RAG) chatbot that can answer questions based on your course content and documents.

## Table of Contents

- [Quick Start](#quick-start)
- [Detailed Setup Guide](#detailed-setup-guide)
  - [1. Installation](#1-installation)
  - [2. API Keys](#2-api-keys)
  - [3. Data Preparation](#3-data-preparation)
  - [4. How to Execute the Program](#4-how-to-execute-the-program)
  - [5. Configuration](#5-configuration)
- [Model Selection and Priority](#model-selection-and-priority)
- [Local Mode (No API Keys Required)](#local-mode-no-api-keys-required)
- [Additional Information](#additional-information)
- [Troubleshooting](#troubleshooting)
- [Quick Reference](#quick-reference)

## Features

- **Multi-Provider Support**: OpenAI, Perplexity, Google Gemini (Copilot), HuggingFace
- **Local LLM Support**: Ollama, llama.cpp, and HuggingFace models optimized for macOS
- **Apple Silicon Optimized**: Automatic MPS (Metal) GPU acceleration on Apple Silicon Macs
- **Automatic Fallbacks**: If one provider fails, automatically tries the next
- **Local Models**: Run completely offline with multiple local LLM options
- **Multiple File Types**: PDF, DOCX, PPTX, TXT, URLs, YouTube videos
- **Robust Error Handling**: Graceful handling of corrupted files and API failures
- **Modern LangChain API**: Uses latest LangChain patterns with backward compatibility
- **Code Optimization**: Shared utilities eliminate code duplication
- **Web Interface**: Beautiful Streamlit interface for easy interaction

## Quick Start

1. **Install Python packages** (see [Installation](#1-installation) below)
2. **Configure directories** in `config.yaml` (see [Configuration](#5-configuration) below)
3. **Add your documents** to the data directory (see [Data Preparation](#3-data-preparation) below)
4. **Set up API keys** (optional, see [API Keys](#2-api-keys) below)
5. **Create the index**: `python main.py`
6. **Run the chatbot**: `streamlit run rag_cli.py`

---

## Detailed Setup Guide

### 1. Installation

#### System Requirements

- **Python**: 3.8 or higher
- **RAM**: 4GB minimum (8GB+ recommended for local models)
- **Disk Space**: 2-10GB (depending on models used)
- **Operating System**: macOS, Linux, or Windows

#### Step-by-Step Installation

1. **Clone or download this repository**

2. **Create a virtual environment (recommended)**
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate virtual environment
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows:
   venv\Scripts\activate
   ```

3. **Install Python packages**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install optional dependencies for local LLMs** (if using local models)
   
   **For Ollama:**
   ```bash
   # Download and install from https://ollama.ai
   # Then pull a model:
   ollama pull llama2
   ```
   
   **For llama.cpp:**
   ```bash
   pip install llama-cpp-python
   ```

#### Verify Installation

```bash
# Check Python version
python --version

# Verify packages are installed
pip list | grep langchain
```

---

### 2. API Keys

API keys are **optional** if you want to use local models. The system will automatically fall back to local models if API keys are not available.

#### Where to Add API Keys

API keys should be set as **environment variables**. You can add them in several ways:

**Option 1: Export in terminal (temporary - lost when terminal closes)**
```bash
export OPENAI_API_KEY="your-openai-api-key"
export PERPLEXITY_API_KEY="your-perplexity-api-key"
export GOOGLE_API_KEY="your-google-api-key"
export HUGGINGFACE_API_KEY="your-huggingface-api-key"  # Optional
```

**Option 2: Create a `.env` file (recommended - persistent)**

Create a `.env` file in the project root directory:

```bash
# Create .env file in the project root
cat > .env << EOF
OPENAI_API_KEY=your-openai-api-key
PERPLEXITY_API_KEY=your-perplexity-api-key
GOOGLE_API_KEY=your-google-api-key
HUGGINGFACE_API_KEY=your-huggingface-api-key
LLAMA_CPP_MODEL_PATH=/path/to/your/model.gguf
EOF
```

**Example `.env` file:**
```env
# OpenAI API Key (get from https://platform.openai.com/api-keys)
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx

# Perplexity API Key (get from https://www.perplexity.ai/settings/api)
PERPLEXITY_API_KEY=pplx-xxxxxxxxxxxxxxxxxxxxx

# Google Gemini API Key (get from https://makersuite.google.com/app/apikey)
GOOGLE_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxx

# HuggingFace Token (optional, for private models)
HUGGINGFACE_API_KEY=hf_xxxxxxxxxxxxxxxxxxxxx

# llama.cpp Model Path (optional, for local GGUF models)
LLAMA_CPP_MODEL_PATH=~/.cache/llama-cpp/llama-2-7b-chat.gguf
```

**Important:**
- The `.env` file is automatically loaded by the application (using `python-dotenv`)
- **Never commit `.env` to version control** - it contains sensitive keys
- Add `.env` to your `.gitignore` file:
  ```bash
  echo ".env" >> .gitignore
  ```

**Option 3: Add to shell profile (permanent)**
```bash
# Add to ~/.bashrc or ~/.zshrc
echo 'export OPENAI_API_KEY="your-openai-api-key"' >> ~/.zshrc
source ~/.zshrc
```

#### Getting API Keys

- **OpenAI**: https://platform.openai.com/api-keys
- **Perplexity**: https://www.perplexity.ai/settings/api
- **Google Gemini**: https://makersuite.google.com/app/apikey
- **HuggingFace**: https://huggingface.co/settings/tokens (optional, mainly for private models)

#### Priority Order

The system tries providers in this order (you can influence this by only setting certain API keys):

1. **OpenAI** (if `OPENAI_API_KEY` is set)
2. **Perplexity** (if `PERPLEXITY_API_KEY` is set)
3. **Google Gemini** (if `GOOGLE_API_KEY` is set)
4. **Ollama** (if installed and models are available)
5. **llama.cpp** (if `LLAMA_CPP_MODEL_PATH` is set)
6. **HuggingFace** (local models, no API key needed)

---

### 3. Data Preparation

#### Where to Place Your Data

By default, documents should be placed in: `./rag-data/AI-Books/data/`

You can change this location by editing `config.yaml` (see [Configuration](#5-configuration) below).

#### Supported File Formats

The system supports the following file types:

| Format | Extension | Description |
|--------|-----------|-------------|
| PDF | `.pdf` | PDF documents |
| Word | `.docx` | Microsoft Word documents |
| PowerPoint | `.pptx` | Microsoft PowerPoint presentations |
| Text | `.txt` | Plain text files |
| URL | `.url` | Text file containing a web URL (one URL per line) |
| YouTube | `.youtube` | Text file containing a YouTube URL (one URL per line) |

#### Data Directory Structure

```
rag-data/
└── AI-Books/
    ├── data/           # Place your source documents here
    │   ├── document1.pdf
    │   ├── document2.docx
    │   ├── notes.txt
    │   ├── website.url
    │   └── video.youtube
    └── index/          # Generated index (created automatically)
        ├── index.faiss
        └── index.pkl
```

#### File Format Examples

**For URL files (`.url`):**
```bash
# Create a file named "example.url" with content:
https://example.com/article
```

**For YouTube files (`.youtube`):**
```bash
# Create a file named "tutorial.youtube" with content:
https://www.youtube.com/watch?v=VIDEO_ID
```

#### Best Practices

- **Organize files**: Use subdirectories to organize your documents
- **File naming**: Use descriptive names for easier identification
- **File size**: Large files (>100MB) may take longer to process
- **Corrupted files**: The system automatically skips corrupted PDFs
- **Excluded files**: Files in `.git` directories are automatically skipped

---

### 4. How to Execute the Program

#### Step 1: Create the Index

Before running the chatbot, you need to create an index of your documents:

```bash
python main.py
```

**What this does:**
- Scans the data directory for supported files
- Loads and processes all documents
- Creates embeddings using the best available provider
- Builds a searchable vector index
- Saves the index to the index directory
- Provides detailed logging of the process

**Expected output:**
```
INFO:__main__:Loaded 25 documents for indexing.
INFO:__main__:Successfully loaded OpenAI embeddings
INFO:__main__:Indexing complete.
```

**If you see errors:**
- Check that your data directory contains supported files
- Verify API keys are set (if using cloud providers)
- Ensure sufficient disk space for the index

#### Step 2: Run the Chatbot

After creating the index, start the web interface:

```bash
streamlit run rag_cli.py
```

**What happens:**
- Streamlit server starts
- Opens a web browser automatically
- Loads the RAG chain with your index
- Displays the chatbot interface

**Access the interface:**
- The app will open automatically in your browser
- Or navigate to: `http://localhost:8501`

**Using the chatbot:**
1. Type your question in the input box
2. Click Enter or wait for processing
3. View the answer and source documents
4. Continue the conversation (chat history is maintained)

#### Re-indexing

If you add new documents, re-run the indexing:

```bash
python main.py
```

The old index will be overwritten with the new one.

---

### 5. Configuration

#### Configuring Directories

Edit `config.yaml` to change data and index locations:

```yaml
# config.yaml
DATA_DIR: "./rag-data/AI-Books/data"    # Source documents directory
INDEX_DIR: "./rag-data/AI-Books/index"   # Generated index directory
```

**Example: Using custom directories**
```yaml
DATA_DIR: "/Users/yourname/Documents/my-docs"
INDEX_DIR: "/Users/yourname/Documents/my-index"
```

**Important:**
- Use absolute paths for reliability
- Ensure the index directory exists or can be created
- The index directory will be created automatically if it doesn't exist

#### Changing Model Priority

The system automatically selects models based on availability. To force a specific model:

**Method 1: Set only the desired API key**
```bash
# Only use OpenAI (remove other API keys)
export OPENAI_API_KEY="your-key"
# Unset others
unset PERPLEXITY_API_KEY
unset GOOGLE_API_KEY
```

**Method 2: Modify `utils.py`**
Edit the `get_llm_model()` function in `utils.py` to change the order of model attempts.

**Method 3: Use environment variables for local models**
```bash
# Force llama.cpp
export LLAMA_CPP_MODEL_PATH="/path/to/your/model.gguf"

# Force Ollama (ensure Ollama is running)
# The system will automatically detect available Ollama models
```

#### Model Selection Examples

**Use only local models (no API keys):**
```bash
# Don't set any API keys
# Install Ollama and pull a model:
ollama pull llama2
# Or set llama.cpp path:
export LLAMA_CPP_MODEL_PATH="~/.cache/llama-cpp/model.gguf"
```

**Use only OpenAI:**
```bash
export OPENAI_API_KEY="your-key"
# Don't set other API keys
```

**Use Perplexity as primary, fallback to local:**
```bash
export PERPLEXITY_API_KEY="your-key"
# Don't set OpenAI or Google keys
# Local models will be used if Perplexity fails
```

---

## Model Selection and Priority

### How Models Are Selected

The system automatically selects the best available model based on:
1. **API keys set** (cloud providers are tried first)
2. **Model availability** (local models are tried if cloud fails)
3. **Performance** (faster models are preferred)

### Embedding Models (Priority Order)

1. **OpenAI** (`text-embedding-ada-002`) - Requires `OPENAI_API_KEY`
2. **Perplexity** (built-in embeddings) - Requires `PERPLEXITY_API_KEY`
3. **Google Gemini** (`embedding-001`) - Requires `GOOGLE_API_KEY`
4. **HuggingFace BGE** (`BAAI/bge-small-en-v1.5`) - Local, high quality
5. **HuggingFace Sentence Transformers** (`all-MiniLM-L6-v2`) - Local fallback

### LLM Models (Priority Order)

1. **OpenAI** (`gpt-3.5-turbo`) - Requires `OPENAI_API_KEY`
2. **Perplexity** (`mistral-7b-instruct`) - Requires `PERPLEXITY_API_KEY`
3. **Google Gemini** (`gemini-pro`) - Requires `GOOGLE_API_KEY`
4. **Ollama** (`llama2`, `mistral`, `llama3`, `phi3`, `gemma`) - Local, requires Ollama installation
5. **llama.cpp** (GGUF models) - Local, requires `LLAMA_CPP_MODEL_PATH`
6. **HuggingFace** (`phi-2`, `TinyLlama`, `DialoGPT-medium`, `GPT-2`, `DistilGPT-2`) - Local, automatic

### Changing Models

See [Configuration](#5-configuration) section above for detailed instructions.

## Local Mode (No API Keys Required)

The system can run completely offline using local models. Multiple options are available:

### Option 1: Ollama (Recommended for macOS)

Ollama is the easiest way to run local LLMs on macOS:

```bash
# Install Ollama from https://ollama.ai
# Then pull a model:
ollama pull llama2
# or
ollama pull mistral

# Run the RAG system
python main.py
streamlit run rag_cli.py
```

The system will automatically detect and use available Ollama models.

### Option 2: llama.cpp (Optimized for macOS)

For GGUF models optimized for Apple Silicon:

```bash
# Install llama-cpp-python
pip install llama-cpp-python

# Download a GGUF model (e.g., from HuggingFace)
# Set the model path:
export LLAMA_CPP_MODEL_PATH=~/.cache/llama-cpp/llama-2-7b-chat.gguf

# Run the RAG system
python main.py
streamlit run rag_cli.py
```

### Option 3: HuggingFace Models (Apple Silicon Optimized)

The system automatically uses Apple Silicon GPU (MPS) when available:

```bash
# No API keys needed - uses local models
python main.py
streamlit run rag_cli.py
```

This will use:
- **Embeddings**: HuggingFace sentence-transformers (local)
- **LLM**: HuggingFace models optimized for Apple Silicon (phi-2, TinyLlama, etc.)

## Error Handling

- **Corrupted PDFs**: Automatically detected and skipped
- **API Quota Exceeded**: Automatic fallback to next provider
- **Network Issues**: Graceful error messages and retry logic
- **Missing Dependencies**: Clear installation instructions
- **Local Model Failures**: Multiple model fallbacks

---

## Additional Information

### Workflow Overview

```
1. Install packages
   ↓
2. Configure directories (config.yaml)
   ↓
3. Add documents to data directory
   ↓
4. Set API keys (optional)
   ↓
5. Run: python main.py (creates index)
   ↓
6. Run: streamlit run rag_cli.py (starts chatbot)
   ↓
7. Ask questions in the web interface
```

### Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | No | OpenAI API key for embeddings and LLM |
| `PERPLEXITY_API_KEY` | No | Perplexity API key for embeddings and LLM |
| `GOOGLE_API_KEY` | No | Google Gemini API key for embeddings and LLM |
| `HUGGINGFACE_API_KEY` | No | HuggingFace token (optional, for private models) |
| `LLAMA_CPP_MODEL_PATH` | No | Path to GGUF model file for llama.cpp |
| `USER_AGENT` | No | User agent string (default: "rag-chatbot/1.0") |

### File Structure Details

```
rag/
├── main.py              # Indexing script - creates vector index
├── rag_cli.py           # Streamlit chatbot interface
├── utils.py             # Shared utilities for embeddings and LLMs
├── generate_docs.py     # Script to convert README.md to HTML
├── config.yaml          # Configuration file (data/index directories)
├── requirements.txt     # Python package dependencies
├── .env                 # Environment variables (create this file)
├── doc/                 # HTML documentation
│   ├── index.html      # HTML version of this README
│   └── README.md       # Documentation about the HTML docs
├── rag-data/           # Your documents directory
│   └── AI-Books/
│       ├── data/       # Source documents (place files here)
│       └── index/      # Generated index (created by main.py)
│           ├── index.faiss
│           └── index.pkl
└── README.md           # This documentation
```

### HTML Documentation

An HTML version of this documentation is available in the `doc/` folder. It's automatically generated from `README.md` and can be viewed in any web browser.

**To generate/update the HTML documentation:**
```bash
python generate_docs.py
```

**To view the HTML documentation:**
```bash
# Open in browser
open doc/index.html  # macOS
# or
xdg-open doc/index.html  # Linux
# or
start doc/index.html  # Windows

# Or serve with HTTP server
python -m http.server 8000 --directory doc
# Then visit http://localhost:8000
```

**Auto-update on README.md changes:**
See `doc/README.md` for instructions on setting up automatic updates via git hooks or file watchers.

### Understanding the Index

The index is a vector database that stores:
- **Document chunks**: Text split into manageable pieces
- **Embeddings**: Vector representations of text chunks
- **Metadata**: Source file information

**Index files:**
- `index.faiss`: FAISS vector index (binary)
- `index.pkl`: Metadata and configuration (pickle)

**When to re-index:**
- After adding new documents
- After modifying existing documents
- If the index becomes corrupted

### Performance Optimization

**For faster indexing:**
- Use cloud embeddings (OpenAI, Perplexity) instead of local
- Reduce number of documents
- Use smaller chunk sizes (edit `main.py`)

**For faster queries:**
- Use cloud LLMs (OpenAI, Perplexity) for faster responses
- Reduce `k` value in retriever (fewer documents retrieved)
- Use smaller local models

**For local models:**
- Use Ollama for best performance on macOS
- Ensure sufficient RAM (8GB+ recommended)
- Use Apple Silicon for GPU acceleration

---

## Troubleshooting

### Common Issues and Solutions

#### 1. "No documents found to index"

**Problem:** The indexing script can't find any documents.

**Solutions:**
- Check that `DATA_DIR` in `config.yaml` points to the correct directory
- Verify files have supported extensions (`.pdf`, `.docx`, `.pptx`, `.txt`, `.url`, `.youtube`)
- Ensure files are not in `.git` directories (automatically skipped)
- Check file permissions (ensure files are readable)

**Debug:**
```bash
# Check if files are in the directory
ls -la rag-data/AI-Books/data/

# Verify config.yaml path
cat config.yaml
```

#### 2. "All LLM providers failed"

**Problem:** No LLM provider is available or working.

**Solutions:**
- **For cloud providers:** Verify API keys are set correctly
  ```bash
  echo $OPENAI_API_KEY  # Should show your key
  ```
- **For local models:** Ensure models are installed
  ```bash
  # Check Ollama
  ollama list
  
  # Check llama.cpp
  echo $LLAMA_CPP_MODEL_PATH
  ```
- Check internet connection (needed for cloud providers and model downloads)
- Verify API quota hasn't been exceeded
- Try local mode (don't set any API keys)

#### 3. "Failed to load the RAG chain"

**Problem:** The chatbot can't load the index or models.

**Solutions:**
- **Run indexing first:** `python main.py`
- Check that index files exist:
  ```bash
  ls -la rag-data/AI-Books/index/
  ```
- Verify `INDEX_DIR` in `config.yaml` is correct
- Check file permissions on index directory
- Re-create the index if corrupted:
  ```bash
  rm -rf rag-data/AI-Books/index/*
  python main.py
  ```

#### 4. "HuggingFace models failed to load"

**Problem:** Local HuggingFace models won't load.

**Solutions:**
- Ensure sufficient disk space (2-5GB per model)
- Check internet connection (needed for initial download)
- Try smaller models (edit `utils.py` to prioritize smaller models)
- On Apple Silicon, ensure PyTorch with MPS is installed:
  ```bash
  pip install torch --upgrade
  ```
- Clear HuggingFace cache if corrupted:
  ```bash
  rm -rf ~/.cache/huggingface/
  ```

#### 5. "Ollama models not found"

**Problem:** Ollama models aren't detected.

**Solutions:**
- Install Ollama: https://ollama.ai
- Pull a model:
  ```bash
  ollama pull llama2
  ```
- Ensure Ollama service is running:
  ```bash
  ollama serve
  # Or check if running:
  ps aux | grep ollama
  ```
- List available models:
  ```bash
  ollama list
  ```

#### 6. "llama.cpp models not found"

**Problem:** llama.cpp can't find model files.

**Solutions:**
- Install llama-cpp-python:
  ```bash
  pip install llama-cpp-python
  ```
- Set model path:
  ```bash
  export LLAMA_CPP_MODEL_PATH="/path/to/model.gguf"
  ```
- Or place models in default location:
  ```bash
  mkdir -p ~/.cache/llama-cpp/
  # Copy your .gguf file there
  ```
- Download GGUF models from HuggingFace (search for "gguf" models)

#### 7. "Import errors" or "Module not found"

**Problem:** Python packages aren't installed.

**Solutions:**
- Install requirements:
  ```bash
  pip install -r requirements.txt
  ```
- Use virtual environment (recommended):
  ```bash
  python -m venv venv
  source venv/bin/activate  # On Windows: venv\Scripts\activate
  pip install -r requirements.txt
  ```
- Check Python version (3.8+ required):
  ```bash
  python --version
  ```

#### 8. "Streamlit not opening in browser"

**Problem:** Streamlit interface doesn't open automatically.

**Solutions:**
- Manually navigate to: `http://localhost:8501`
- Check if port 8501 is already in use:
  ```bash
  lsof -i :8501
  ```
- Use different port:
  ```bash
  streamlit run rag_cli.py --server.port 8502
  ```

#### 9. "Slow response times"

**Problem:** Queries take too long.

**Solutions:**
- **For local models:** Use smaller models or cloud providers
- **For cloud providers:** Check internet speed
- **Reduce retrieved documents:** Edit `k` value in `rag_cli.py` (line 37)
- **Use GPU:** Ensure Apple Silicon MPS or CUDA is available

#### 10. "Memory errors" or "Out of memory"

**Problem:** System runs out of RAM.

**Solutions:**
- Use smaller models (edit `utils.py` model list)
- Reduce number of documents indexed
- Use cloud providers instead of local models
- Close other applications to free memory
- Increase system RAM if possible

---

## Quick Reference

### Installation Checklist

- [ ] Python 3.8+ installed
- [ ] Virtual environment created and activated
- [ ] Packages installed: `pip install -r requirements.txt`
- [ ] Optional: Ollama installed (for local LLMs)
- [ ] Optional: llama-cpp-python installed (for GGUF models)

### Setup Checklist

- [ ] `config.yaml` configured with correct directories
- [ ] Documents placed in data directory
- [ ] API keys set (optional, in `.env` file or environment)
- [ ] Index created: `python main.py`
- [ ] Chatbot tested: `streamlit run rag_cli.py`

### Common Commands

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Install packages
pip install -r requirements.txt

# Create index
python main.py

# Run chatbot
streamlit run rag_cli.py

# Check Ollama models
ollama list

# Pull Ollama model
ollama pull llama2

# Set environment variable
export OPENAI_API_KEY="your-key"

# Check if index exists
ls -la rag-data/AI-Books/index/
```

### Getting API Keys

- **OpenAI**: https://platform.openai.com/api-keys
- **Perplexity**: https://www.perplexity.ai/settings/api
- **Google Gemini**: https://makersuite.google.com/app/apikey
- **HuggingFace**: https://huggingface.co/settings/tokens (optional)

### Local Model Requirements

**For HuggingFace models:**
- **RAM**: 4GB+ recommended for larger models
- **Disk Space**: 2-5GB for model downloads
- **Internet**: Required for initial model download
- **Apple Silicon**: Automatically uses MPS (Metal Performance Shaders) for GPU acceleration

**For Ollama:**
- **RAM**: 8GB+ recommended
- **Disk Space**: 4-10GB per model
- **Installation**: Download from https://ollama.ai
- **Models**: Automatically downloaded on first use

**For llama.cpp:**
- **RAM**: 4GB+ recommended
- **Disk Space**: 2-8GB per model
- **Installation**: `pip install llama-cpp-python`
- **Models**: Download GGUF format models from HuggingFace
- **Apple Silicon**: Optimized with multi-threading support

## File Structure

```
rag/
├── main.py              # Indexing script
├── rag_cli.py           # Streamlit chatbot
├── config.yaml          # Configuration
├── requirements.txt     # Dependencies
├── rag-data/           # Your documents
│   └── AI-Books/
│       ├── data/       # Source documents
│       └── index/      # Generated index
└── README.md           # This file
```

## Performance Tips

### For Local Mode:
- Use smaller models for faster inference
- Consider using GPU acceleration if available
- Monitor memory usage with larger models

### For API Mode:
- Set up multiple API keys for redundancy
- Monitor API quotas and costs
- Use appropriate model sizes for your use case


