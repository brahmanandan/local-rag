# Database & Storage Layer Setup Guide

## Overview

The RAG system now includes enterprise-grade storage with three integrated backends:

1. **PostgreSQL + pgvector**: Vector embeddings and chunk storage (production)
2. **Neo4j**: Knowledge graph for entity/relationship tracking
3. **SQLite/DuckDB**: Local file metadata and change detection

---

## Quick Setup

### 1. PostgreSQL + pgvector

#### macOS (using Homebrew)

```bash
# Install PostgreSQL
brew install postgresql@15

# Start PostgreSQL service
brew services start postgresql@15

# Create database
createdb rag_db

# Install pgvector extension
psql rag_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Set password for postgres user
psql -d rag_db -c "ALTER USER postgres WITH PASSWORD 'postgres';"
```

#### Docker (Alternative)

```bash
docker run --name rag-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=rag_db \
  -p 5432:5432 \
  -d pgvector/pgvector:pg15

# Verify
psql -h localhost -U postgres -d rag_db -c "SELECT version();"
```

**Connection String**: 
```
postgresql://postgres:postgres@localhost:5432/rag_db
```

### 2. Neo4j

#### Docker (Recommended)

```bash
docker run --name rag-neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -d neo4j:latest

# Verify - Open browser to http://localhost:7474
# Default: neo4j / password
```

#### Homebrew (macOS)

```bash
brew install neo4j

# Start Neo4j
brew services start neo4j

# Access: http://localhost:7474
# Default: neo4j / neo4j (change on first login)
```

**Connection Settings**:
- URI: `bolt://localhost:7687`
- Username: `neo4j`
- Password: `password` (or your custom)

### 3. SQLite (No Setup Required!)

SQLite is embedded and requires zero setup. Metadata database is created automatically at:
```
.rag_metadata.db
```

---

## Python Integration

### Install Dependencies

```bash
pip install psycopg asyncpg pgvector neo4j sqlalchemy
```

### Environment Configuration

Create `.env` or update your configuration:

```bash
# PostgreSQL
PG_URL="postgresql://postgres:postgres@localhost:5432/rag_db"

# Neo4j
NEO4J_URI="bolt://localhost:7687"
NEO4J_USER="neo4j"
NEO4J_PASSWORD="password"

# SQLite (auto-created)
METADATA_DB_PATH=".rag_metadata.db"
```

### Usage Example

```python
import asyncio
from src.storage import StorageOrchestrator

async def main():
    # Initialize
    storage = StorageOrchestrator(
        postgres_url="postgresql://postgres:postgres@localhost:5432/rag_db",
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
    )
    
    # Check health
    health = await storage.health_check()
    print(health)
    
    # Use individual backends
    postgres = await storage.init_postgres()
    metadata = storage.init_metadata()
    neo4j = storage.init_neo4j()
    
    # Store chunk
    chunk_id = await postgres.store_chunk(
        file_id="doc_1",
        chunk_index=0,
        text="Sample text...",
        embedding=[0.1, 0.2, ...],  # 384-dim for BGE model
        metadata={"source": "example.pdf"}
    )
    
    # Track file
    metadata.add_file(
        file_id="doc_1",
        path="example.pdf",
        mime_type="application/pdf"
    )
    
    # Create knowledge graph nodes
    doc_node = neo4j.create_document_node(
        doc_id="doc_1",
        file_path="example.pdf",
        doc_type="pdf"
    )
    
    # Close connections
    await storage.close()

asyncio.run(main())
```

---

## Architecture Details

### PostgreSQL Schema

```sql
-- Chunks table with vector embeddings
CREATE TABLE chunks (
    id BIGSERIAL PRIMARY KEY,
    file_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding vector(384),  -- BGE model dimension
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(file_id, chunk_index)
);

-- Indexes for performance
CREATE INDEX idx_chunks_file_id ON chunks(file_id);
CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);
```

### SQLite Schema

```sql
-- Files tracking table
CREATE TABLE files (
    id TEXT PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    file_hash TEXT UNIQUE NOT NULL,
    file_size INTEGER,
    indexed BOOLEAN DEFAULT 0,
    last_indexed_at TIMESTAMP
);

-- Metadata with tags and properties
CREATE TABLE file_metadata (
    file_id TEXT PRIMARY KEY,
    tags TEXT,  -- JSON array
    properties TEXT  -- JSON object
);

-- Change detection
CREATE TABLE file_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT NOT NULL,
    change_type TEXT,  -- 'created', 'modified', 'deleted'
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Neo4j Schema (Property Graph)

**Node Types**:
- `Document`: Source files
- `Chunk`: Text segments
- `Entity`: People, organizations, concepts
- `Person`, `Organization`, `Location` (specialized)

**Relationship Types**:
- `FROM_DOCUMENT`: Chunk → Document
- `MENTIONED_IN`: Entity → Chunk
- `RELATED_TO`: Entity → Entity
- `CO_OCCURS_WITH`: Entity → Entity (same chunk)

---

## API Reference

### PostgresStorage

```python
class PostgresStorage:
    async def store_chunk(
        file_id: str,
        chunk_index: int,
        text: str,
        embedding: List[float],
        metadata: Dict
    ) -> str:
        """Store text chunk with embedding. Returns chunk_id."""
    
    async def similarity_search(
        embedding: List[float],
        limit: int = 5,
        threshold: float = 0.0
    ) -> List[Dict]:
        """Find similar chunks by cosine distance."""
    
    async def get_file_chunks(file_id: str) -> List[Dict]:
        """Retrieve all chunks for a file."""
    
    async def delete_file_chunks(file_id: str) -> int:
        """Remove all chunks for a file."""
    
    async def get_chunk_by_id(chunk_id: str) -> Optional[Dict]:
        """Fetch single chunk by ID."""
