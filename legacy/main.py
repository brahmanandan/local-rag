import os
# Set USER_AGENT environment variable early to avoid warnings
os.environ['USER_AGENT'] = os.getenv("USER_AGENT", "rag-chatbot/1.0")

import yaml
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    # Fallback for older LangChain versions
    from langchain.text_splitter import RecursiveCharacterTextSplitter

try:
    from langchain_core.documents import Document
except ImportError:
    # Fallback for older LangChain versions
    from langchain.schema import Document

import logging
load_dotenv()

from utils import get_embeddings_model

# Docling imports for comprehensive document support
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import ConversionStatus
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Docling not installed. Install it with: pip install docling")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_config(config_path='config.yaml'):
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

config = load_config()

DATA_DIR = config['DATA_DIR']
INDEX_DIR = config['INDEX_DIR']

# Docling supports these formats natively
DOCLING_SUPPORTED_EXTENSIONS = (
    # Documents
    ".pdf", ".docx", ".pptx", ".xlsx", ".html", ".htm",
    # Images
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp",
    # Videos
    ".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm",
    # Audio
    ".mp3", ".wav", ".aac", ".flac", ".m4a", ".ogg", ".wma",
    # Text formats
    ".txt", ".md", ".rst", ".latex", ".tex", ".xml", ".json",
    # Other supported formats
    ".asciidoc", ".adoc"
)

def should_skip_file(file_path):
    """Check if file should be skipped based on path and extension."""
    # Skip .git directories
    if '.git' in file_path:
        return True
    
    # Skip system and config files that shouldn't be indexed
    skip_extensions = {
        # Python and code-specific (we index content differently)
        '.py', '.pyc', '.pyo', '.pyd', '.so',
        '.js', '.ts', '.jsx', '.tsx', '.java', '.class',
        '.c', '.cpp', '.h', '.hpp', '.go', '.rs', '.rb',
        # Config files (usually not content to extract)
        '.yaml', '.yml', '.toml', '.ini', '.cfg', '.config',
        # Archive files (not directly indexable)
        '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
        # System files
        '.log', '.tmp', '.bak', '.swp', '.DS_Store',
        '.gitignore', '.gitattributes', '.gitmodules', '.gitkeep',
        # Compiled/binary that shouldn't be indexed
        '.exe', '.dll', '.so', '.dylib',
    }
    
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext in skip_extensions:
        return True
    
    # Skip files without extensions that are likely not documents
    if not file_ext:
        return True
    
    return False

