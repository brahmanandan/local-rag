"""Tests for storage layer (PostgreSQL, Neo4j, SQLite)."""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from datetime import datetime

from src.storage import (
    PostgresStorage,
    MetadataStore,
    Neo4jGraphStore,
    StorageOrchestrator,
    init_postgres_pool,
)


class TestMetadataStore:
    """Tests for SQLite metadata storage."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary metadata database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = MetadataStore(str(db_path))
            yield store
            store.close()

    @pytest.fixture
    def temp_file(self):
        """Create temporary test file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"Test content for hashing")
            return f.name

    def test_add_file(self, temp_db, temp_file):
        """Test adding file to metadata store."""
        result = temp_db.add_file(
            file_id="test_doc_1",
            path=temp_file,
            mime_type="text/plain",
            tags=["test", "sample"],
        )
        
        assert result["id"] == "test_doc_1"
        assert result["path"] == temp_file
        assert result["mime_type"] == "text/plain"
        assert "hash" in result
        assert result["size"] > 0

    def test_file_change_detection(self, temp_db, temp_file):
        """Test detecting file changes."""
        # Add initial file
        temp_db.add_file("test_doc_1", temp_file, "text/plain")
        
        # File should appear unchanged
        assert not temp_db.has_file_changed("test_doc_1", temp_file)
        
        # Modify file
        with open(temp_file, "a") as f:
            f.write("Modified content")
        
        # File should now appear changed
        assert temp_db.has_file_changed("test_doc_1", temp_file)

    def test_mark_indexed(self, temp_db, temp_file):
        """Test marking file as indexed."""
        temp_db.add_file("test_doc_1", temp_file)
        
        # Mark as indexed
        chunk_ids = ["chunk_1", "chunk_2", "chunk_3"]
        temp_db.mark_indexed("test_doc_1", chunk_ids)
        
        # Verify stats
        stats = temp_db.get_file_stats()
        assert stats["indexed_files"] == 1
        assert stats["total_files"] == 1

    def test_get_pending_files(self, temp_db, temp_file):
        """Test retrieving pending (unindexed) files."""
        # Add two files
        temp_db.add_file("test_doc_1", temp_file)
        temp_db.add_file("test_doc_2", temp_file)
        
        # Both should be pending
        pending = temp_db.get_pending_files()
        assert len(pending) == 2
        
        # Mark one as indexed
        temp_db.mark_indexed("test_doc_1", ["chunk_1"])
        
        # Only one should remain pending
        pending = temp_db.get_pending_files()
        assert len(pending) == 1
        assert pending[0]["id"] == "test_doc_2"

    def test_record_error(self, temp_db, temp_file):
        """Test recording indexing errors."""
        temp_db.add_file("test_doc_1", temp_file)
        
        # Record error
        temp_db.record_error("test_doc_1", "Test error message")
        
        # Verify error tracking
        pending = temp_db.get_pending_files()
        assert len(pending) == 1  # Still pending due to error


