"""Enhanced document ingestion pipeline with storage layer integration.

This module integrates Docling document processing with the storage layer:
- PostgreSQL: Stores chunks with embeddings
- SQLite: Tracks file metadata and changes
- Neo4j: Builds knowledge graph from entities

Usage:
    python main_async.py                    # Ingest all documents
    python main_async.py --rebuild-index    # Force rebuild FAISS index
"""

import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Set USER_AGENT early
os.environ['USER_AGENT'] = os.getenv("USER_AGENT", "rag-chatbot/1.0")

import yaml
from dotenv import load_dotenv

# LangChain imports
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

try:
    from langchain_core.documents import Document
except ImportError:
    from langchain.schema import Document

from langchain_community.vectorstores import FAISS

# Docling imports
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import ConversionStatus
    from docling.datamodel.pipeline_options import PipelineOptions
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False

# Storage layer imports
from src.storage import StorageOrchestrator
from utils import get_embeddings_model

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_config(config_path: str = 'config.yaml') -> Dict[str, Any]:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)


class AsyncDocumentIngestionPipeline:
    """Async pipeline for end-to-end document ingestion with storage integration."""

    # Supported file extensions (36+ formats via Docling)
    SUPPORTED_EXTENSIONS = {
        # Documents
        ".pdf", ".docx", ".pptx", ".xlsx", ".html", ".htm",
        # Images
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp",
        # Videos
        ".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm",
        # Audio
        ".mp3", ".wav", ".aac", ".flac", ".m4a", ".ogg", ".wma",
        # Text
        ".txt", ".md", ".rst", ".markdown", ".latex", ".tex", ".xml", ".json",
        ".asciidoc", ".adoc"
    }

    SKIP_EXTENSIONS = {
        '.py', '.pyc', '.pyo', '.js', '.ts', '.java', '.class',
        '.yaml', '.yml', '.toml', '.ini', '.cfg',
        '.zip', '.rar', '.7z', '.tar', '.gz',
        '.log', '.tmp', '.bak', '.swp', '.DS_Store'
    }

    def __init__(
        self,
        config: Dict[str, Any],
        storage: StorageOrchestrator,
        enable_ocr: bool = False,
        enable_table_structure: bool = False,
    ):
        """Initialize ingestion pipeline.
        
        Args:
            config: Configuration dictionary
            storage: StorageOrchestrator instance
            enable_ocr: Enable OCR for images
            enable_table_structure: Enable table structure extraction
        """
        self.config = config
        self.storage = storage
        self.enable_ocr = enable_ocr
        self.enable_table_structure = enable_table_structure
        
        self.data_dir = Path(config['DATA_DIR'])
        self.index_dir = Path(config['INDEX_DIR'])
        
        self.converter = None
        self.embeddings = None
        self.splitter = None
        
        # Statistics
        self.stats = {
            'files_processed': 0,
            'files_failed': 0,
            'chunks_stored': 0,
            'entities_extracted': 0,
            'start_time': None,
            'end_time': None,
        }

    async def initialize(self):
        """Initialize all components."""
        logger.info("Initializing document ingestion pipeline...")
        
        # Initialize Docling converter
        self._init_converter()
        
        # Initialize embeddings model
        logger.info("Loading embeddings model...")
        self.embeddings = get_embeddings_model()
        
        # Initialize text splitter
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.get('CHUNK_SIZE', 512),
            chunk_overlap=self.config.get('CHUNK_OVERLAP', 50),
        )
        
        # Initialize storage backends
        logger.info("Initializing storage backends...")
        await self.storage.init_postgres()
        self.storage.init_metadata()
        self.storage.init_neo4j()
        
        # Check health
        health = await self.storage.health_check()
        logger.info("Storage health check:")
        for backend, status in health.items():
            logger.info(f"  {backend}: {status['status']}")
        
        logger.info("Pipeline initialization complete!")

    def _init_converter(self):
        """Initialize Docling converter with error handling."""
        if not DOCLING_AVAILABLE:
            raise ImportError("Docling not installed. Run: pip install docling")
        
        try:
            options = PipelineOptions(
                do_ocr=self.enable_ocr,
                do_table_structure=self.enable_table_structure,
                do_classify_tables=False,
            )
            self.converter = DocumentConverter(pipeline_options=options)
            logger.info(f"Docling converter initialized (OCR: {self.enable_ocr}, Tables: {self.enable_table_structure})")
        except Exception as e:
            logger.warning(f"Failed with custom options: {e}")
            try:
                self.converter = DocumentConverter()
                logger.info("Docling converter initialized (basic mode)")
            except Exception as e:
                logger.error(f"Failed to initialize converter: {e}")
                raise

    def _should_process_file(self, file_path: Path) -> bool:
        """Check if file should be processed."""
        # Skip directories
        if file_path.is_dir():
            return False
        
        # Skip .git and __pycache__
        if '.git' in file_path.parts or '__pycache__' in file_path.parts:
            return False
        
        # Check extension
        suffix = file_path.suffix.lower()
        if not suffix:
            return False
        
        if suffix in self.SKIP_EXTENSIONS:
            return False
        
        if suffix not in self.SUPPORTED_EXTENSIONS:
            return False
        
        return True

    def _convert_file(self, file_path: Path) -> Optional[str]:
        """Convert file to markdown text using Docling.
        
        Args:
            file_path: Path to file
            
        Returns:
            Markdown text or None
        """
        try:
            result = self.converter.convert(str(file_path))
            
            if result.status != ConversionStatus.SUCCESS:
                logger.warning(f"Conversion failed for {file_path.name}: {result.status}")
                return None
            
            if not result.document:
                logger.warning(f"No document returned from converter: {file_path.name}")
                return None
            
            text = result.document.export_to_markdown()
            if not text or not text.strip():
                logger.warning(f"No text extracted from {file_path.name}")
                return None
            
            return text
            
        except Exception as e:
            error_msg = str(e).lower()
            if any(x in error_msg for x in ['checkpoint', 'rt_detr', 'transformers', 'model']):
                logger.warning(f"Model compatibility issue: {e}")
            else:
                logger.error(f"Conversion error: {e}")
            return None

    def _extract_entities(self, text: str) -> List[tuple]:
        """Extract entities from text (placeholder).
        
        Args:
            text: Text to extract entities from
            
        Returns:
            List of (entity_name, entity_type) tuples
        """
        # TODO: Integrate with spaCy NER or transformer model
        entities = []
        
        # Simple keyword-based extraction for demo
        keywords = {
            "Person": ["Mr.", "Ms.", "Dr.", "Prof.", "CEO", "Developer"],
            "Organization": ["Inc.", "Corp.", "Ltd.", "University", "Company"],
            "Location": ["USA", "Europe", "Asia", "UK", "Canada"],
        }
        
        for entity_type, keywords_list in keywords.items():
            for keyword in keywords_list:
                if keyword in text:
                    entities.append((keyword, entity_type))
        
        return entities

    async def _store_chunks(
        self,
        file_id: str,
        file_path: Path,
        chunks: List[str],
    ) -> List[str]:
        """Store chunks in PostgreSQL and Neo4j.
        
        Args:
            file_id: Document file ID
            file_path: Path to source file
            chunks: List of text chunks
            
        Returns:
            List of PostgreSQL chunk IDs
        """
        postgres = await self.storage.init_postgres()
        neo4j = self.storage.init_neo4j()
        
        chunk_ids = []
        
        for chunk_idx, chunk_text in enumerate(chunks):
            try:
                # Compute embedding
                embedding = self.embeddings.embed_query(chunk_text)
                
                # Store in PostgreSQL
                chunk_id = await postgres.store_chunk(
                    file_id=file_id,
                    chunk_index=chunk_idx,
                    text=chunk_text,
                    embedding=embedding,
                    metadata={
                        "source": str(file_path),
                        "chunk_index": chunk_idx,
                        "total_chunks": len(chunks),
                    },
                )
                chunk_ids.append(chunk_id)
                self.stats['chunks_stored'] += 1
                
                # Extract and store entities in Neo4j
                entities = self._extract_entities(chunk_text)
                if entities:
                    chunk_entities = neo4j.extract_entities_from_chunk(
                        chunk_id=chunk_id,
                        text=chunk_text,
                        doc_id=file_id,
                        entities=entities,
                    )
                    self.stats['entities_extracted'] += len(chunk_entities)
                    
            except Exception as e:
                logger.error(f"Error storing chunk {chunk_idx}: {e}")
                continue
        
        return chunk_ids

    async def ingest_documents(self, rebuild_faiss: bool = False) -> Dict[str, Any]:
        """Ingest all documents from data directory.
        
        Args:
            rebuild_faiss: Force rebuild FAISS index
            
        Returns:
            Ingestion statistics
        """
        self.stats['start_time'] = datetime.now()
        logger.info("=" * 70)
        logger.info("STARTING DOCUMENT INGESTION")
        logger.info("=" * 70)
        logger.info(f"Data directory: {self.data_dir}")
        logger.info(f"Index directory: {self.index_dir}")
        
        postgres = await self.storage.init_postgres()
        metadata = self.storage.init_metadata()
        neo4j = self.storage.init_neo4j()
        
        # Get metadata store for change tracking
        all_chunks = []
        all_documents = []
        
        logger.info("Scanning documents...")
        
        # Process each file
        for file_path in self.data_dir.rglob('*'):
            if not self._should_process_file(file_path):
                continue
            
            file_id = f"{file_path.stem}_{int(file_path.stat().st_mtime)}"
            
            try:
                # Check if file changed
                if not metadata.has_file_changed(file_id, str(file_path)):
                    logger.info(f"⊘ Skipping unchanged: {file_path.name}")
                    continue
                
                logger.info(f"→ Processing: {file_path.name}")
                
                # Track file
                file_info = metadata.add_file(
                    file_id=file_id,
                    path=str(file_path),
                    mime_type=file_path.suffix,
                    tags=["auto-ingested"],
                )
                
                # Convert file
                text = self._convert_file(file_path)
                if not text:
                    logger.warning(f"  ✗ Conversion failed")
                    metadata.record_error(file_id, "Conversion failed")
                    self.stats['files_failed'] += 1
                    continue
                
                # Create document
                doc = Document(
                    page_content=text,
                    metadata={
                        "source": str(file_path),
                        "file_name": file_path.name,
                        "file_type": file_path.suffix,
                        "file_size": file_path.stat().st_size,
                    },
                )
                all_documents.append(doc)
                
                # Create document node in Neo4j
                doc_node = neo4j.create_document_node(
                    doc_id=file_id,
                    file_path=str(file_path),
                    doc_type=file_path.suffix,
                    metadata=file_info,
                )
                
                # Split into chunks
                chunks = self.splitter.split_documents([doc])
                chunk_texts = [chunk.page_content for chunk in chunks]
                all_chunks.extend(chunks)
                
                # Store chunks
                chunk_ids = await self._store_chunks(
                    file_id=file_id,
                    file_path=file_path,
                    chunks=chunk_texts,
                )
                
                # Mark indexed
                metadata.mark_indexed(file_id, chunk_ids)
                self.stats['files_processed'] += 1
                
                logger.info(f"  ✓ Stored {len(chunk_ids)} chunks, "
                           f"{self.stats['entities_extracted']} entities")
                
            except Exception as e:
                logger.error(f"Error processing {file_path.name}: {e}")
                metadata.record_error(file_id, str(e))
                self.stats['files_failed'] += 1
                continue
        
        # Build FAISS index
        if all_chunks:
            logger.info("=" * 70)
            logger.info("Building FAISS index...")
            
            try:
                self.index_dir.mkdir(parents=True, exist_ok=True)
                vectorstore = FAISS.from_documents(all_chunks, self.embeddings)
                vectorstore.save_local(str(self.index_dir))
                logger.info(f"✓ FAISS index saved to: {self.index_dir}")
            except Exception as e:
                logger.error(f"Failed to build FAISS index: {e}")
                self.stats['files_failed'] += 1
        else:
            logger.warning("No chunks to index")
        
        # Get statistics
        file_stats = metadata.get_file_stats()
        graph_stats = neo4j.get_graph_stats()
        
        self.stats['end_time'] = datetime.now()
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        # Log results
        logger.info("=" * 70)
        logger.info("INGESTION COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Files processed: {self.stats['files_processed']}")
        logger.info(f"Files failed: {self.stats['files_failed']}")
        logger.info(f"Chunks stored: {self.stats['chunks_stored']}")
        logger.info(f"Entities extracted: {self.stats['entities_extracted']}")
        logger.info(f"Total indexed files: {file_stats['total_files']}")
        logger.info(f"Graph nodes: {graph_stats['total_nodes']}")
        logger.info(f"Graph relationships: {graph_stats['total_relationships']}")
        logger.info(f"Duration: {duration:.2f}s")
        logger.info("=" * 70)
        
        self.stats.update({
            'file_stats': file_stats,
            'graph_stats': graph_stats,
            'duration_seconds': duration,
        })
        
        return self.stats

    async def cleanup(self):
        """Close all connections."""
        await self.storage.close()


async def main(rebuild_faiss: bool = False):
    """Main entry point for async document ingestion."""
    config = load_config()
    
    # Initialize storage orchestrator
    storage = StorageOrchestrator(
        postgres_url=os.getenv(
            'DATABASE_URL',
            'postgresql://postgres:postgres@localhost:5432/rag_db'
        ),
        neo4j_uri=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
        neo4j_user=os.getenv('NEO4J_USER', 'neo4j'),
        neo4j_password=os.getenv('NEO4J_PASSWORD', 'password'),
        metadata_db_path='.rag_metadata.db',
    )
    
    # Create pipeline
    pipeline = AsyncDocumentIngestionPipeline(config, storage)
    
    try:
        # Initialize
        await pipeline.initialize()
        
        # Ingest documents
        stats = await pipeline.ingest_documents(rebuild_faiss=rebuild_faiss)
        
        return stats
        
    except KeyboardInterrupt:
        logger.info("Ingestion interrupted by user")
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise
    finally:
        await pipeline.cleanup()


if __name__ == "__main__":
    import sys
    
    rebuild = "--rebuild-index" in sys.argv
    asyncio.run(main(rebuild_faiss=rebuild))
