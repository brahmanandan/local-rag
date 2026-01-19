"""PostgreSQL + pgvector storage for embeddings and document chunks."""

import logging
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import json

import asyncpg
from pgvector.asyncpg import register_vector

logger = logging.getLogger(__name__)


class PostgresStorage:
    """PostgreSQL storage with pgvector for embeddings."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def close(self):
        """Close the connection pool."""
        await self.pool.close()

    async def store_chunk(
        self,
        file_id: str,
        chunk_index: int,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a document chunk with its embedding.
        
        Args:
            file_id: Document file ID
            chunk_index: Chunk sequence number
            text: Chunk text content
            embedding: Vector embedding
            metadata: Additional metadata
            
        Returns:
            Chunk ID
        """
        async with self.pool.acquire() as conn:
            chunk_id = await conn.fetchval(
                """
                INSERT INTO chunks (file_id, chunk_index, text, embedding, metadata)
                VALUES ($1, $2, $3, $4::vector, $5)
                RETURNING id
                """,
                file_id,
                chunk_index,
                text,
                embedding,
                json.dumps(metadata or {}),
            )
            return str(chunk_id)

    async def similarity_search(
        self,
        embedding: List[float],
        limit: int = 5,
        threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Search chunks by embedding similarity.
        
        Args:
            embedding: Query embedding vector
            limit: Maximum results to return
            threshold: Minimum similarity score
            
        Returns:
            List of chunks with similarity scores
        """
        async with self.pool.acquire() as conn:
            results = await conn.fetch(
                """
                SELECT 
                    id, file_id, chunk_index, text, metadata,
                    1 - (embedding <=> $1::vector) as similarity
                FROM chunks
                WHERE 1 - (embedding <=> $1::vector) > $2
                ORDER BY embedding <=> $1::vector
                LIMIT $3
                """,
                embedding,
                threshold,
                limit,
            )
            return [dict(row) for row in results]

    async def get_file_chunks(self, file_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a file.
        
        Args:
            file_id: Document file ID
            
        Returns:
            List of chunks
        """
        async with self.pool.acquire() as conn:
            results = await conn.fetch(
                """
                SELECT id, file_id, chunk_index, text, metadata
                FROM chunks
                WHERE file_id = $1
                ORDER BY chunk_index
                """,
                file_id,
            )
            return [dict(row) for row in results]

    async def delete_file_chunks(self, file_id: str) -> int:
        """Delete all chunks for a file.
        
        Args:
            file_id: Document file ID
            
        Returns:
            Number of deleted chunks
        """
        async with self.pool.acquire() as conn:
            count = await conn.fetchval(
                "DELETE FROM chunks WHERE file_id = $1",
                file_id,
            )
            return count

    async def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific chunk by ID.
        
        Args:
            chunk_id: Chunk ID
            
        Returns:
            Chunk data or None
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT * FROM chunks WHERE id = $1",
                chunk_id,
            )
            return dict(result) if result else None


async def init_postgres_pool(
    database_url: str,
    min_size: int = 10,
    max_size: int = 20,
) -> asyncpg.Pool:
    """Initialize PostgreSQL connection pool with pgvector.
    
    Args:
        database_url: PostgreSQL connection string
        min_size: Minimum pool connections
        max_size: Maximum pool connections
        
    Returns:
        asyncpg connection pool
    """
    pool = await asyncpg.create_pool(
        database_url,
        min_size=min_size,
        max_size=max_size,
        init=register_vector,
    )
    
    # Create tables
    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE EXTENSION IF NOT EXISTS vector;
            
            CREATE TABLE IF NOT EXISTS chunks (
                id BIGSERIAL PRIMARY KEY,
                file_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                text TEXT NOT NULL,
                embedding vector(384),
                metadata JSONB,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(file_id, chunk_index)
            );
            
            CREATE INDEX IF NOT EXISTS idx_chunks_file_id ON chunks(file_id);
            CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
            """
        )
    
    logger.info(f"PostgreSQL pool initialized: {min_size}-{max_size} connections")
    return pool
