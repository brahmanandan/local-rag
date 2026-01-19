#!/usr/bin/env python3
"""
Examples of using Docling for document processing in the RAG system.

This script demonstrates various ways to use Docling for:
- Converting individual files
- Processing directories with mixed media
- Checking supported formats
- Custom configuration
"""

import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import docling utilities
from docling_utils import (
    DoclingConverter,
    convert_file_to_document,
    process_directory,
    get_supported_formats,
    is_format_supported,
)

# Import LangChain utilities
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain_community.vectorstores import FAISS
from utils import get_embeddings_model


def example_1_single_file():
    """Example 1: Convert a single file to a Document."""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 1: Converting a single file")
    logger.info("="*60)
    
    # Create a converter instance
    converter = DoclingConverter(use_ocr=True)
    
    # Convert a file (adjust path as needed)
    file_path = "./rag-data/AI-Books/data/AI Agent Book.pdf"
    
    if Path(file_path).exists():
        doc = convert_file_to_document(file_path, converter)
        
        if doc:
            logger.info(f"✓ Successfully converted: {file_path}")
            logger.info(f"  Source: {doc.metadata['source']}")
            logger.info(f"  File size: {doc.metadata['file_size']} bytes")
            logger.info(f"  Content length: {len(doc.page_content)} characters")
            logger.info(f"  First 200 chars: {doc.page_content[:200]}...")
        else:
            logger.error(f"✗ Failed to convert: {file_path}")
    else:
        logger.warning(f"File not found: {file_path}")


def example_2_check_formats():
    """Example 2: Check supported formats and file format support."""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 2: Checking supported formats")
    logger.info("="*60)
    
    # Get all supported formats
    formats = get_supported_formats()
    
    logger.info("\nSupported formats by category:")
    for category, extensions in sorted(formats.items()):
        logger.info(f"\n  {category.upper()}:")
        for ext in sorted(extensions):
            logger.info(f"    {ext}")
    
    # Check specific files
    test_files = [
        "document.pdf",
        "presentation.pptx",
        "image.jpg",
        "video.mp4",
        "audio.mp3",
        "archive.zip",
        "unknown.xyz"
    ]
    
    logger.info("\nFile format support check:")
    for file_name in test_files:
        supported = is_format_supported(file_name)
        status = "✓ SUPPORTED" if supported else "✗ NOT SUPPORTED"
        logger.info(f"  {file_name:20} {status}")


def example_3_process_directory():
    """Example 3: Process entire directory with mixed media."""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 3: Processing entire directory")
    logger.info("="*60)
    
    data_dir = "./rag-data/AI-Books/data"
    
    if Path(data_dir).exists():
        try:
            # Process directory
            documents, stats = process_directory(
                directory_path=data_dir,
                use_ocr=True,
                max_files=10  # Limit to 10 files for demo
            )
            
            logger.info(f"\n✓ Processing complete!")
            logger.info(f"  Documents created: {len(documents)}")
            logger.info(f"  Successfully processed: {stats['processed_files']}")
            logger.info(f"  Failed: {stats['failed_files']}")
            logger.info(f"  Skipped: {stats['skipped_files']}")
            
            if stats['by_type']:
                logger.info("  Processed by type:")
                for file_type, count in sorted(stats['by_type'].items()):
                    logger.info(f"    {file_type}: {count}")
                    
        except Exception as e:
            logger.error(f"Error processing directory: {e}")
    else:
        logger.warning(f"Directory not found: {data_dir}")


def example_4_create_vector_index():
    """Example 4: Process documents and create vector index."""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 4: Creating vector index from documents")
    logger.info("="*60)
    
    try:
        # Process documents
        data_dir = "./rag-data/AI-Books/data"
        documents, stats = process_directory(
            directory_path=data_dir,
            use_ocr=False,  # Disable OCR for faster demo
            max_files=5     # Process only 5 files for demo
        )
        
        if not documents:
            logger.warning("No documents to index")
            return
        
        logger.info(f"\nProcessed {len(documents)} documents")
        
        # Split into chunks
        logger.info("Splitting documents into chunks...")
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100
        )
        texts = splitter.split_documents(documents)
        logger.info(f"Created {len(texts)} text chunks")
        
        # Create embeddings
        logger.info("Loading embeddings model...")
        embeddings = get_embeddings_model()
        
        # Create vector index
        logger.info("Creating FAISS vector index...")
        vectorstore = FAISS.from_documents(texts, embeddings)
        
        # Save index
        index_path = "./example_index"
        vectorstore.save_local(index_path)
        logger.info(f"✓ Vector index saved to: {index_path}")
        
        # Test retrieval
        logger.info("\nTesting retrieval with sample query...")
        query = "machine learning"
        results = vectorstore.similarity_search(query, k=3)
        logger.info(f"Retrieved {len(results)} results for query: '{query}'")
        for i, result in enumerate(results, 1):
            source = result.metadata.get('source', 'unknown')
            logger.info(f"  {i}. {Path(source).name}")
        
    except Exception as e:
        logger.error(f"Error creating vector index: {e}")
        import traceback
        traceback.print_exc()


def example_5_custom_processing():
    """Example 5: Custom processing with specific file types."""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 5: Custom processing with filters")
    logger.info("="*60)
    
    data_dir = "./rag-data/AI-Books/data"
    
    if Path(data_dir).exists():
        try:
            # Process directory
            documents, stats = process_directory(
                directory_path=data_dir,
                skip_patterns=['.git', '__pycache__', 'images', 'videos'],
                use_ocr=False,
                max_files=3
            )
            
            logger.info(f"\n✓ Custom processing complete!")
            logger.info(f"  Total files found: {stats['total_files']}")
            logger.info(f"  Processed: {stats['processed_files']}")
            logger.info(f"  Skipped: {stats['skipped_files']}")
            logger.info(f"  Failed: {stats['failed_files']}")
            
            # Analyze content
            if documents:
                total_chars = sum(len(doc.page_content) for doc in documents)
                avg_chars = total_chars / len(documents)
                logger.info(f"\nContent Statistics:")
                logger.info(f"  Total documents: {len(documents)}")
                logger.info(f"  Total characters: {total_chars:,}")
                logger.info(f"  Average chars per document: {avg_chars:,.0f}")
                
        except Exception as e:
            logger.error(f"Error in custom processing: {e}")
    else:
        logger.warning(f"Directory not found: {data_dir}")


def main():
    """Run all examples."""
    logger.info("\n")
    logger.info("#" * 60)
    logger.info("# DOCLING INTEGRATION EXAMPLES")
    logger.info("#" * 60)
    
    try:
        # Run examples
        example_2_check_formats()    # This one doesn't require actual files
        example_1_single_file()
        example_3_process_directory()
        example_5_custom_processing()
        
        # Uncomment to test vector index creation (requires embeddings model)
        # example_4_create_vector_index()
        
    except KeyboardInterrupt:
        logger.info("\n\nExamples interrupted by user")
    except Exception as e:
        logger.error(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()
    
    logger.info("\n")
    logger.info("#" * 60)
    logger.info("# EXAMPLES COMPLETE")
    logger.info("#" * 60)
    logger.info("\nFor more information, see DOCLING_GUIDE.md")
    logger.info("\n")


if __name__ == "__main__":
    main()
