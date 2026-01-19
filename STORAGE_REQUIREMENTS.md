# Storage Layer Requirements

This file documents the database and storage layer dependencies for the RAG system.

## Main Database Packages (Already in requirements.txt)

### PostgreSQL + pgvector
```
asyncpg>=0.29.0           # Async PostgreSQL driver
psycopg2-binary>=2.9.9    # Sync PostgreSQL driver (fallback)
pgvector>=0.2.4           # Python client for pgvector extension
```

### Neo4j
```
neo4j>=5.14.0             # Neo4j Python driver (sync)
graphiti-core>=0.3.0      # Knowledge graph framework (future)
```

## Optional: Advanced Storage Patterns

If you need distributed or advanced features:

```bash
# Redis caching (optional)
pip install redis aioredis

# Database connection pooling utilities
pip install sqlalchemy

# DuckDB for advanced local analytics (optional)
pip install duckdb

# MongoDB for document storage (optional)
pip install pymongo motor

# ElasticSearch for full-text search (optional)
pip install elasticsearch
```

## Installation & Setup

### 1. Install Python Packages

```bash
# Core storage packages (already in requirements.txt)
pip install -r requirements.txt

# Optional packages
pip install redis sqlalchemy duckdb
```

### 2. Setup PostgreSQL

#### macOS
```bash
brew install postgresql@15
brew services start postgresql@15
createdb rag_db
psql rag_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

#### Docker
```bash
docker run --name rag-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=rag_db \
  -p 5432:5432 \
  -d pgvector/pgvector:pg15
```

#### Verify
```bash
psql -h localhost -U postgres -d rag_db -c "SELECT version();"
psql -h localhost -U postgres -d rag_db -c "SELECT * FROM pg_available_extensions WHERE name='vector';"
```

### 3. Setup Neo4j

#### Docker (Recommended)
```bash
docker run --name rag-neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -d neo4j:latest
```

#### Homebrew (macOS)
```bash
brew install neo4j
brew services start neo4j
```

#### Browser Access
- URL: http://localhost:7474
- Default credentials: neo4j / neo4j (or your custom password)

### 4. Verify Installations

```python
# Python verification script
import asyncio
from src.storage import StorageOrchestrator

async def verify():
    storage = StorageOrchestrator(
        postgres_url="postgresql://postgres:postgres@localhost:5432/rag_db",
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
    )
    
    health = await storage.health_check()
    print("Backend Health:")
    for backend, status in health.items():
        print(f"  {backend}: {status['status']}")
    
    await storage.close()

asyncio.run(verify())
```

## Dependency Tree

```
pydantic-ai (LLM agent framework)
├── LangChain integrations
│   └── Requires storage for vector retrieval
├── Requires embeddings model
│   └── sentence-transformers (uses HuggingFace)
└── Requires LLM backend
    └── ollama, openai, google-generativeai

Storage Layer
├── PostgreSQL + pgvector
│   ├── asyncpg (async driver)
│   ├── psycopg2 (sync driver)
│   └── pgvector (Python wrapper)
├── Neo4j
│   └── neo4j (Python driver)
└── SQLite
    └── Built-in sqlite3

Docling (Document processing)
├── docling
├── docling-core
├── docling-parse
└── Dependencies: torch, transformers
```

## Version Compatibility Matrix

| Component | Version | Python | Status |
|-----------|---------|--------|--------|
| PostgreSQL | 15+ | 3.8+ | ✅ Tested |
| pgvector | 0.2.4+ | 3.8+ | ✅ Tested |
| asyncpg | 0.29.0+ | 3.8+ | ✅ Tested |
| Neo4j | 5.14+ | 3.8+ | ✅ Tested |
| SQLite | 3.8+ | Built-in | ✅ Tested |
| LangChain | 0.3.1+ | 3.10+ | ✅ Tested |
| Docling | 2.0+ | 3.10+ | ✅ Tested |

## Performance Optimization

### PostgreSQL Tuning

```sql
-- Increase effective cache size (for 16GB machine)
ALTER SYSTEM SET effective_cache_size = '12GB';

-- Increase work memory
ALTER SYSTEM SET work_mem = '256MB';

-- Increase random page cost for SSD
ALTER SYSTEM SET random_page_cost = '1.1';

