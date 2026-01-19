"""Local metadata storage for file tracking with SQLite."""

import logging
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import sqlite3
import json

logger = logging.getLogger(__name__)


class MetadataStore:
    """SQLite-based metadata store for file tracking and change detection."""

    def __init__(self, db_path: str = ".rag_metadata.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        """Initialize database schema."""
        cursor = self.conn.cursor()
        
        # Files table with hash tracking
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                path TEXT UNIQUE NOT NULL,
                mime_type TEXT,
                file_size INTEGER,
                file_hash TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_indexed_at TIMESTAMP,
                indexed BOOLEAN DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                last_error TEXT
            )
            """
        )
        
        # Chunks table (references)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS file_chunks (
                chunk_id INTEGER PRIMARY KEY,
                file_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                postgres_chunk_id TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
                UNIQUE(file_id, chunk_index)
            )
            """
        )
        
        # Change tracking
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS file_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT NOT NULL,
                change_type TEXT,  -- 'created', 'modified', 'deleted'
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES files(id)
            )
            """
        )
        
        # Metadata tags
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS file_metadata (
                file_id TEXT PRIMARY KEY,
                tags TEXT,  -- JSON array
                properties TEXT,  -- JSON object
                processing_options TEXT,  -- JSON object
                FOREIGN KEY (file_id) REFERENCES files(id)
            )
            """
        )
        
        self.conn.commit()
        logger.info(f"Metadata database initialized: {self.db_path}")

    @staticmethod
    def _compute_file_hash(file_path: str) -> str:
        """Compute SHA256 hash of file contents."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def add_file(
        self,
        file_id: str,
        path: str,
        mime_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Register a file for tracking.
        
        Args:
            file_id: Unique identifier for file
            path: File path
            mime_type: MIME type
            tags: Optional tags
            
        Returns:
            File metadata
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        file_hash = self._compute_file_hash(str(file_path))
        file_size = file_path.stat().st_size
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute(
                """
                INSERT INTO files 
                (id, path, mime_type, file_size, file_hash)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    file_hash = excluded.file_hash,
                    file_size = excluded.file_size,
                    modified_at = CURRENT_TIMESTAMP
                """,
                (file_id, str(file_path), mime_type, file_size, file_hash),
            )
            
            if tags:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO file_metadata (file_id, tags)
                    VALUES (?, ?)
                    """,
                    (file_id, json.dumps(tags)),
                )
            
            self.conn.commit()
            
            return {
                "id": file_id,
                "path": str(file_path),
                "size": file_size,
                "hash": file_hash,
                "mime_type": mime_type,
            }
        except sqlite3.IntegrityError as e:
            logger.error(f"Failed to add file: {e}")
            raise

    def has_file_changed(self, file_id: str, path: str) -> bool:
        """Check if file has been modified since last tracking.
        
        Args:
            file_id: File identifier
            path: File path
            
        Returns:
            True if file changed or not tracked
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT file_hash FROM files WHERE id = ?", (file_id,))
        row = cursor.fetchone()
        
        if not row:
            return True  # Not tracked yet
        
        old_hash = row[0]
        new_hash = self._compute_file_hash(path)
        
        return old_hash != new_hash

    def mark_indexed(self, file_id: str, postgres_chunk_ids: List[str]):
        """Mark file as successfully indexed.
        
        Args:
            file_id: File identifier
            postgres_chunk_ids: List of chunk IDs from PostgreSQL
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE files 
            SET indexed = 1, last_indexed_at = CURRENT_TIMESTAMP, error_count = 0
            WHERE id = ?
            """,
            (file_id,),
        )
        
        for i, chunk_id in enumerate(postgres_chunk_ids):
            cursor.execute(
                """
                INSERT OR REPLACE INTO file_chunks 
                (file_id, chunk_index, postgres_chunk_id)
                VALUES (?, ?, ?)
                """,
                (file_id, i, chunk_id),
            )
        
        self.conn.commit()

    def record_error(self, file_id: str, error: str):
        """Record indexing error for a file.
        
        Args:
            file_id: File identifier
            error: Error message
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE files 
            SET error_count = error_count + 1, last_error = ?
            WHERE id = ?
            """,
            (error, file_id),
        )
        self.conn.commit()

    def get_pending_files(self) -> List[Dict[str, Any]]:
        """Get files that need indexing.
        
        Returns:
            List of unindexed or changed files
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, path, mime_type FROM files 
            WHERE indexed = 0 OR last_indexed_at IS NULL
            ORDER BY created_at
            """
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_file_stats(self) -> Dict[str, Any]:
        """Get metadata store statistics.
        
        Returns:
            Stats about tracked files
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT 
                COUNT(*) as total_files,
                SUM(CASE WHEN indexed = 1 THEN 1 ELSE 0 END) as indexed_files,
                SUM(CASE WHEN indexed = 0 THEN 1 ELSE 0 END) as pending_files,
                SUM(file_size) as total_size
            FROM files
            """
        )
        row = cursor.fetchone()
        return {
            "total_files": row[0] or 0,
            "indexed_files": row[1] or 0,
            "pending_files": row[2] or 0,
            "total_size_bytes": row[3] or 0,
        }

    def close(self):
        """Close the database connection."""
        self.conn.close()
        logger.info("Metadata database closed")


def init_metadata_db(db_path: str = ".rag_metadata.db") -> MetadataStore:
    """Initialize metadata store.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        MetadataStore instance
    """
    return MetadataStore(db_path)
