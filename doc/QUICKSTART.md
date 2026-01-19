# Quick Start Guide - Docling Integration

Get started with the new Docling-powered RAG system in 3 steps.

## Step 1: Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# Or install just docling
pip install docling docling-core
```

## Step 2: Run Document Indexing

```bash
# Index all documents in DATA_DIR (from config.yaml)
python main.py
```

The system will:
- ✓ Scan your data directory
- ✓ Detect supported file types (36+ formats!)
- ✓ Convert documents using Docling
- ✓ Extract text content
- ✓ Create embeddings
- ✓ Build FAISS vector index

## Step 3: Use Your Index

```bash
# Use with your RAG CLI
python rag_cli.py

# Or import in your code
from langchain_community.vectorstores import FAISS
from utils import get_embeddings_model

embeddings = get_embeddings_model()
vectorstore = FAISS.load_local("./rag-data/AI-Books/index", embeddings)

# Search
results = vectorstore.similarity_search("your query", k=5)
```

## What's Supported Now?

**Before Docling**: 5 formats (PDF, DOCX, PPTX, TXT, URL)
**After Docling**: 36+ formats!

### Document Types
- 📄 PDF, Word, PowerPoint, Excel
- 🔗 HTML, Markdown, LaTeX, XML, JSON
- 🖼️ Images (JPG, PNG, GIF, BMP, TIFF) with OCR
- 🎥 Videos (MP4, AVI, MOV, MKV, FLV, WMV, WebM)
- 🎵 Audio (MP3, WAV, AAC, FLAC, M4A, OGG, WMA, Opus)

## Common Tasks

### Process a Single File
```python
from docling_utils import convert_file_to_document, DoclingConverter

converter = DoclingConverter(use_ocr=True)
doc = convert_file_to_document("document.pdf", converter)
print(doc.page_content)
```

### Process an Entire Directory
```python
from docling_utils import process_directory

documents, stats = process_directory(
    "./my-documents",
    use_ocr=True,
    max_files=100
)

print(f"Processed {stats['processed_files']} files")
```

### Check Supported Formats
```python
from docling_utils import get_supported_formats, is_format_supported

# List all supported formats
formats = get_supported_formats()
for category, extensions in formats.items():
    print(f"{category}: {extensions}")

# Check specific file
if is_format_supported("document.pdf"):
    print("Format is supported!")
```

### Create Vector Index from Documents
```python
from docling_utils import process_directory
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from utils import get_embeddings_model

# Load documents
docs, _ = process_directory("./data")

# Split into chunks
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
texts = splitter.split_documents(docs)

# Create index
embeddings = get_embeddings_model()
vectorstore = FAISS.from_documents(texts, embeddings)
vectorstore.save_local("./my-index")
```

### Enable Image OCR
```python
from docling_utils import DoclingConverter

# Enable OCR for extracting text from images
converter = DoclingConverter(use_ocr=True)
doc = converter.convert("screenshot.png")
text = converter.extract_text(doc)
print(text)  # Extracted text from image
```

## Configuration

Edit `config.yaml` to change:

```yaml
# Where to find your documents
DATA_DIR: "./rag-data/AI-Books/data"

# Where to save the index
INDEX_DIR: "./rag-data/AI-Books/index"

# Embeddings and LLM providers
EMBEDDINGS_PRIORITY:
  - huggingface_bge
  - huggingface
  - openai

LLM_PRIORITY:
  - ollama
  - llama_cpp
  - openai
```

## Troubleshooting

### "Docling not installed"
```bash
pip install docling docling-core
```

### "No documents found"
Check that:
1. `DATA_DIR` in `config.yaml` points to the right location
2. Directory contains supported file formats
3. Files have correct extensions

### "OCR not working"
```bash
# Install OCR dependencies
pip install pytesseract pillow

# On macOS
brew install tesseract
```

### "Memory error with large files"
Process in smaller batches:
```python
docs, stats = process_directory("./data", max_files=50)
```

## Examples

See `docling_examples.py` for working examples:

```bash
python docling_examples.py
```

This demonstrates:
- Converting single files
- Listing supported formats
- Processing directories
- Creating vector indexes
- Custom filtering

## Full Documentation

For detailed documentation, see:
- `DOCLING_GUIDE.md` - Complete reference
- `INTEGRATION_SUMMARY.md` - What changed
- `docling_examples.py` - Code examples

## Key Features

✓ **36+ file formats** - Documents, images, videos, audio
✓ **OCR support** - Extract text from images and scans
✓ **Unified interface** - Same code for all formats
✓ **Better errors** - Graceful handling of corrupted files
✓ **Rich metadata** - File info included in documents
✓ **Batch processing** - Process thousands of files
✓ **LangChain integration** - Works with existing RAG pipeline

## File Structure

```
.
├── main.py                 # Main indexing script (uses Docling)
├── rag_cli.py             # Chat interface
├── utils.py               # Embeddings and LLM utilities
├── docling_utils.py       # NEW: Docling utilities
├── docling_examples.py    # NEW: Example scripts
├── config.yaml            # Configuration
├── requirements.txt       # Dependencies
├── DOCLING_GUIDE.md       # Complete documentation
├── INTEGRATION_SUMMARY.md # What changed
├── QUICKSTART.md          # This file
└── rag-data/
    └── AI-Books/
        ├── data/          # Your documents (any supported format)
        └── index/         # Generated FAISS index
```

## Next Steps

1. ✓ Install: `pip install -r requirements.txt`
2. ✓ Test: `python docling_examples.py`
3. ✓ Index: `python main.py`
4. ✓ Use: `python rag_cli.py` or import in your code

## Performance Tips

- **Disable OCR** if you don't need image text extraction (faster)
- **Use max_files** parameter when processing large directories
- **Process separately** - Images/videos in separate index than text documents
- **Batch processing** - Process in chunks, not all at once

## Common Questions

**Q: Will my existing code break?**
A: No! All existing functionality is preserved. The change is transparent.

**Q: Do I need to re-index?**
A: Recommended, but not required. Old index will still work.

**Q: Can I use with my existing RAG system?**
A: Yes! Drop-in replacement. Same interface, more formats.

**Q: What about large files (videos, large PDFs)?**
A: Docling handles them efficiently. Process in batches if memory is limited.

**Q: Is OCR included?**
A: Yes! Install `pytesseract` and `pillow` for full OCR support.

---

**Ready to get started?**

```bash
pip install -r requirements.txt
python main.py
```

For help, see `DOCLING_GUIDE.md` or `docling_examples.py`