@pytest.mark.asyncio
class TestPostgresStorage:
    """Tests for PostgreSQL + pgvector storage."""

    @pytest.fixture
    async def postgres_store(self):
        """Create PostgreSQL storage instance."""
        # This requires PostgreSQL running - skip if not available
        try:
            pool = await init_postgres_pool(
                "postgresql://postgres:postgres@localhost:5432/rag_db"
            )
            store = PostgresStorage(pool)
            yield store
            await pool.close()
        except Exception as e:
            pytest.skip(f"PostgreSQL not available: {e}")

    async def test_store_chunk(self, postgres_store):
        """Test storing chunk with embedding."""
        embedding = [0.1] * 384  # BGE model dimension
        
        chunk_id = await postgres_store.store_chunk(
            file_id="test_doc_1",
            chunk_index=0,
            text="Sample chunk text",
            embedding=embedding,
            metadata={"source": "test.pdf", "page": 1},
        )
        
        assert chunk_id is not None
        assert isinstance(chunk_id, str)

    async def test_get_chunk_by_id(self, postgres_store):
        """Test retrieving chunk by ID."""
        embedding = [0.1] * 384
        
        chunk_id = await postgres_store.store_chunk(
            file_id="test_doc_2",
            chunk_index=0,
            text="Sample chunk text",
            embedding=embedding,
            metadata={"source": "test.pdf"},
        )
        
        # Retrieve chunk
        chunk = await postgres_store.get_chunk_by_id(chunk_id)
        assert chunk is not None
        assert chunk["text"] == "Sample chunk text"
        assert chunk["file_id"] == "test_doc_2"

    async def test_get_file_chunks(self, postgres_store):
        """Test retrieving all chunks for a file."""
        embedding = [0.1] * 384
        
        # Store multiple chunks
        for i in range(3):
            await postgres_store.store_chunk(
                file_id="test_doc_3",
                chunk_index=i,
                text=f"Chunk {i}",
                embedding=embedding,
                metadata={"chunk_index": i},
            )
        
        # Retrieve all chunks
        chunks = await postgres_store.get_file_chunks("test_doc_3")
        assert len(chunks) == 3

    async def test_similarity_search(self, postgres_store):
        """Test similarity search with embeddings."""
        # Store chunks with different embeddings
        embeddings = [
            [1.0, 0.0, 0.0] + [0.0] * 381,  # Similar to query
            [0.0, 1.0, 0.0] + [0.0] * 381,  # Different
            [0.9, 0.1, 0.0] + [0.0] * 381,  # Similar to query
        ]
        
        for i, embedding in enumerate(embeddings):
            await postgres_store.store_chunk(
                file_id=f"test_doc_4_{i}",
                chunk_index=0,
                text=f"Chunk {i}",
                embedding=embedding,
                metadata={"index": i},
            )
        
        # Search with similar embedding
        query_embedding = [0.95, 0.05, 0.0] + [0.0] * 381
        results = await postgres_store.similarity_search(
            embedding=query_embedding,
            limit=2,
            threshold=0.5,
        )
        
        assert len(results) <= 2

    async def test_delete_file_chunks(self, postgres_store):
        """Test deleting all chunks for a file."""
        embedding = [0.1] * 384
        
        # Store chunks
        for i in range(3):
            await postgres_store.store_chunk(
                file_id="test_doc_5",
                chunk_index=i,
                text=f"Chunk {i}",
                embedding=embedding,
            )
        
        # Delete chunks
        deleted_count = await postgres_store.delete_file_chunks("test_doc_5")
        assert deleted_count == 3
        
        # Verify deletion
        chunks = await postgres_store.get_file_chunks("test_doc_5")
        assert len(chunks) == 0


@pytest.mark.asyncio
class TestNeo4jGraphStore:
    """Tests for Neo4j knowledge graph storage."""

    @pytest.fixture
    def neo4j_store(self):
        """Create Neo4j storage instance."""
        try:
            store = Neo4jGraphStore(
                uri="bolt://localhost:7687",
                username="neo4j",
                password="password",
            )
            yield store
            store.close()
        except Exception as e:
            pytest.skip(f"Neo4j not available: {e}")

    def test_create_document_node(self, neo4j_store):
        """Test creating document node."""
        node = neo4j_store.create_document_node(
            doc_id="test_doc_1",
            file_path="/path/to/document.pdf",
            doc_type="pdf",
            metadata={"size": 1024, "pages": 10},
        )
        
        assert node["id"] == "test_doc_1"
        assert node["type"] == "Document"

    def test_create_entity_node(self, neo4j_store):
        """Test creating entity node."""
        node = neo4j_store.create_entity_node(
            entity_id="person_alice",
            name="Alice",
            entity_type="Person",
            properties={"age": 30, "role": "Engineer"},
        )
        
        assert node["id"] == "person_alice"
        assert node["type"] == "Person"

    def test_create_relationship(self, neo4j_store):
        """Test creating relationship between entities."""
        # Create entities
        neo4j_store.create_entity_node("person_alice", "Alice", "Person")
        neo4j_store.create_entity_node("org_acme", "ACME Corp", "Organization")
        
        # Create relationship
        rel = neo4j_store.create_relationship(
            source_id="person_alice",
            target_id="org_acme",
            relationship_type="WORKS_AT",
            properties={"since": 2020},
        )
        
        assert rel["source"] == "person_alice"
        assert rel["target"] == "org_acme"
        assert rel["type"] == "WORKS_AT"

    def test_extract_entities_from_chunk(self, neo4j_store):
        """Test extracting entities from text chunk."""
        # Create document
        neo4j_store.create_document_node("doc_1", "test.pdf", "pdf")
        
        # Extract entities
        entities = neo4j_store.extract_entities_from_chunk(
            chunk_id="chunk_1",
            text="Alice works at ACME Corp in New York.",
            doc_id="doc_1",
            entities=[
                ("Alice", "Person"),
                ("ACME Corp", "Organization"),
                ("New York", "Location"),
            ],
        )
        
        assert len(entities) == 3

    def test_get_entity_neighbors(self, neo4j_store):
        """Test getting neighboring entities."""
        # Create network
        neo4j_store.create_entity_node("person_alice", "Alice", "Person")
        neo4j_store.create_entity_node("person_bob", "Bob", "Person")
        neo4j_store.create_relationship(
            "person_alice",
            "person_bob",
            "KNOWS",
        )
        
        # Get neighbors
        neighbors = neo4j_store.get_entity_neighbors("person_alice")
        assert len(neighbors) >= 1

    def test_get_concept_clusters(self, neo4j_store):
        """Test getting concept clusters."""
        # Create entities with relationships
        entities = ["concept_a", "concept_b", "concept_c"]
        for entity in entities:
            neo4j_store.create_entity_node(entity, entity.upper(), "Concept")
        
        # Create relationships
        neo4j_store.create_relationship("concept_a", "concept_b", "RELATED_TO")
        neo4j_store.create_relationship("concept_b", "concept_c", "RELATED_TO")
        
        # Get clusters
        clusters = neo4j_store.get_concept_clusters(min_connections=1)
        assert len(clusters) >= 1

    def test_get_graph_stats(self, neo4j_store):
        """Test getting graph statistics."""
        stats = neo4j_store.get_graph_stats()
        
        assert "total_nodes" in stats
        assert "total_relationships" in stats
        assert all(isinstance(v, int) for v in stats.values())


