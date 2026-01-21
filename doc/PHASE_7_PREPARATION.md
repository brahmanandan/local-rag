# Phase 7: API Layer - Preparation Guide

**Status**: 🟡 **READY TO BEGIN**
**Prerequisite**: Phase 6 (Agent Layer) ✅ **COMPLETE**

---

## Overview

Phase 7 implements the FastAPI application layer that exposes the RAGAgent through REST endpoints with streaming support. This layer bridges user applications with the intelligent reasoning engine.

---

## Architecture

### API Layer Stack

```
┌────────────────────────────────────┐
│ Client Applications                │
│ (Web, CLI, Mobile)                 │
└────────────┬───────────────────────┘
             │
┌────────────▼───────────────────────┐
│ FastAPI Application (Phase 7)      │
├────────────────────────────────────┤
│ • Health checks                    │
│ • Query endpoints                  │
│ • SSE streaming                    │
│ • Context selection API            │
│ • Tool usage logging API           │
│ • Error handling                   │
└────────────┬───────────────────────┘
             │
┌────────────▼───────────────────────┐
│ RAGAgent (Phase 6)                 │
│ Reasoning + Tool Calling           │
└────────────┬───────────────────────┘
             │
┌────────────▼───────────────────────┐
│ Storage Layer (Phase 2-5)          │
│ PostgreSQL, Neo4j, SQLite          │
└────────────────────────────────────┘
```

### Endpoint Structure

```
/api/v1/
├── health/
│   └── GET /            (Health check)
├── query/
│   ├── POST /query      (Query with streaming)
│   ├── GET /{id}        (Get specific query result)
│   └── GET /logs        (Query logs)
├── context/
│   ├── POST /select     (Select context)
│   └── GET /{id}        (Get context)
├── tools/
│   ├── POST /vector-search
│   ├── POST /graph-search
│   ├── POST /hybrid-search
│   ├── POST /document/{id}
│   └── POST /entity-context/{id}
└── metrics/
    └── GET /usage       (Tool usage metrics)
```

---

## Phase 7 Requirements

### 1. FastAPI Application
- [ ] Create `src/api/app.py` with FastAPI instance
- [ ] Configure CORS, logging, middleware
- [ ] Set up error handling
- [ ] Add request/response models
- [ ] Implement health check endpoint

### 2. Query Endpoint
- [ ] POST `/api/v1/query` for sync queries
- [ ] GET `/api/v1/query/{id}` to retrieve results
- [ ] Implement request validation
- [ ] Add response formatting
- [ ] Include source attribution

### 3. Streaming Endpoint
- [ ] Implement SSE (Server-Sent Events) streaming
- [ ] Real-time tool usage logging
- [ ] Partial result streaming
- [ ] Error handling in streams
- [ ] Client reconnection support

### 4. Context Selection API
- [ ] POST `/api/v1/context/select` to choose context
- [ ] GET `/api/v1/context/{id}` to retrieve
- [ ] Context persistence
- [ ] Context history

### 5. Tool Usage Logging API
- [ ] GET `/api/v1/metrics/usage` for logs
- [ ] Filter by time range
- [ ] Aggregate statistics
- [ ] JSON export

### 6. Tool-Specific Endpoints
- [ ] Vector search endpoint
- [ ] Graph search endpoint
- [ ] Hybrid search endpoint
- [ ] Document retrieval endpoint
- [ ] Entity context endpoint

### 7. Error Handling
- [ ] Custom exception handlers
- [ ] HTTP status code mapping
- [ ] Detailed error messages
- [ ] Error logging

### 8. API Documentation
- [ ] OpenAPI/Swagger documentation
- [ ] Endpoint descriptions
- [ ] Request/response examples
- [ ] Error codes documentation

### 9. Testing
- [ ] Unit tests for endpoints
- [ ] Integration tests
- [ ] Streaming tests
- [ ] Error scenario tests

### 10. Configuration
- [ ] Environment-based config
- [ ] API key support (optional)
- [ ] Rate limiting (optional)
- [ ] CORS configuration

---

## Code Structure

### New Files to Create

#### 1. `src/api/app.py`
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.agent.agent import RAGAgent
from src.storage import StorageOrchestrator

app = FastAPI(
    title="RAG System API",
    description="Local-first RAG with agent reasoning",
    version="1.0.0"
)

# Setup routes
from src.api.routes import (
    health,
    query,
    context,
    tools,
    metrics
)

# Include routers
app.include_router(health.router)
app.include_router(query.router)
app.include_router(context.router)
app.include_router(tools.router)
app.include_router(metrics.router)
```

#### 2. `src/api/routes/health.py`
```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/health", tags=["health"])

@router.get("/")
async def health_check():
    """Check API health and dependencies."""
    return {"status": "healthy", "timestamp": datetime.now()}
```

#### 3. `src/api/routes/query.py`
```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from src.agent.agent import RAGAgent

router = APIRouter(prefix="/api/v1/query", tags=["query"])

