# Docling Integration Guide

This RAG system now uses **Docling** for comprehensive document processing and conversion.

## What is Docling?

Docling is a state-of-the-art document conversion and processing library developed by IBM that supports an extensive range of file formats:

### Supported Formats

#### 📄 Documents
- **PDF** (.pdf)
- **Microsoft Office** (.docx, .pptx, .xlsx)
- **Web** (.html, .htm)
- **Markup** (.md, .rst, .latex, .tex, .xml, .json, .asciidoc, .adoc)
- **Text** (.txt)

#### 🖼️ Images (with OCR)
- .jpg, .jpeg, .png, .gif, .bmp, .tiff, .tif, .webp
- Includes Optical Character Recognition (OCR) for text extraction from images

#### 🎥 Videos
- .mp4, .avi, .mov, .mkv, .flv, .wmv, .webm, .m4v
- Extracts frames, metadata, and key information from videos

#### 🎵 Audio
- .mp3, .wav, .aac, .flac, .m4a, .ogg, .wma, .opus
- Capable of transcription and content extraction

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Or install Docling manually:

```bash
pip install docling docling-core
```

### 2. Optional Dependencies for Advanced Features

For audio transcription support:
```bash
pip install openai-whisper
```

For better OCR performance:
```bash
pip install easyocr
```

## Usage

### Basic Document Indexing

The main indexing script now automatically uses Docling:

```bash
python main.py
```

This will:
1. Scan `DATA_DIR` (configured in `config.yaml`) for all supported file types
2. Convert each document using Docling
3. Extract text content
4. Create embeddings
5. Build and save FAISS vector index

### Using Docling Utilities

Import the utility functions for custom document processing:

```python
from docling_utils import (
    DoclingConverter,
    convert_file_to_document,
    process_directory,
    get_supported_formats,
    is_format_supported
)

# Process a single file
converter = DoclingConverter(use_ocr=True)
doc = convert_file_to_document("path/to/document.pdf", converter)

# Process entire directory
documents, stats = process_directory(
    "./data",
    use_ocr=True,
    max_files=100
)

# Check supported formats
formats = get_supported_formats()
print(formats)

# Check if file is supported
if is_format_supported("image.jpg"):
    print("Format is supported!")
```

## Configuration

### config.yaml

The main configuration file supports all existing settings:

```yaml
DATA_DIR: "./rag-data/AI-Books/data"
INDEX_DIR: "./rag-data/AI-Books/index"

# Embeddings and LLM configurations remain the same
EMBEDDINGS_PRIORITY:
  - huggingface_bge
  - huggingface
  - openai
  # ... rest of configuration
```

### Docling Conversion Options

In `main.py`, the DoclingConverter can be customized:

```python
converter = DocumentConverter(
    pipeline_options=PipelineOptions(
        do_ocr=True,              # Enable OCR for images
        do_table_structure=True,  # Extract table structures
        do_classify_tables=True   # Classify table types
    )
)
```

## Advanced Features

### 1. OCR (Optical Character Recognition)

Docling can extract text from images and image-based PDFs:

```python
converter = DoclingConverter(use_ocr=True)
doc = convert_file_to_document("scanned_document.pdf", converter)
```

### 2. Video Processing

Videos are processed to extract:
- Key frames
- Metadata (duration, resolution, etc.)
- Scene descriptions

```python
# Videos are automatically processed alongside other documents
documents, stats = process_directory("./media", use_ocr=True)
```

### 3. Audio Processing

Audio files can be processed for transcription and content extraction:

```python
# Install whisper for audio transcription
pip install openai-whisper

# Audio files are included in directory processing
documents, stats = process_directory("./audio_files")
```

### 4. Batch Processing

For large directories with multiple formats:

```python
documents, stats = process_directory(
    directory_path="./large_data",
    use_ocr=True,
    max_files=1000  # Limit processing
)

# Review statistics
print(f"Processed: {stats['processed_files']} files")
print(f"Failed: {stats['failed_files']} files")
print(f"By type: {stats['by_type']}")
```

## File Structure

```
.
├── main.py                 # Main indexing script (uses Docling)
├── docling_utils.py       # Docling utility functions
├── rag_cli.py             # CLI interface
├── utils.py               # Embeddings and LLM utilities
├── config.yaml            # Configuration
├── requirements.txt       # Python dependencies (includes docling)
└── rag-data/
    └── AI-Books/
        ├── data/          # Source documents (all supported formats)
        └── index/         # Generated FAISS index
```

