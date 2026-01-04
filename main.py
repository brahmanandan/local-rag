import os
# Set USER_AGENT environment variable early to avoid warnings
os.environ['USER_AGENT'] = os.getenv("USER_AGENT", "rag-chatbot/1.0")

import yaml
from dotenv import load_dotenv
from langchain_community.document_loaders import (
    PyMuPDFLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredPowerPointLoader,
    WebBaseLoader,
    YoutubeLoader
)
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
import fitz  # PyMuPDF
import logging
from utils import get_embeddings_model

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_config(config_path='config.yaml'):
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

config = load_config()

DATA_DIR = config['DATA_DIR']
INDEX_DIR = config['INDEX_DIR']

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".pptx", ".txt", ".url", ".youtube")

def should_skip_file(file_path):
    """Check if file should be skipped based on path and extension."""
    # Skip .git directories
    if '.git' in file_path:
        return True
    
    # Skip common non-document files
    skip_extensions = {
        # Code and config files
        '.md', '.ipynb', '.java', '.py', '.js', '.html', '.css', '.json', 
        '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.config',
        # Data files
        '.mat', '.csv', '.tsv', '.xlsx', '.xls', '.db', '.sqlite',
        # Image files (not supported for text extraction)
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.svg', '.webp',
        # Archive files (not supported)
        '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2',
        # System and temp files
        '.log', '.tmp', '.bak', '.swp', '.DS_Store', '.gitignore',
        '.gitattributes', '.gitmodules', '.gitkeep'
    }
    
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext in skip_extensions:
        return True
    
    # Skip files without extensions that are likely not documents
    if not file_ext and not file_path.endswith(('.url', '.youtube')):
        return True
    
    return False

def is_pdf_corrupted(file_path):
    """Check if a PDF file is corrupted by trying to open it with PyMuPDF."""
    try:
        doc = fitz.open(file_path)
        page_count = len(doc)
        doc.close()
        return page_count == 0
    except (fitz.FileDataError, fitz.FileNotFoundError, RuntimeError, ValueError, SyntaxError) as e:
        # Catch MuPDF syntax errors and other PDF corruption issues
        logger.warning(f"PDF appears corrupted (syntax/format error): {file_path} - {e}")
        return True
    except Exception as e:
        # Catch any other unexpected errors
        error_msg = str(e).lower()
        if 'syntax error' in error_msg or 'expected object' in error_msg or 'corrupted' in error_msg:
            logger.warning(f"PDF appears corrupted: {file_path} - {e}")
            return True
        # Re-raise if it's not a corruption issue
        raise

def load_docs():
    """Load documents from the data directory.
    
    Supported formats:
    - PDF (.pdf)
    - Word documents (.docx) - requires unstructured package
    - PowerPoint (.pptx) - requires unstructured package
    - Text files (.txt)
    - URL files (.url)
    - YouTube files (.youtube)
    
    Unsupported formats are automatically skipped (images, archives, etc.)
    """
    docs = []
    
    logger.info(f"Starting to load documents from: {DATA_DIR}")
    logger.info("Supported formats: PDF, DOCX, PPTX, TXT, URL, YouTube")
    logger.info("Unsupported formats (images, archives, etc.) will be skipped automatically")

    for root, dirs, files in os.walk(DATA_DIR):
        # Skip .git directories
        dirs[:] = [d for d in dirs if d != '.git']
        
        for file in files:
            path = os.path.join(root, file)
            
            # Skip files that should be excluded
            if should_skip_file(path):
                continue
                
            if file.lower().endswith(".pdf"):
                # Check if PDF is corrupted before trying to load
                if is_pdf_corrupted(path):
                    logger.warning(f"Skipping corrupted PDF: {path}")
                    continue
                    
                try:
                    docs += PyMuPDFLoader(path).load()
                except Exception as e:
                    logger.error(f"Error loading PDF {path}: {e}")
                    continue

            elif file.lower().endswith(".docx"):
                try:
                    docs += UnstructuredWordDocumentLoader(path).load()
                except ImportError as e:
                    if 'unstructured' in str(e).lower():
                        logger.error(f"Error loading DOCX {path}: unstructured package not found")
                        logger.error("Please install it with: pip install unstructured")
                        logger.error("Or install all requirements: pip install -r requirements.txt")
                    else:
                        logger.error(f"Error loading DOCX {path}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error loading DOCX {path}: {e}")
                    continue

            elif file.lower().endswith(".pptx"):
                try:
                    docs += UnstructuredPowerPointLoader(path).load()
                except ImportError as e:
                    if 'unstructured' in str(e).lower():
                        logger.error(f"Error loading PPTX {path}: unstructured package not found")
                        logger.error("Please install it with: pip install unstructured")
                        logger.error("Or install all requirements: pip install -r requirements.txt")
                    else:
                        logger.error(f"Error loading PPTX {path}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error loading PPTX {path}: {e}")
                    continue

            elif file.lower().endswith(".txt"):
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        # Create a proper Document object
                        doc = Document(
                            page_content=content,
                            metadata={"source": path}
                        )
                        docs.append(doc)
                except Exception as e:
                    logger.error(f"Error loading TXT {path}: {e}")
                    continue

            elif file.lower().endswith(".url"):
                try:
                    with open(path, "r") as url_file:
                        url = url_file.read().strip()
                        docs += WebBaseLoader(url).load()
                except Exception as e:
                    logger.error(f"Error loading URL {path}: {e}")
                    continue

            elif file.lower().endswith(".youtube"):
                try:
                    with open(path, "r") as yt_file:
                        yt_url = yt_file.read().strip()
                        docs += YoutubeLoader.from_youtube_url(yt_url, add_video_info=True).load()
                except Exception as e:
                    logger.error(f"Error loading YouTube URL {path}: {e}")
                    continue

            else:
                # Only log if it's not already in our skip list
                file_ext = os.path.splitext(path)[1].lower()
                if file_ext not in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.svg', 
                                    '.webp', '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'}:
                    logger.debug(f"Skipping unsupported file: {path}")

    logger.info(f"Successfully loaded {len(docs)} document chunks from supported files")
    return docs


def index_documents():
    """Index all documents in the data directory."""
    logger.info("=" * 60)
    logger.info("Starting document indexing process")
    logger.info("=" * 60)
    
    docs = load_docs()
    
    if not docs:
        logger.warning("No documents found to index.")
        logger.warning(f"Please check that {DATA_DIR} contains supported files.")
        logger.warning("Supported formats: PDF, DOCX, PPTX, TXT, URL, YouTube")
        return
        
    logger.info(f"Loaded {len(docs)} document chunks for indexing.")
    
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
