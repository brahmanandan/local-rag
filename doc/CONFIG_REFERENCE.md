# Docling Configuration Reference

Complete configuration guide for the Docling-powered RAG system.

## Quick Reference

| Setting | File | Default | Purpose |
|---------|------|---------|---------|
| DATA_DIR | config.yaml | `./rag-data/AI-Books/data` | Source documents directory |
| INDEX_DIR | config.yaml | `./rag-data/AI-Books/index` | FAISS index output directory |
| use_ocr | docling_utils.py | `True` | Enable OCR for images |
| chunk_size | main.py | `1000` | Text chunk size for splitting |
| chunk_overlap | main.py | `200` | Chunk overlap for context |
| max_files | process_directory | `None` | Max files to process (None = all) |

---

## config.yaml Configuration

### Directory Settings
```yaml
# Where Docling will look for documents
DATA_DIR: "./rag-data/AI-Books/data"

# Where the FAISS index will be saved
INDEX_DIR: "./rag-data/AI-Books/index"
```

### Embeddings Configuration
```yaml
EMBEDDINGS_PRIORITY:
  - huggingface_bge          # BAAI/bge-small-en-v1.5 (high quality)
  - huggingface              # sentence-transformers/all-MiniLM-L6-v2
  - openai                   # text-embedding-ada-002
  - perplexity               # Perplexity embeddings
  - google                   # Gemini text-embedding-004 (modern)
```

### LLM Configuration
```yaml
LLM_PRIORITY:
  - ollama                   # Local Ollama models
  - llama_cpp                # llama.cpp GGUF models
  - huggingface              # Local HuggingFace models
  - openai                   # GPT-3.5-turbo or GPT-4
  - perplexity               # mistral-7b-instruct
  - google                   # Gemini 1.5 Flash/Pro
```

### Model-Specific Settings
```yaml
MODELS:
  openai:
    embedding_model: "text-embedding-ada-002"
    llm_model: "gpt-3.5-turbo"
    temperature: 0.2
  
  perplexity:
    llm_model: "mistral-7b-instruct"
    temperature: 0.2
  
  google:
    embedding_model: "models/embedding-001"
    llm_model: "gemini-1.5-flash"
    temperature: 0.2
```

---

## main.py Configuration

### Document Converter Settings
```python
# Initialize Docling converter
converter = DocumentConverter()

# With options (optional)
from docling.datamodel.pipeline_options import PipelineOptions

options = PipelineOptions(
    do_ocr=True,              # Enable OCR for images
    do_table_structure=True,  # Extract table structures
    do_classify_tables=True   # Classify table types
)

converter = DocumentConverter(pipeline_options=options)
```

### Text Splitting Configuration
```python
# Configure chunk size and overlap
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,          # Size of each chunk in characters
    chunk_overlap=200         # Overlap between chunks
)

# For longer documents, increase chunk_size:
splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000,
    chunk_overlap=400
)

# For shorter documents, decrease chunk_size:
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100
)
```

### Logging Configuration
```python
# Current logging level
logging.basicConfig(level=logging.INFO)

# For more detailed output
logging.basicConfig(level=logging.DEBUG)

# For less output
logging.basicConfig(level=logging.WARNING)
```

---

## docling_utils.py Configuration

### DoclingConverter Class
```python
from docling_utils import DoclingConverter

# Basic initialization
converter = DoclingConverter(use_ocr=True)

# With options
converter = DoclingConverter(
    use_ocr=True,                    # Enable OCR
    use_audio_transcription=False    # Audio transcription (requires models)
)
```

### process_directory Function
```python
from docling_utils import process_directory

# Basic usage
documents, stats = process_directory("./data")

# With all options
documents, stats = process_directory(
    directory_path="./data",
    skip_patterns=['.git', '__pycache__', '.venv'],  # Patterns to skip
    use_ocr=True,                    # Enable OCR
    max_files=None                   # None = process all files
)

# Limit processing
documents, stats = process_directory(
    "./data",
    max_files=100  # Process max 100 files
)

# Custom skip patterns
documents, stats = process_directory(
    "./data",
    skip_patterns=['.git', 'test_data', 'temp', '__pycache__']
)
```

---

## Environment Variables

### API Keys (set in .env file)
```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Perplexity
PERPLEXITY_API_KEY=pplx-...

# Google Gemini
GOOGLE_API_KEY=AIzaSy...

# HuggingFace (optional)
HUGGINGFACE_API_KEY=hf_...
```

### Other Environment Variables
```bash
# User agent for web requests
USER_AGENT=rag-chatbot/1.0

# Disable tokenizer warnings
TOKENIZERS_PARALLELISM=false

# CUDA/GPU settings (if using GPU)
CUDA_VISIBLE_DEVICES=0
```