@router.post("/")
async def query(request: QueryRequest):
    """Submit a query."""
    # Use RAGAgent.query()
    pass

@router.get("/{query_id}")
async def get_query(query_id: str):
    """Get previous query result."""
    pass

@router.get("/logs")
async def get_query_logs():
    """Get query logs."""
    pass
```

#### 4. `src/api/routes/streaming.py`
```python
from fastapi.responses import StreamingResponse

@router.post("/stream")
async def stream_query(request: QueryRequest):
    """Stream query results with SSE."""
    async def event_generator():
        async for chunk in agent.query_stream(request.query):
            yield f"data: {json.dumps(chunk)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

#### 5. `src/api/models.py`
```python
from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str
    context_id: Optional[str] = None
    limit: int = 5

class QueryResponse(BaseModel):
    query_id: str
    answer: str
    sources: List[str]
    tool_usage: List[Dict]
    duration_ms: float

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
```

#### 6. `src/api/middleware.py`
```python
from fastapi import Request
import logging

async def logging_middleware(request: Request, call_next):
    """Log all API requests."""
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    return response
```

#### 7. `src/api/exceptions.py`
```python
from fastapi import HTTPException

class QueryNotFoundError(HTTPException):
    """Query not found."""
    pass

class QueryProcessingError(HTTPException):
    """Query processing failed."""
    pass
```

### Test Files to Create

#### 1. `tests/api/test_app.py`
```python
# Test FastAPI application
# - Startup/shutdown
# - Route registration
# - Middleware
```

#### 2. `tests/api/test_endpoints.py`
```python
# Test individual endpoints
# - Health check
# - Query endpoint
# - Tool endpoints
# - Error scenarios
```

#### 3. `tests/api/test_streaming.py`
```python
# Test SSE streaming
# - Real-time events
# - Error handling
# - Client reconnection
```

#### 4. `tests/api/test_integration.py`
```python
# End-to-end API tests
# - Full query workflow
# - Multi-step interactions
# - Error recovery
```

---

## Request/Response Models

### Query Request
```json
{
  "query": "What are the main findings?",
  "context_id": "optional-context-id",
  "limit": 5,
  "tools": ["vector_search", "graph_search"],
  "streaming": false
}
```

### Query Response
```json
{
  "query_id": "q-12345",
  "answer": "The main findings are...",
  "sources": [
    {
      "document_id": "doc-123",
      "title": "Research Paper",
      "score": 0.95
    }
  ],
  "tool_usage": [
    {
      "tool_name": "vector_search",
      "duration_ms": 75.5,
      "success": true
    }
  ],
  "duration_ms": 150.0,
  "timestamp": "2026-01-20T10:30:00Z"
}
```

### Streaming Event
```json
{
  "type": "thinking",
  "content": "Let me search for relevant documents..."
}
```

or

```json
{
  "type": "tool_call",
  "tool": "vector_search",
  "duration_ms": 75.5
}
```

or

```json
{
  "type": "final_answer",
  "content": "Based on my search...",
  "sources": [...]
}
```

---

## Integration Points

### From Phase 6
- ✅ `RAGAgent` class - Main reasoning engine
- ✅ `RAGAgent.query()` - Query processing
- ✅ `RAGAgent.get_tool_usage_logs()` - Logging access
- ✅ Tool implementations - For direct access
- ✅ Data models - For response formatting

### To Phase 7
- 📝 StorageOrchestrator initialization
- 📝 Configuration management
- 📝 Logging/metrics collection
- 📝 Error handling strategy

---

## Development Steps

### Step 1: Project Setup
```bash
# Install dependencies
pip install fastapi uvicorn python-multipart sse-starlette

# Create API module structure
mkdir -p src/api/routes
touch src/api/__init__.py
touch src/api/routes/__init__.py
```

### Step 2: Core Application
```bash
# Create base app with middleware
# - FastAPI instance
# - CORS configuration
# - Error handling
# - Middleware setup
```

### Step 3: Health Endpoint
```bash
# Implement and test /api/v1/health
# - Database connectivity
# - LLM provider check
# - Dependencies status
```

### Step 4: Query Endpoint
```bash
# Implement POST /api/v1/query
# - Request validation
# - RAGAgent integration
# - Response formatting
# - Error handling
```

### Step 5: Streaming Endpoint
```bash
# Implement SSE streaming
# - Real-time tool usage
# - Partial results
# - Error recovery
```

### Step 6: Tool Endpoints
```bash
# Implement direct tool endpoints
# - Vector search
# - Graph search
# - Document retrieval
# - Entity context
```

### Step 7: Testing
```bash
# Write comprehensive tests
# - Unit tests
# - Integration tests
# - Streaming tests
# - Error scenarios
```

### Step 8: Documentation
```bash
# Generate API documentation
# - OpenAPI schema
# - Endpoint descriptions
# - Example requests/responses
```

---

## Configuration

### Environment Variables
```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_ENV=development|production

# Database
DATABASE_URL=postgresql://...
NEO4J_URI=bolt://localhost:7687

# LLM
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2:latest

# API Options
ENABLE_DOCS=true
ENABLE_STREAMING=true
CORS_ORIGINS=["http://localhost:3000"]
```