## Error Handling

The system includes comprehensive error handling:

```
✓ Successfully converted: document.pdf
✗ Failed to convert: corrupted.pdf
⊘ Skipped: archive.zip (unsupported format)
```

Each error is logged with details and doesn't stop the batch processing.

## Performance Considerations

- **OCR Processing**: Can be slow for image-heavy documents. Disable if not needed.
- **Video Processing**: Extracts frames and metadata. Suitable for content indexing.
- **Audio Processing**: Requires additional models for transcription.
- **Batch Size**: Process in batches if dealing with thousands of files.

## Troubleshooting

### "The checkpoint you are trying to load has model type `rt_detr_v2`..."

This is a model compatibility issue. Quick fix:
```bash
pip install --upgrade docling docling-core transformers
```

**Detailed solution:** See `MODEL_COMPATIBILITY_FIX.md`

**What this means:** Docling tried to use an advanced model your Transformers version doesn't have.

**Current status:** The code has been updated to disable these features by default, so basic indexing will work even without the fix. You can still process all file formats - just without OCR and advanced table detection.

### "Docling is not installed"
```bash
pip install docling docling-core
```

### OCR not working
Ensure you have the required OCR dependencies:
```bash
pip install pytesseract pillow
# On macOS: brew install tesseract
```

### Memory issues with large files
Process files in smaller batches using `max_files` parameter:
```python
documents, stats = process_directory("./data", max_files=50)
```

### Slow video processing
Videos are automatically indexed but processing can be slow. Consider:
- Processing videos separately in a separate index
- Disabling video indexing by implementing file type filters

## API Reference

### DoclingConverter Class

**Methods:**
- `__init__(use_ocr=True, use_audio_transcription=False)`: Initialize converter
- `convert(file_path)`: Convert a single file
- `extract_text(converted_doc)`: Extract markdown text from converted document

### Functions

- `convert_file_to_document(file_path, converter, include_metadata)`: Convert file to LangChain Document
- `process_directory(directory_path, skip_patterns, use_ocr, max_files)`: Process entire directory
- `get_supported_formats()`: Get all supported formats
- `is_format_supported(file_path)`: Check if file format is supported

## Examples

### Example 1: Index Mixed Media Directory

```python
from docling_utils import process_directory
from langchain_community.vectorstores import FAISS
from utils import get_embeddings_model
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Process all documents
documents, stats = process_directory("./mixed_media")

# Split into chunks
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
texts = splitter.split_documents(documents)

# Create embeddings and index
embeddings = get_embeddings_model()
vectorstore = FAISS.from_documents(texts, embeddings)
vectorstore.save_local("./index")
```

### Example 2: Process Images with OCR

```python
from docling_utils import DoclingConverter, convert_file_to_document

converter = DoclingConverter(use_ocr=True)
doc = convert_file_to_document("screenshot.png", converter)

if doc:
    print(doc.page_content)  # Extracted text from image
```

### Example 3: Check Supported Formats

```python
from docling_utils import get_supported_formats, is_format_supported

# Get all supported formats
formats = get_supported_formats()
for category, extensions in formats.items():
    print(f"{category}: {', '.join(extensions)}")

# Check specific files
files = ["document.pdf", "image.jpg", "video.mp4", "audio.mp3", "archive.zip"]
for file in files:
    supported = is_format_supported(file)
    print(f"{file}: {'✓' if supported else '✗'}")
```

## Performance Metrics

Typical processing times (varies by hardware and file size):
- **PDF (10 pages)**: ~2-5 seconds
- **DOCX (10 pages)**: ~1-3 seconds
- **Image (OCR)**: ~3-10 seconds per page
- **Video (5 min)**: ~10-30 seconds (frame extraction)
- **Audio (5 min)**: ~5-15 seconds (with transcription)

## Future Enhancements

Potential improvements for the integration:
1. Parallel processing for batch operations
2. Custom OCR models for domain-specific text
3. Video scene detection and summarization
4. Audio speaker identification
5. Document classification and tagging
6. Incremental indexing with change detection

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Docling documentation: https://github.com/DS4SD/docling
3. Check LangChain documentation: https://python.langchain.com
4. Review logs in your terminal for detailed error messages

## License

This integration uses:
- **Docling**: Apache 2.0 License
- **LangChain**: MIT License
- **FAISS**: MIT License

See individual package licenses for details.