---

## Advanced Configuration

### Custom OCR Settings
```python
from docling.datamodel.pipeline_options import PipelineOptions

options = PipelineOptions(
    do_ocr=True,
    ocr_engine="tesseract",  # or "easyocr"
)

converter = DocumentConverter(pipeline_options=options)
```

### Table Extraction Settings
```python
options = PipelineOptions(
    do_table_structure=True,     # Extract table structure
    do_classify_tables=True,     # Classify table types
    table_extraction_params={
        "extract_tables": True,
        "include_table_headers": True
    }
)
```

### Batch Processing Settings
```python
# For large directory processing
documents = []
batch_size = 50

for batch in batch_generator("./large_data", batch_size):
    batch_docs, stats = process_directory(
        batch,
        max_files=batch_size
    )
    documents.extend(batch_docs)
```

---

## Format-Specific Configuration

### PDF Processing
```python
# PDFs are handled automatically
# For encrypted PDFs, they're skipped with a warning
# No special configuration needed
```

### Image Processing with OCR
```python
# Enable OCR in converter
converter = DoclingConverter(use_ocr=True)

# For better OCR, install easyocr
# pip install easyocr

# OCR languages can be configured via environment
import os
os.environ['LANG'] = 'en'  # Or any supported language
```

### Video Processing
```python
# Videos are processed to extract:
# - Key frames
# - Metadata (duration, fps, resolution)
# - Scene information

# No special configuration needed
# Videos are processed like other documents
```

### Audio Processing
```python
# For audio transcription, install Whisper
# pip install openai-whisper

# Audio files are indexed without transcription by default
# Transcription requires additional models
```

---

## Performance Tuning

### For Speed (Faster Processing)
```python
# Disable OCR for faster processing (if not needed images)
converter = DoclingConverter(use_ocr=False)

# Reduce chunk size for faster splitting
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100
)

# Use max_files to process in batches
documents, _ = process_directory(
    "./data",
    use_ocr=False,
    max_files=50
)
```

### For Quality (Better Results)
```python
# Enable all features
converter = DoclingConverter(use_ocr=True)

# Larger chunks preserve more context
splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000,
    chunk_overlap=400
)

# Use high-quality embeddings model
# In config.yaml, put best model first:
EMBEDDINGS_PRIORITY:
  - huggingface_bge  # High quality
  - openai           # High quality
  # ... lower quality options last
```

### For Memory Efficiency
```python
# Process in smaller batches
documents, _ = process_directory(
    "./data",
    max_files=10  # Smaller batches
)

# Use smaller embedding models
# In config.yaml:
EMBEDDINGS_PRIORITY:
  - huggingface  # Smaller than BGE
  - openai
```

---

## Logging Configuration

### Different Log Levels
```python
import logging

# Detailed debugging
logging.basicConfig(level=logging.DEBUG)

# Standard information
logging.basicConfig(level=logging.INFO)

# Only warnings and errors
logging.basicConfig(level=logging.WARNING)

# Only errors and critical
logging.basicConfig(level=logging.ERROR)
```

### Log Format
```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Redirect Logs to File
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rag_system.log'),
        logging.StreamHandler()
    ]
)
```

---

## Database/Index Configuration

### FAISS Index Options
```python
# Basic index (default)
vectorstore = FAISS.from_documents(texts, embeddings)

# With compression (for large indexes)
# vectorstore = FAISS.from_documents(texts, embeddings, 
#                                    compress_level=4)

# Save and load
vectorstore.save_local("./index")
vectorstore = FAISS.load_local("./index", embeddings)
```

---

## Security Configuration

### .env File (for API keys)
```bash
# Create .env file with your secrets
OPENAI_API_KEY=sk-...
PERPLEXITY_API_KEY=pplx-...
GOOGLE_API_KEY=AIzaSy...

# Never commit .env to version control
# Add to .gitignore:
# .env
# .env.local
```

### File Permissions
```bash
# Make config readable but not world-accessible
chmod 600 .env
chmod 644 config.yaml

# Restrict index directory
chmod 700 ./rag-data/AI-Books/index
```

---

## Integration Configuration

### With Web Framework (Flask/FastAPI)
```python
# Load embeddings and index once at startup
embeddings = get_embeddings_model()
vectorstore = FAISS.load_local("./index", embeddings)

# Use in routes
@app.post("/search")
def search(query: str):
    results = vectorstore.similarity_search(query, k=5)
    return results
```

