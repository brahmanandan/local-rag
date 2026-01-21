"""
Filesystem traversal and metadata tracking for RAG system.

Provides recursive directory scanning, MIME type detection, file change tracking,
and watchdog-based file system monitoring with incremental update support.
"""

import asyncio
import hashlib
import json
import logging
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Callable, Any
from enum import Enum

import filetype
from watchdog.observers import Observer
from watchdog.events import (
    FileSystemEventHandler,
    FileModifiedEvent,
    FileCreatedEvent,
    FileDeletedEvent,
)

logger = logging.getLogger(__name__)


class FileChangeType(str, Enum):
    """Types of file changes detected."""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    UNCHANGED = "unchanged"


@dataclass
class FileMetadata:
    """Metadata for a file in the system."""
    file_id: str  # SHA256 hash of path
    path: str
    absolute_path: str
    name: str
    mime_type: Optional[str]
    file_size: int
    created_at: datetime
    modified_at: datetime
    indexed_at: Optional[datetime]
    file_hash: str  # SHA256 of file content
    indexed: bool
    is_directory: bool
    tags: List[str]
    metadata_json: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            **asdict(self),
            'created_at': self.created_at.isoformat(),
            'modified_at': self.modified_at.isoformat(),
            'indexed_at': self.indexed_at.isoformat() if self.indexed_at else None,
            'metadata_json': json.dumps(self.metadata_json),
        }


# Supported document formats
DOCLING_FORMATS = {
    # Documents
    'pdf', 'docx', 'doc', 'pptx', 'ppt', 'xlsx', 'xls',
    'html', 'htm', 'txt', 'md', 'markdown', 'rst',
    'latex', 'tex', 'xml', 'json', 'asciidoc', 'adoc',
    
    # Images (with OCR)
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif', 'webp',
    
    # Video (keyframes/metadata)
    'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv', 'webm', 'm4v',
    
    # Audio (transcription)
    'mp3', 'wav', 'aac', 'flac', 'm4a', 'ogg', 'wma', 'opus',
}


class FilesystemTraversal:
    """Recursive filesystem traversal with metadata extraction."""

    def __init__(self, data_dir: Path, metadata_db: Optional[Path] = None):
        """Initialize filesystem traversal.
        
        Args:
            data_dir: Root directory to traverse
            metadata_db: Path to SQLite metadata database
        """
        self.data_dir = Path(data_dir)
        self.metadata_db = metadata_db or Path(".rag_metadata.db")
        
        if not self.data_dir.exists():
            raise ValueError(f"Data directory does not exist: {self.data_dir}")
        
        logger.info(f"Initialized filesystem traversal for: {self.data_dir}")

    @staticmethod
    def compute_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
        """Compute hash of file content.
        
        Args:
            file_path: Path to file
            algorithm: Hash algorithm (sha256, md5, sha1)
            
        Returns:
            Hex digest of file hash
        """
        hasher = hashlib.new(algorithm)
        try:
            with open(file_path, 'rb') as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except (OSError, IOError) as e:
            logger.warning(f"Failed to compute hash for {file_path}: {e}")
            return ""

    @staticmethod
    def compute_path_hash(file_path: Path) -> str:
        """Compute hash of file path (for unique file_id).
        
        Args:
            file_path: Path to file
            
        Returns:
            Hex digest of path hash
        """
        return hashlib.sha256(str(file_path).encode()).hexdigest()

    @staticmethod
    def detect_mime_type(file_path: Path) -> Optional[str]:
        """Detect MIME type of file.
        
        Args:
            file_path: Path to file
            
        Returns:
            MIME type string or None
        """
        try:
            kind = filetype.guess(str(file_path))
            return kind.mime if kind else None
        except Exception as e:
            logger.debug(f"Failed to detect MIME type for {file_path}: {e}")
            return None

    @staticmethod
    def is_supported_format(file_path: Path) -> bool:
        """Check if file format is supported by Docling.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if format is supported
        """
        suffix = file_path.suffix.lstrip('.').lower()
        return suffix in DOCLING_FORMATS

    def extract_file_metadata(self, file_path: Path) -> FileMetadata:
        """Extract metadata for a single file.
        
        Args:
            file_path: Path to file
            
        Returns:
            FileMetadata object
        """
        stat = file_path.stat()
        
        metadata = FileMetadata(
            file_id=self.compute_path_hash(file_path),
            path=str(file_path.relative_to(self.data_dir)),
            absolute_path=str(file_path),
            name=file_path.name,
            mime_type=self.detect_mime_type(file_path),
            file_size=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            indexed_at=None,
            file_hash=self.compute_file_hash(file_path) if file_path.is_file() else "",
            indexed=False,
            is_directory=file_path.is_dir(),
            tags=[],
            metadata_json={
                'format': file_path.suffix.lstrip('.').lower(),
                'supported': self.is_supported_format(file_path),
            },
        )
        
        return metadata

    def traverse(self, extensions: Optional[Set[str]] = None) -> List[FileMetadata]:
        """Recursively traverse directory and extract metadata.
        
        Args:
            extensions: Optional set of file extensions to include (e.g., {'pdf', 'docx'})
                       If None, includes all supported formats
            
        Returns:
            List of FileMetadata objects
        """
        files = []
        
        for file_path in self.data_dir.rglob('*'):
            if file_path.is_dir():
                continue
            
            # Filter by extension if provided
            if extensions:
                suffix = file_path.suffix.lstrip('.').lower()
                if suffix not in extensions:
                    continue
            
            # Always check if format is supported
            if not self.is_supported_format(file_path):
                logger.debug(f"Skipping unsupported format: {file_path}")
                continue
            
            try:
                metadata = self.extract_file_metadata(file_path)
                files.append(metadata)
            except Exception as e:
                logger.error(f"Failed to extract metadata for {file_path}: {e}")
                continue
        
        logger.info(f"Traversed {len(files)} files in {self.data_dir}")
        return files