-- Reload config
SELECT pg_reload_conf();
```

### Connection Pooling

Default pool settings in `src/storage/postgres.py`:
```python
min_size=10      # Minimum connections
max_size=20      # Maximum connections  
max_queries=50000 # Queries per connection before new connection
```

Adjust for your workload:
```python
pool = await init_postgres_pool(
    db_url,
    min_size=5,      # Lower for dev
    max_size=50,     # Higher for production
    max_queries=50000
)
```

## Troubleshooting

### PostgreSQL Connection Issues

```bash
# Check if PostgreSQL is running
pg_isready -h localhost -U postgres

# Check PostgreSQL logs
tail -f /usr/local/var/log/postgres.log

# Verify pgvector extension
psql -d rag_db -c "SELECT * FROM pg_extension;"

# Rebuild connection
psql -d rag_db -c "SELECT version();"
```

### Neo4j Connection Issues

```bash
# Check if Neo4j is running
docker ps | grep rag-neo4j

# View Neo4j logs
docker logs rag-neo4j -f

# Check Neo4j status
curl -u neo4j:password http://localhost:7474/db/neo4j/info

# Restart Neo4j
docker restart rag-neo4j
```

### Python Import Issues

```bash
# Verify installations
python -c "import asyncpg; print(asyncpg.__version__)"
python -c "import pgvector; print(pgvector.__version__)"
python -c "import neo4j; print(neo4j.__version__)"

# Reinstall if needed
pip install --upgrade asyncpg pgvector neo4j
```

## Environment Variables (Optional)

Create `.env` file:

```bash
# PostgreSQL
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rag_db
DATABASE_POOL_MIN=10
DATABASE_POOL_MAX=20

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# SQLite
METADATA_DB_PATH=.rag_metadata.db

# Features
ENABLE_ASYNC_RETRIEVAL=true
ENABLE_GRAPH_TRAVERSAL=true
ENABLE_CHANGE_DETECTION=true
```

Load in Python:

```python
from dotenv import load_dotenv
import os

load_dotenv()

postgres_url = os.getenv("DATABASE_URL")
neo4j_uri = os.getenv("NEO4J_URI")
```

## Testing Storage Layer

```bash
# Run all tests
pytest tests/storage/test_storage_layer.py -v

# Run specific backend tests
pytest tests/storage/test_storage_layer.py::TestPostgresStorage -v
pytest tests/storage/test_storage_layer.py::TestMetadataStore -v
pytest tests/storage/test_storage_layer.py::TestNeo4jGraphStore -v

# Run with coverage
pytest tests/storage/test_storage_layer.py --cov=src.storage --cov-report=html

# Run integration test
pytest tests/storage/test_storage_layer.py::test_end_to_end_pipeline -v
```

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| `ImportError: No module named 'asyncpg'` | Package not installed | `pip install asyncpg` |
| `ImportError: No module named 'pgvector'` | Package not installed | `pip install pgvector` |
| `psycopg2.OperationalError: could not connect` | PostgreSQL not running | `brew services start postgresql@15` |
| `neo4j.exceptions.ServiceUnavailable` | Neo4j not running | Docker or `brew services start neo4j` |
| `vector dimension mismatch` | Wrong embedding size | Use 384-dim (BGE model) |
| `timeout expired` | Connection pool exhausted | Increase max_size in init_postgres_pool |
| `sqlite3 database is locked` | File in use | Close connections or delete DB |

## Next Steps

1. ✅ Install all requirements from `requirements.txt`
2. ✅ Setup PostgreSQL with pgvector extension
3. ✅ Setup Neo4j (Docker or Homebrew)
4. ✅ Run health check: `python -c "from src.storage import StorageOrchestrator; ..."`
5. ✅ Run tests: `pytest tests/storage/test_storage_layer.py -v`
6. ⏳ Integrate with main.py (Phase 3)

## References

- PostgreSQL: https://www.postgresql.org/
- pgvector: https://github.com/pgvector/pgvector
- Neo4j: https://neo4j.com/
- asyncpg: https://github.com/MagicStack/asyncpg
- LangChain: https://www.langchain.com/

---

*Storage Layer Requirements - Updated 2024*