### With Existing RAG Pipeline
```python
# The new Docling integration is drop-in compatible
# Just use process_directory instead of individual loaders

# Old way:
# pdf_docs = PyMuPDFLoader("file.pdf").load()
# docx_docs = UnstructuredWordDocumentLoader("file.docx").load()

# New way:
from docling_utils import process_directory
documents, stats = process_directory("./data")
```

---

## Configuration Validation

### Check Configuration
```python
import yaml

# Load and validate config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Check required fields
required = ['DATA_DIR', 'INDEX_DIR']
for field in required:
    if field not in config:
        raise ValueError(f"Missing {field} in config.yaml")

# Check directories exist
from pathlib import Path
data_dir = Path(config['DATA_DIR'])
if not data_dir.exists():
    print(f"Warning: DATA_DIR not found: {data_dir}")
```

### Test Docling Setup
```python
from docling_utils import DoclingConverter, get_supported_formats

# Test converter
try:
    converter = DoclingConverter(use_ocr=True)
    print("✓ Docling converter OK")
except Exception as e:
    print(f"✗ Docling error: {e}")

# Check formats
formats = get_supported_formats()
print(f"✓ {len([e for exts in formats.values() for e in exts])} formats supported")
```

---

## Common Configuration Scenarios

### Scenario 1: Documents Only
```yaml
# config.yaml
DATA_DIR: "./documents"
INDEX_DIR: "./index"

EMBEDDINGS_PRIORITY:
  - huggingface_bge
  - openai
```

```python
# main.py
documents, _ = process_directory(
    DATA_DIR,
    use_ocr=False  # No images, disable OCR
)
```

### Scenario 2: Mixed Media (Documents + Images)
```yaml
# config.yaml
DATA_DIR: "./media"
INDEX_DIR: "./media_index"
```

```python
# main.py
documents, _ = process_directory(
    DATA_DIR,
    use_ocr=True  # Enable OCR for images
)
```

### Scenario 3: Large Document Set
```yaml
# config.yaml
DATA_DIR: "./large_library"
INDEX_DIR: "./large_index"
```

```python
# Process in batches
documents = []
for batch_num in range(0, total_files, 100):
    batch_docs, _ = process_directory(
        DATA_DIR,
        max_files=100
    )
    documents.extend(batch_docs)
```

### Scenario 4: Real-Time Indexing
```python
# Watch directory for new files
from pathlib import Path
import time

watched_dir = Path("./incoming_documents")
index_dir = Path("./index")

while True:
    new_files = get_new_files(watched_dir)
    if new_files:
        docs, _ = process_directory(watched_dir, max_files=10)
        # Add to existing index
        add_to_index(docs, index_dir)
    time.sleep(60)  # Check every minute
```

---

## Troubleshooting Configuration

### Configuration File Not Found
```bash
# Ensure config.yaml is in the project root
ls -la config.yaml

# Or specify path explicitly in code
config = load_config('./path/to/config.yaml')
```

### Directory Paths Not Found
```yaml
# Use absolute paths for clarity
DATA_DIR: "/Users/username/documents"
INDEX_DIR: "/Users/username/index"

# Or relative from project root
DATA_DIR: "./data"
INDEX_DIR: "./index"
```

### API Keys Not Working
```bash
# Verify .env file exists
ls -la .env

# Check API key format
cat .env | grep API_KEY

# Test API connection
python -c "from utils import get_embeddings_model; print(get_embeddings_model())"
```

### OCR Not Working
```bash
# Install OCR dependencies
pip install pytesseract pillow

# On macOS
brew install tesseract

# Verify installation
which tesseract
```

---

## Default Configuration Values

```yaml
# Default config.yaml
DATA_DIR: "./rag-data/AI-Books/data"
INDEX_DIR: "./rag-data/AI-Books/index"

EMBEDDINGS_PRIORITY:
  - huggingface_bge
  - huggingface
  - openai
  - perplexity
  - google

LLM_PRIORITY:
  - ollama
  - llama_cpp
  - huggingface
  - openai
  - perplexity
  - google

MODELS:
  openai:
    embedding_model: "text-embedding-ada-002"
    llm_model: "gpt-3.5-turbo"
    temperature: 0.2
  perplexity:
    llm_model: "mistral-7b-instruct"
    temperature: 0.2
  google:
    embedding_model: "models/embedding-001"
    llm_model: "gemini-1.5-flash"
    temperature: 0.2
```

```python
# Default Python values
chunk_size = 1000
chunk_overlap = 200
use_ocr = True
max_files = None  # Process all
skip_patterns = ['.git', '__pycache__', '.venv']
```

---

**For complete usage guide, see: DOCLING_GUIDE.md**
**For quick start, see: QUICKSTART.md**