class FilesystemWatcher(FileSystemEventHandler):
    """Watch filesystem for changes and trigger callbacks."""

    def __init__(self, callback: Callable[[Path, FileChangeType], Any]):
        """Initialize filesystem watcher.
        
        Args:
            callback: Async callback function(file_path, change_type)
        """
        self.callback = callback
        self.debounce_delay = 1.0  # Seconds
        self.pending_events: Dict[Path, FileChangeType] = {}
        self.debounce_task: Optional[asyncio.Task] = None

    def on_created(self, event: FileCreatedEvent) -> None:
        """Handle file creation."""
        if event.is_directory:
            return
        self._schedule_callback(Path(event.src_path), FileChangeType.CREATED)

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modification."""
        if event.is_directory:
            return
        self._schedule_callback(Path(event.src_path), FileChangeType.MODIFIED)

    def on_deleted(self, event: FileDeletedEvent) -> None:
        """Handle file deletion."""
        if event.is_directory:
            return
        self._schedule_callback(Path(event.src_path), FileChangeType.DELETED)

    def _schedule_callback(self, file_path: Path, change_type: FileChangeType) -> None:
        """Schedule debounced callback for file change.
        
        Args:
            file_path: Path to file
            change_type: Type of change
        """
        # Update pending events (last event wins within debounce window)
        self.pending_events[file_path] = change_type
        
        # Cancel previous debounce task if exists
        if self.debounce_task and not self.debounce_task.done():
            self.debounce_task.cancel()
        
        # Schedule new debounce task
        self.debounce_task = asyncio.create_task(self._execute_callbacks())

    async def _execute_callbacks(self) -> None:
        """Execute pending callbacks after debounce delay."""
        await asyncio.sleep(self.debounce_delay)
        
        for file_path, change_type in self.pending_events.items():
            try:
                if asyncio.iscoroutinefunction(self.callback):
                    await self.callback(file_path, change_type)
                else:
                    self.callback(file_path, change_type)
            except Exception as e:
                logger.error(f"Error in filesystem change callback: {e}")
        
        self.pending_events.clear()


class MetadataTracker:
    """Track file metadata and changes in SQLite."""

    def __init__(self, db_path: Path = Path(".rag_metadata.db")):
        """Initialize metadata tracker.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    file_id TEXT PRIMARY KEY,
                    path TEXT NOT NULL UNIQUE,
                    absolute_path TEXT,
                    name TEXT,
                    mime_type TEXT,
                    file_size INTEGER,
                    created_at TEXT,
                    modified_at TEXT,
                    indexed_at TEXT,
                    file_hash TEXT,
                    indexed INTEGER DEFAULT 0,
                    is_directory INTEGER,
                    tags TEXT,
                    metadata_json TEXT,
                    created_timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS file_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT NOT NULL,
                    path TEXT NOT NULL,
                    change_type TEXT NOT NULL,
                    detected_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    processed INTEGER DEFAULT 0,
                    error_message TEXT,
                    FOREIGN KEY(file_id) REFERENCES files(file_id)
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_files_indexed ON files(indexed)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_files_mime ON files(mime_type)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_changes_processed ON file_changes(processed)
            ''')
            
            conn.commit()
        
        logger.info(f"Initialized metadata database at {self.db_path}")

    def upsert_file(self, metadata: FileMetadata) -> None:
        """Insert or update file metadata.
        
        Args:
            metadata: FileMetadata object
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO files 
                (file_id, path, absolute_path, name, mime_type, file_size,
                 created_at, modified_at, indexed_at, file_hash, indexed,
                 is_directory, tags, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_id) DO UPDATE SET
                    file_hash = excluded.file_hash,
                    modified_at = excluded.modified_at,
                    file_size = excluded.file_size,
                    metadata_json = excluded.metadata_json
            ''', (
                metadata.file_id,
                metadata.path,
                metadata.absolute_path,
                metadata.name,
                metadata.mime_type,
                metadata.file_size,
                metadata.created_at.isoformat(),
                metadata.modified_at.isoformat(),
                metadata.indexed_at.isoformat() if metadata.indexed_at else None,
                metadata.file_hash,
                1 if metadata.indexed else 0,
                1 if metadata.is_directory else 0,
                json.dumps(metadata.tags),
                json.dumps(metadata.metadata_json),
            ))
            conn.commit()

    def has_file_changed(self, file_id: str, file_hash: str) -> bool:
        """Check if file has changed since last indexing.
        
        Args:
            file_id: File path hash
            file_hash: Current file content hash
            
        Returns:
            True if file is new or has changed
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT file_hash FROM files WHERE file_id = ?',
                (file_id,)
            )
            row = cursor.fetchone()
            
            if row is None:
                return True  # New file
            
            return row[0] != file_hash  # Changed if hashes differ

    def mark_indexed(self, file_id: str) -> None:
        """Mark file as indexed.
        
        Args:
            file_id: File path hash
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'UPDATE files SET indexed = 1, indexed_at = CURRENT_TIMESTAMP WHERE file_id = ?',
                (file_id,)
            )
            conn.commit()

    def mark_unindexed(self, file_id: str) -> None:
        """Mark file as unindexed.
        
        Args:
            file_id: File path hash
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'UPDATE files SET indexed = 0, indexed_at = NULL WHERE file_id = ?',
                (file_id,)
            )
            conn.commit()

    def get_indexed_files(self) -> List[str]:
        """Get all indexed file IDs.
        
        Returns:
            List of file IDs
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT file_id FROM files WHERE indexed = 1')
            return [row[0] for row in cursor.fetchall()]

    def get_unindexed_files(self) -> List[str]:
        """Get all unindexed files.
        
        Returns:
            List of file IDs
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT file_id FROM files WHERE indexed = 0')
            return [row[0] for row in cursor.fetchall()]

    def get_file_by_id(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file metadata by ID.
        
        Args:
            file_id: File path hash
            
        Returns:
            File metadata dictionary or None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM files WHERE file_id = ?',
                (file_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_file_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        """Get file metadata by path.
        
        Args:
            path: File path
            
        Returns:
            File metadata dictionary or None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM files WHERE path = ?',
                (path,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_file(self, file_id: str) -> None:
        """Delete file metadata.
        
        Args:
            file_id: File path hash
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM files WHERE file_id = ?', (file_id,))
            conn.commit()

    def record_change(
        self,
        file_id: str,
        path: str,
        change_type: FileChangeType,
        error_message: Optional[str] = None,
    ) -> None:
        """Record file change event.
        
        Args:
            file_id: File path hash
            path: File path
            change_type: Type of change
            error_message: Optional error message
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                '''
                INSERT INTO file_changes (file_id, path, change_type, error_message, processed)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (file_id, path, change_type.value, error_message, 0)
            )
            conn.commit()

    def get_unprocessed_changes(self) -> List[Dict[str, Any]]:
        """Get all unprocessed file changes.
        
        Returns:
            List of file change records
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM file_changes WHERE processed = 0 ORDER BY detected_at ASC'
            )
            return [dict(row) for row in cursor.fetchall()]

    def mark_change_processed(self, change_id: int, error_message: Optional[str] = None) -> None:
        """Mark file change as processed.
        
        Args:
            change_id: Change record ID
            error_message: Optional error message if processing failed
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                '''
                UPDATE file_changes 
                SET processed = 1, error_message = ?
                WHERE id = ?
                ''',
                (error_message, change_id)
            )
            conn.commit()

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about indexed files.
        
        Returns:
            Statistics dictionary
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_files,
                    SUM(CASE WHEN indexed = 1 THEN 1 ELSE 0 END) as indexed_files,
                    SUM(file_size) as total_size,
                    COUNT(DISTINCT mime_type) as unique_mime_types
                FROM files
            ''')
            row = cursor.fetchone()
            
            total = row[0] or 0
            indexed = row[1] or 0
            
            return {
                'total_files': total,
                'indexed_files': indexed,
                'unindexed_files': total - indexed,
                'total_size_bytes': row[2] or 0,
                'unique_mime_types': row[3] or 0,
                'indexing_percentage': (indexed / total * 100) if total > 0 else 0,
            }