```

### MetadataStore

```python
class MetadataStore:
    def add_file(
        file_id: str,
        path: str,
        mime_type: Optional[str],
        tags: Optional[List[str]]
    ) -> Dict:
        """Register file for tracking."""
    
    def has_file_changed(file_id: str, path: str) -> bool:
        """Check if file modified since last tracking."""
    
    def mark_indexed(file_id: str, postgres_chunk_ids: List[str]):
        """Mark file successfully indexed."""
    
    def get_pending_files() -> List[Dict]:
        """Get unindexed or changed files."""
    
    def get_file_stats() -> Dict:
        """Get tracking statistics."""
```

### Neo4jGraphStore

```python
class Neo4jGraphStore:
    def create_document_node(
        doc_id: str,
        file_path: str,
        doc_type: str,
        metadata: Dict
    ) -> Dict:
        """Create document node."""
    
    def create_entity_node(
        entity_id: str,
        name: str,
        entity_type: str,
        properties: Dict
    ) -> Dict:
        """Create entity (Person, Organization, etc.)."""
    
    def create_relationship(
        source_id: str,
        target_id: str,
        relationship_type: str,
        properties: Dict
    ) -> Dict:
        """Create relationship between entities."""
    
    def extract_entities_from_chunk(
        chunk_id: str,
        text: str,
        doc_id: str,
        entities: List[Tuple[str, str]]
    ) -> List[Dict]:
        """Extract and store entities from text."""
    
    def get_entity_neighbors(
        entity_id: str,
        relationship_type: Optional[str],
        depth: int
    ) -> List[Dict]:
        """Get related entities."""
    
    def find_paths(
        source_id: str,
        target_id: str,
        max_length: int
    ) -> List[List[Dict]]:
        """Find relationship paths between entities."""
    
    def get_concept_clusters(
        min_connections: int,
        limit: int
    ) -> List[Dict]:
        """Get clusters of related concepts."""
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `psycopg2.OperationalError: could not connect` | PostgreSQL not running: `brew services start postgresql@15` |
| `neo4j.exceptions.ServiceUnavailable` | Neo4j not running: `brew services start neo4j` or Docker container |
| `vector dimension mismatch` | Embedding model changed; embeddings must be 384-dim for BGE model |
| `FAISS index dimension mismatch` | Delete old FAISS index files; regenerate with matching embeddings |
| `Connection refused` | Check firewall, port bindings: `lsof -i :5432` (PostgreSQL), `lsof -i :7687` (Neo4j) |
| `sqlite3.OperationalError: database is locked` | File in use; close other connections or delete `.rag_metadata.db` |

---

## Performance Tuning

### PostgreSQL

```sql
-- Create better index for similarity search
CREATE INDEX idx_chunks_embedding_perf ON chunks 
    USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);  -- Increase lists for larger datasets

-- Analyze table for query planner
ANALYZE chunks;
```

### Neo4j

```cypher
-- Create indexes for faster lookups
CREATE INDEX FOR (d:Document) ON (d.id);
CREATE INDEX FOR (e:Entity) ON (e.name);

-- Monitor query performance
PROFILE MATCH (e:Entity)-[:MENTIONED_IN]->(c:Chunk) 
    WHERE e.type = "Person" RETURN COUNT(e);
```

### Connection Pooling

```python
# PostgreSQL pool configuration
pool = await init_postgres_pool(
    postgres_url,
    min_size=10,      # Minimum connections
    max_size=20,      # Maximum connections
    max_queries=50000 # Queries per connection
)
```

---

## Integration with Existing RAG Pipeline

### Modified main.py Pattern

```python
from src.storage import StorageOrchestrator

async def main():
    storage = StorageOrchestrator(...)
    
    # Load documents with Docling
    documents = process_directory("./rag-data/data")
    
    # Get embeddings
    embeddings = get_embeddings_model()
    
    # Store in PostgreSQL
    postgres = await storage.init_postgres()
    for doc in documents:
        embedding = embeddings.embed_query(doc.page_content)
        chunk_id = await postgres.store_chunk(
            file_id=doc.metadata["source"],
            chunk_index=0,
            text=doc.page_content,
            embedding=embedding,
            metadata=doc.metadata
        )
    
    # Track metadata
    metadata = storage.init_metadata()
    for doc in documents:
        metadata.mark_indexed(doc.metadata["source"], [chunk_id])
    
    # Build knowledge graph
    neo4j = storage.init_neo4j()
    # ... entity extraction ...
    
    await storage.close()
```

---

## Next Steps

1. ✅ **Storage Layer**: Complete (PostgreSQL, Neo4j, SQLite)
2. ⏳ **Ingestion Integration**: Connect to main.py
3. ⏳ **Agent Layer**: Implement Pydantic AI agent
4. ⏳ **FastAPI**: Build REST API with SSE streaming
5. ⏳ **CLI**: Add command-line interface

---

## References

- PostgreSQL + pgvector: https://github.com/pgvector/pgvector
- Neo4j Python driver: https://neo4j.com/docs/python-manual/current/
- FAISS + LangChain: https://python.langchain.com/docs/modules/data_connection/vectorstores/faiss
- Async patterns: https://docs.python.org/3/library/asyncio.html
