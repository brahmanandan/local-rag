"""Storage layer for RAG system with PostgreSQL, Neo4j, and metadata tracking."""

import logging
from typing import Optional
from contextlib import asynccontextmanager

from .postgres import PostgresStorage, init_postgres_pool
from .metadata import MetadataStore, init_metadata_db
from .neo4j_graph import Neo4jGraphStore, init_neo4j_graph

logger = logging.getLogger(__name__)


class StorageOrchestrator:
    """Orchestrates all storage backends (PostgreSQL, Neo4j, SQLite)."""

    def __init__(
        self,
        postgres_url: str,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        metadata_db_path: str = ".rag_metadata.db",
    ):
        """Initialize storage backends.
        
        Args:
            postgres_url: PostgreSQL connection string
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            metadata_db_path: Path to SQLite metadata database
        """
        self.postgres_url = postgres_url
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.metadata_db_path = metadata_db_path
        
        # Lazy initialization
        self._postgres_pool = None
        self._postgres_storage = None
        self._metadata_store = None
        self._neo4j_store = None

    async def init_postgres(self) -> PostgresStorage:
        """Initialize PostgreSQL backend.
        
        Returns:
            PostgresStorage instance
        """
        if self._postgres_storage is None:
            self._postgres_pool = await init_postgres_pool(self.postgres_url)
            self._postgres_storage = PostgresStorage(self._postgres_pool)
            logger.info("PostgreSQL storage initialized")
        return self._postgres_storage

    def init_metadata(self) -> MetadataStore:
        """Initialize metadata tracking backend.
        
        Returns:
            MetadataStore instance
        """
        if self._metadata_store is None:
            self._metadata_store = init_metadata_db(self.metadata_db_path)
            logger.info("Metadata storage initialized")
        return self._metadata_store

    def init_neo4j(self) -> Neo4jGraphStore:
        """Initialize Neo4j knowledge graph backend.
        
        Returns:
            Neo4jGraphStore instance
        """
        if self._neo4j_store is None:
            self._neo4j_store = init_neo4j_graph(
                uri=self.neo4j_uri,
                username=self.neo4j_user,
                password=self.neo4j_password,
            )
            logger.info("Neo4j graph storage initialized")
        return self._neo4j_store

    async def health_check(self) -> dict:
        """Check health of all storage backends.
        
        Returns:
            Health status for each backend
        """
        health = {}
        
        # PostgreSQL
        try:
            postgres = await self.init_postgres()
            # Simple query to test connection
            health["postgresql"] = {"status": "healthy"}
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            health["postgresql"] = {"status": "unhealthy", "error": str(e)}
        
        # Metadata
        try:
            metadata = self.init_metadata()
            stats = metadata.get_file_stats()
            health["metadata"] = {"status": "healthy", "stats": stats}
        except Exception as e:
            logger.error(f"Metadata health check failed: {e}")
            health["metadata"] = {"status": "unhealthy", "error": str(e)}
        
        # Neo4j
        try:
            neo4j = self.init_neo4j()
            stats = neo4j.get_graph_stats()
            health["neo4j"] = {"status": "healthy", "stats": stats}
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            health["neo4j"] = {"status": "unhealthy", "error": str(e)}
        
        return health

    async def close(self):
        """Close all storage backend connections."""
        if self._postgres_pool:
            await self._postgres_pool.close()
            logger.info("PostgreSQL pool closed")
        
        if self._metadata_store:
            self._metadata_store.close()
            logger.info("Metadata store closed")
        
        if self._neo4j_store:
            self._neo4j_store.close()
            logger.info("Neo4j store closed")


# Export main classes
__all__ = [
    "PostgresStorage",
    "init_postgres_pool",
    "MetadataStore",
    "init_metadata_db",
    "Neo4jGraphStore",
    "init_neo4j_graph",
    "StorageOrchestrator",
]
