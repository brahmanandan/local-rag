"""
Utility functions for Docling document processing.
Docling is a comprehensive document conversion and processing library
that supports multiple formats including PDFs, images, videos, and audio.
"""

import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

try:
    from docling.document_converter import DocumentConverter, ConvertedDocument
    from docling.datamodel.base_models import ConversionStatus
    from docling.datamodel.pipeline_options import PipelineOptions
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False

try:
    from langchain_core.documents import Document
except ImportError:
    from langchain.schema import Document

logger = logging.getLogger(__name__)

# Docling supported file formats
DOCLING_FORMATS = {
    # Documents
    "documents": [".pdf", ".docx", ".pptx", ".xlsx", ".html", ".htm"],
    # Text formats
    "text": [".txt", ".md", ".rst", ".latex", ".tex", ".xml", ".json", ".asciidoc", ".adoc"],
    # Images (with OCR capability)
    "images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp"],
    # Videos (extracts frames and metadata)
    "videos": [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm", ".m4v"],
    # Audio (transcription capable)
    "audio": [".mp3", ".wav", ".aac", ".flac", ".m4a", ".ogg", ".wma", ".opus"],
}

ALL_SUPPORTED_EXTENSIONS = {
    ext for formats in DOCLING_FORMATS.values() for ext in formats
}