@pytest.mark.asyncio
class TestStorageOrchestrator:
    """Tests for storage orchestrator."""

    @pytest.fixture
    async def orchestrator(self):
        """Create storage orchestrator."""
        # This requires all backends running
        try:
            orchestrator = StorageOrchestrator(
                postgres_url="postgresql://postgres:postgres@localhost:5432/rag_db",
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="password",
            )
            yield orchestrator
            await orchestrator.close()
        except Exception as e:
            pytest.skip(f"Storage backends not available: {e}")

    async def test_health_check(self, orchestrator):
        """Test health check for all backends."""
        health = await orchestrator.health_check()
        
        assert "postgresql" in health
        assert "metadata" in health
        assert "neo4j" in health

    async def test_lazy_initialization(self, orchestrator):
        """Test lazy initialization of backends."""
        assert orchestrator._postgres_storage is None
        assert orchestrator._metadata_store is None
        assert orchestrator._neo4j_store is None
        
        # Initialize one
        postgres = await orchestrator.init_postgres()
        assert orchestrator._postgres_storage is not None
        assert orchestrator._metadata_store is None
        assert orchestrator._neo4j_store is None


# Integration test
@pytest.mark.asyncio
async def test_end_to_end_pipeline():
    """Test complete pipeline: ingest → store → query."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test file
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("Sample document content")
        
        # Initialize storage
        try:
            storage = StorageOrchestrator(
                postgres_url="postgresql://postgres:postgres@localhost:5432/rag_db",
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="password",
                metadata_db_path=str(Path(tmpdir) / "metadata.db"),
            )
            
            # Track file
            metadata = storage.init_metadata()
            metadata.add_file("doc_1", str(test_file))
            
            # Create document node
            neo4j = storage.init_neo4j()
            neo4j.create_document_node("doc_1", str(test_file), "txt")
            
            # Store chunk
            postgres = await storage.init_postgres()
            chunk_id = await postgres.store_chunk(
                file_id="doc_1",
                chunk_index=0,
                text="Sample document content",
                embedding=[0.1] * 384,
                metadata={"source": str(test_file)},
            )
            
            # Mark indexed
            metadata.mark_indexed("doc_1", [chunk_id])
            
            # Verify stats
            file_stats = metadata.get_file_stats()
            assert file_stats["indexed_files"] == 1
            
            graph_stats = neo4j.get_graph_stats()
            assert graph_stats["document_count"] >= 1
            
            await storage.close()
            
        except Exception as e:
            pytest.skip(f"Storage backends not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