class FilesystemMonitor:
    """High-level filesystem monitoring with incremental updates."""

    def __init__(
        self,
        data_dir: Path,
        metadata_db: Path = Path(".rag_metadata.db"),
        watch: bool = False,
    ):
        """Initialize filesystem monitor.
        
        Args:
            data_dir: Root directory to monitor
            metadata_db: Path to metadata database
            watch: Enable real-time file watching
        """
        self.traversal = FilesystemTraversal(data_dir, metadata_db)
        self.tracker = MetadataTracker(metadata_db)
        self.observer: Optional[Observer] = None
        self.watch_enabled = watch
        self._on_change_callback: Optional[Callable] = None

    def set_change_callback(self, callback: Callable) -> None:
        """Set callback for file changes.
        
        Args:
            callback: Async callback function(file_path, change_type)
        """
        self._on_change_callback = callback

    def scan(self, extensions: Optional[Set[str]] = None) -> Dict[str, Any]:
        """Scan filesystem and update metadata database.
        
        Args:
            extensions: Optional set of file extensions to include
            
        Returns:
            Statistics about the scan
        """
        logger.info("Starting filesystem scan...")
        
        # Traverse filesystem
        files = self.traversal.traverse(extensions)
        
        # Update database
        for metadata in files:
            self.tracker.upsert_file(metadata)
        
        stats = self.tracker.get_statistics()
        logger.info(f"Scan complete: {stats}")
        
        return stats

    def get_incremental_updates(self) -> List[Dict[str, Any]]:
        """Get files that have been modified since last index.
        
        Returns:
            List of file metadata for files needing reprocessing
        """
        unindexed = self.tracker.get_unindexed_files()
        files_to_process = []
        
        for file_id in unindexed:
            file_metadata = self.tracker.get_file_by_id(file_id)
            if file_metadata:
                files_to_process.append(file_metadata)
        
        return files_to_process

    def start_watching(self) -> None:
        """Start real-time filesystem watching."""
        if not self.watch_enabled or self._on_change_callback is None:
            logger.warning("Watching not enabled or callback not set")
            return
        
        handler = FilesystemWatcher(self._on_change_callback)
        self.observer = Observer()
        self.observer.schedule(handler, str(self.traversal.data_dir), recursive=True)
        self.observer.start()
        logger.info(f"Started watching {self.traversal.data_dir}")

    def stop_watching(self) -> None:
        """Stop real-time filesystem watching."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Stopped filesystem watching")

    def __enter__(self):
        """Context manager entry."""
        self.start_watching()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_watching()