class DoclingConverter:
    """Wrapper class for Docling document conversion with enhanced error handling."""
    
    def __init__(self, use_ocr: bool = True, use_audio_transcription: bool = False):
        """
        Initialize Docling converter.
        
        Args:
            use_ocr: Enable OCR for image-based documents and image extraction
            use_audio_transcription: Enable audio transcription (requires additional models)
        """
        if not DOCLING_AVAILABLE:
            raise ImportError("Docling is not installed. Install with: pip install docling docling-core")
        
        self.use_ocr = use_ocr
        self.use_audio_transcription = use_audio_transcription
        
        # Initialize converter with options
        options = PipelineOptions(
            do_ocr=use_ocr,
            do_table_structure=True,
            do_classify_tables=True,
        )
        
        self.converter = DocumentConverter(pipeline_options=options)
        logger.info(f"Docling converter initialized (OCR: {use_ocr})")
    
    def convert(self, file_path: str) -> Optional[ConvertedDocument]:
        """
        Convert a document file to Docling format.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            ConvertedDocument object or None if conversion failed
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"File does not exist: {file_path}")
                return None
            
            result = self.converter.convert(file_path)
            
            if result.status == ConversionStatus.SUCCESS:
                logger.debug(f"Successfully converted: {file_path}")
                return result
            else:
                logger.warning(f"Conversion failed for {file_path}: {result.status}")
                return None
                
        except Exception as e:
            logger.error(f"Error converting {file_path}: {e}")
            return None
    
    def extract_text(self, converted_doc: ConvertedDocument) -> str:
        """
        Extract markdown text from a converted document.
        
        Args:
            converted_doc: ConvertedDocument object
            
        Returns:
            Extracted text as markdown string
        """
        try:
            if converted_doc and converted_doc.document:
                return converted_doc.document.export_to_markdown()
            return ""
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            return ""


def convert_file_to_document(
    file_path: str,
    converter: Optional[DoclingConverter] = None,
    include_metadata: bool = True
) -> Optional[Document]:
    """
    Convert a single file to a LangChain Document.
    
    Args:
        file_path: Path to the file to convert
        converter: DoclingConverter instance (creates new if None)
        include_metadata: Whether to include file metadata
        
    Returns:
        LangChain Document or None if conversion failed
    """
    if converter is None:
        converter = DoclingConverter()
    
    # Convert using docling
    result = converter.convert(file_path)
    if not result:
        return None
    
    # Extract text
    text_content = converter.extract_text(result)
    if not text_content or not text_content.strip():
        logger.warning(f"No text content extracted from: {file_path}")
        return None
    
    # Build metadata
    metadata = {}
    if include_metadata:
        path = Path(file_path)
        metadata = {
            "source": str(path.absolute()),
            "file_name": path.name,
            "file_type": path.suffix.lower(),
            "file_size": path.stat().st_size if path.exists() else 0,
        }
    
    # Create LangChain Document
    return Document(
        page_content=text_content,
        metadata=metadata
    )


def process_directory(
    directory_path: str,
    skip_patterns: Optional[List[str]] = None,
    use_ocr: bool = True,
    max_files: Optional[int] = None
) -> tuple[List[Document], Dict[str, Any]]:
    """
    Process all supported documents in a directory.
    
    Args:
        directory_path: Path to directory containing documents
        skip_patterns: List of path patterns to skip (e.g., ['.git', '__pycache__'])
        use_ocr: Enable OCR for images
        max_files: Maximum number of files to process (None for all)
        
    Returns:
        Tuple of (list of Documents, statistics dict)
    """
    if not DOCLING_AVAILABLE:
        raise ImportError("Docling is not installed. Install with: pip install docling docling-core")
    
    skip_patterns = skip_patterns or ['.git', '__pycache__', '.venv', 'venv']
    directory = Path(directory_path)
    
    if not directory.is_dir():
        logger.error(f"Directory not found: {directory_path}")
        return [], {}
    
    # Initialize converter
    converter = DoclingConverter(use_ocr=use_ocr)
    
    documents = []
    stats = {
        "total_files": 0,
        "processed_files": 0,
        "failed_files": 0,
        "skipped_files": 0,
        "by_type": {}
    }
    
    logger.info(f"Processing directory: {directory_path}")
    logger.info(f"Supported formats: {', '.join(ALL_SUPPORTED_EXTENSIONS)}")
    
    for file_path in directory.rglob("*"):
        if not file_path.is_file():
            continue
        
        stats["total_files"] += 1
        
        # Check skip patterns
        if any(pattern in str(file_path) for pattern in skip_patterns):
            stats["skipped_files"] += 1
            continue
        
        # Check if supported format
        if file_path.suffix.lower() not in ALL_SUPPORTED_EXTENSIONS:
            stats["skipped_files"] += 1
            continue
        
        # Check max files limit
        if max_files and stats["processed_files"] >= max_files:
            break
        
        try:
            logger.info(f"Processing: {file_path.name}")
            doc = convert_file_to_document(str(file_path), converter)
            
            if doc:
                documents.append(doc)
                stats["processed_files"] += 1
                
                # Track by file type
                file_type = file_path.suffix.lower()
                stats["by_type"][file_type] = stats["by_type"].get(file_type, 0) + 1
            else:
                stats["failed_files"] += 1
                
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            stats["failed_files"] += 1
    
    # Log statistics
    logger.info("=" * 60)
    logger.info("Directory Processing Summary:")
    logger.info(f"  Total files found: {stats['total_files']}")
    logger.info(f"  Successfully processed: {stats['processed_files']}")
    logger.info(f"  Failed: {stats['failed_files']}")
    logger.info(f"  Skipped: {stats['skipped_files']}")
    logger.info(f"  Documents created: {len(documents)}")
    if stats["by_type"]:
        logger.info("  Processed by type:")
        for file_type, count in sorted(stats["by_type"].items()):
            logger.info(f"    {file_type}: {count}")
    logger.info("=" * 60)
    
    return documents, stats


def get_supported_formats() -> Dict[str, List[str]]:
    """
    Get all supported file formats organized by category.
    
    Returns:
        Dictionary with format categories and their extensions
    """
    return DOCLING_FORMATS.copy()


def is_format_supported(file_path: str) -> bool:
    """
    Check if a file format is supported by Docling.
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        True if format is supported, False otherwise
    """
    file_ext = Path(file_path).suffix.lower()
    return file_ext in ALL_SUPPORTED_EXTENSIONS