def load_docs_with_docling():
    """Load documents using Docling for comprehensive format support.
    
    Docling supports:
    - Documents: PDF, DOCX, PPTX, XLSX, HTML, Markdown, LaTeX, AsciiDoc
    - Images: JPG, PNG, GIF, BMP, TIFF, WebP (with OCR capability)
    - Videos: MP4, AVI, MOV, MKV, FLV, WMV, WebM (extracts frames and metadata)
    - Audio: MP3, WAV, AAC, FLAC, M4A, OGG, WMA (transcription capable)
    - Other: XML, JSON, RST, TXT
    """
    if not DOCLING_AVAILABLE:
        logger.error("Docling is not installed!")
        logger.error("Please install it with: pip install docling")
        return []
    
    docs = []
    converter = None
    
    # Try to initialize converter with error handling
    try:
        from docling.datamodel.pipeline_options import PipelineOptions
        # Use conservative options to avoid model compatibility issues
        options = PipelineOptions(
            do_ocr=False,  # Disable OCR by default to avoid rt_detr_v2 issues
            do_table_structure=False,  # Disable table structure to avoid model issues
            do_classify_tables=False   # Disable table classification
        )
        converter = DocumentConverter(pipeline_options=options)
        logger.info("Docling converter initialized (OCR and table extraction disabled)")
    except Exception as init_error:
        logger.warning(f"Could not initialize converter with options: {init_error}")
        try:
            # Fallback: try basic initialization
            converter = DocumentConverter()
            logger.info("Docling converter initialized (basic mode)")
        except Exception as e:
            logger.error(f"Failed to initialize Docling converter: {e}")
            logger.error("Try updating: pip install --upgrade docling transformers")
            return []
    
    logger.info(f"Starting to load documents from: {DATA_DIR}")
    logger.info("Using Docling for comprehensive format support:")
    logger.info("  - Documents: PDF, DOCX, PPTX, XLSX, HTML, Markdown, LaTeX, AsciiDoc")
    logger.info("  - Images: JPG, PNG, GIF, BMP, TIFF, WebP")
    logger.info("  - Videos: MP4, AVI, MOV, MKV, FLV, WMV, WebM")
    logger.info("  - Audio: MP3, WAV, AAC, FLAC, M4A, OGG, WMA")
    logger.info("  - Text: TXT, Markdown, JSON, XML, RST")
    logger.info("Note: OCR and table extraction disabled to avoid model compatibility issues")

    processed_files = 0
    failed_files = 0
    
    for root, dirs, files in os.walk(DATA_DIR):
        # Skip .git directories
        dirs[:] = [d for d in dirs if d != '.git']
        
        for file in files:
            path = os.path.join(root, file)
            
            # Skip files that should be excluded
            if should_skip_file(path):
                continue
            
            # Check if extension is supported by docling
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext not in DOCLING_SUPPORTED_EXTENSIONS:
                logger.debug(f"Skipping unsupported file: {path}")
                continue
            
            try:
                logger.debug(f"Processing: {path}")
                
                # Convert document using docling
                result = converter.convert(path)
                
                # Check conversion status
                if result.status != ConversionStatus.SUCCESS:
                    logger.warning(f"Failed to convert {path}: {result.status}")
                    failed_files += 1
                    continue
                
                # Extract text content and metadata from the document
                if result.document:
                    text_content = result.document.export_to_markdown()
                    
                    if text_content and text_content.strip():
                        # Create a Document object for LangChain
                        doc = Document(
                            page_content=text_content,
                            metadata={
                                "source": path,
                                "file_name": file,
                                "file_type": file_ext,
                                "file_size": os.path.getsize(path)
                            }
                        )
                        docs.append(doc)
                        processed_files += 1
                        logger.debug(f"Successfully loaded: {path}")
                    else:
                        logger.warning(f"No text content extracted from: {path}")
                        failed_files += 1
                else:
                    logger.warning(f"No document returned from converter for: {path}")
                    failed_files += 1
                    
            except Exception as e:
                error_msg = str(e).lower()
                # Handle model compatibility issues gracefully
                if "checkpoint" in error_msg or "rt_detr" in error_msg or "transformers" in error_msg:
                    logger.warning(f"Model compatibility issue with {path}: {e}")
                    logger.warning("Try: pip install --upgrade docling transformers")
                else:
                    logger.error(f"Error processing {path}: {e}")
                failed_files += 1
                continue
    
    logger.info(f"Document loading complete:")
    logger.info(f"  - Successfully processed: {processed_files} files")
    logger.info(f"  - Failed: {failed_files} files")
    logger.info(f"  - Total documents loaded: {len(docs)}")
    
    if failed_files > 0 and processed_files == 0:
        logger.warning("No files were successfully processed.")
        logger.warning("If you see model errors, try:")
        logger.warning("  pip install --upgrade docling docling-core transformers")
    
    return docs


def index_documents():
    """Index all documents in the data directory using Docling."""
    logger.info("=" * 60)
    logger.info("Starting document indexing process (powered by Docling)")
    logger.info("=" * 60)
    
    if not DOCLING_AVAILABLE:
        logger.error("Docling is required but not installed!")
        logger.error("Please install it with: pip install docling")
        logger.error("Or install all requirements: pip install -r requirements.txt")
        return
    
    docs = load_docs_with_docling()
    
    if not docs:
        logger.warning("No documents found to index.")
        logger.warning(f"Please check that {DATA_DIR} contains supported files.")
        logger.warning("Supported formats: PDF, DOCX, PPTX, XLSX, HTML, Markdown, LaTeX, AsciiDoc")
        logger.warning("Images (JPG, PNG, GIF, BMP, TIFF, WebP), Videos (MP4, AVI, MOV, MKV), Audio (MP3, WAV, AAC, FLAC)")
        return
        
    logger.info(f"Loaded {len(docs)} documents for indexing.")
    
    logger.info("Splitting documents into chunks...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = splitter.split_documents(docs)
    logger.info(f"Created {len(texts)} text chunks from {len(docs)} documents.")

    try:
        logger.info("Loading embeddings model...")
        embeddings = get_embeddings_model()
        logger.info("Creating vector index...")
        vectorstore = FAISS.from_documents(texts, embeddings)
        
        # Ensure index directory exists
        os.makedirs(INDEX_DIR, exist_ok=True)
        
        logger.info(f"Saving index to: {INDEX_DIR}")
        vectorstore.save_local(INDEX_DIR)
        logger.info("=" * 60)
        logger.info("✓ Indexing complete!")
        logger.info(f"  - Documents processed: {len(docs)}")
        logger.info(f"  - Text chunks created: {len(texts)}")
        logger.info(f"  - Index saved to: {INDEX_DIR}")
        logger.info("=" * 60)
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"Indexing failed: {e}")
        logger.error("=" * 60)
        logger.error("Troubleshooting:")
        logger.error("1. Check your API keys (if using cloud embeddings)")
        logger.error("2. Ensure you have internet connection (for model downloads)")
        logger.error("3. Install all requirements: pip install -r requirements.txt")
        logger.error("4. For local embeddings, ensure sentence-transformers is installed")
        raise

if __name__ == "__main__":
    index_documents()