### Settings File
```python
# src/api/settings.py
from pydantic_settings import BaseSettings

class APISettings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    env: str = "development"
    docs_url: str = "/docs"
    
    class Config:
        env_file = ".env"
```

---

## Error Handling Strategy

### HTTP Status Codes
- 200: Success
- 400: Bad request (validation error)
- 404: Not found
- 500: Server error
- 503: Service unavailable

### Error Response Format
```json
{
  "error": "error_code",
  "message": "Human-readable message",
  "details": {
    "field": "validation_error_details"
  },
  "request_id": "req-12345"
}
```

### Exception Mapping
```python
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(status_code=400, content={...})

@app.exception_handler(QueryProcessingError)
async def query_exception_handler(request, exc):
    return JSONResponse(status_code=500, content={...})
```

---

## Testing Strategy

### Unit Tests
- Endpoint request validation
- Response formatting
- Error handling
- Middleware behavior

### Integration Tests
- Full query workflow
- RAGAgent integration
- Storage layer coordination
- Error scenarios

### Streaming Tests
- SSE event format
- Real-time delivery
- Connection handling
- Error recovery

### Performance Tests
- Response time
- Throughput
- Memory usage
- Concurrent requests

---

## Deployment Considerations

### Local Development
```bash
# Run with auto-reload
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

### Production
```bash
# Run with Gunicorn
gunicorn "src.api.app:app" \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Dependencies to Add

### pyproject.toml
```toml
[project]
dependencies = [
    # ... existing dependencies ...
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "python-multipart>=0.0.6",
    "sse-starlette>=2.1.0",
    "pydantic-settings>=2.1.0",
]

[project.optional-dependencies]
dev = [
    # ... existing dev dependencies ...
    "httpx>=0.25.0",  # For testing
]
```

---

## Phase 7 Checklist

### Planning
- [ ] Review Phase 6 completion
- [ ] Design endpoint structure
- [ ] Plan request/response models
- [ ] Design error handling strategy
- [ ] Plan testing approach

### Implementation
- [ ] Create `src/api/` module
- [ ] Implement FastAPI app
- [ ] Create middleware
- [ ] Implement health endpoint
- [ ] Implement query endpoint
- [ ] Implement streaming endpoint
- [ ] Implement tool endpoints
- [ ] Add error handling
- [ ] Add documentation

### Testing
- [ ] Unit tests for endpoints
- [ ] Integration tests
- [ ] Streaming tests
- [ ] Error scenario tests
- [ ] Performance tests

### Documentation
- [ ] API documentation
- [ ] Deployment guide
- [ ] Configuration guide
- [ ] Examples

### Verification
- [ ] All endpoints working
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Ready for Phase 8

---

## Success Criteria

### Functionality
✅ Health check endpoint working
✅ Query endpoint processing queries via RAGAgent
✅ Streaming endpoint providing real-time updates
✅ Tool endpoints accessible
✅ Error handling comprehensive
✅ All responses properly formatted

### Quality
✅ Unit tests (15+ tests)
✅ Integration tests (10+ tests)
✅ Streaming tests (5+ tests)
✅ Code coverage >80%
✅ All imports resolvable
✅ Type hints comprehensive

### Documentation
✅ API documentation (OpenAPI)
✅ Endpoint descriptions
✅ Request/response examples
✅ Error codes documented
✅ Configuration guide

### Performance
✅ Query response time <500ms (excluding LLM)
✅ Streaming events delivered in real-time
✅ Memory usage <200MB baseline
✅ Handles 10+ concurrent requests

---

## Next Steps After Phase 7

1. **Phase 8**: Mind Map & Export
   - Mermaid export
   - Graphviz export
   - Interactive visualization

2. **Phase 9**: Provider & Fallback
   - Multi-provider support
   - Fallback chains
   - Provider configuration

3. **Phase 10**: CLI Interface
   - Interactive CLI
   - Rich formatting
   - Command structure

4. **Phase 11**: Testing & Quality
   - Performance testing
   - E2E testing
   - Load testing

5. **Phase 12**: Documentation & Polish
   - Complete documentation
   - Deployment guides
   - User manual

---

## Resources

### FastAPI Documentation
- https://fastapi.tiangolo.com/
- https://fastapi.tiangolo.com/tutorial/
- https://fastapi.tiangolo.com/deployment/

### Streaming with SSE
- https://github.com/sysid/sse-starlette
- https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events

### Testing FastAPI
- https://fastapi.tiangolo.com/tutorial/testing/
- https://httpx.readthedocs.io/

---

## Ready to Begin

✅ Phase 6 (Agent Layer) is complete
✅ All integration points documented
✅ API architecture designed
✅ Development workflow planned
🟢 **Ready to start Phase 7**

---

**Document**: Phase 7 Preparation Guide
**Status**: Ready for Phase 7 Implementation
**Last Updated**: January 20, 2026
