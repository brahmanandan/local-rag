---
description: 
globs: 
alwaysApply: true
---

# Personal Knowledge Graph RAG + Mind-Map Agent Requirements


## Purpose
Local-first system to ingest personal files (documents, images, audio, video), build embeddings/knowledge graph/mind map, and enable context-driven reasoning with private models and deterministic external fallbacks.


## Scope
- Recursive filesystem discovery with metadata tracking and change detection.
- Docling-driven extraction and chunking into vector-ready text/markdown for supported formats.
- Embedding generation (local primary, external fallback) stored in vector DB with relational metadata.
- Concept extraction, clustering, and knowledge graph construction feeding an interactive mind map.
- User-driven context selection and reasoning with source-aware outputs.


## Non-Goals
- Cloud storage of raw personal data.
- Real-time collaborative editing.
- Full media rendering/annotation UI beyond mind map interactions.


## Architecture Pipeline
1) Filesystem traversal → metadata store (SQLite/DuckDB) with file hashes and change tracking.
2) Ingestion & extraction → docling text/OCR/captions/keyframes/audio transcripts with semantic chunking.
3) Embeddings → vector store (FAISS/Chroma/Qdrant or PostgreSQL + pgvector) keyed by chunk/file IDs.
4) Knowledge graph → entity/relationship extraction feeding Graphiti/Neo4j.
5) Mind map → graph export (Mermaid/Graphviz/JSON) for UI.
6) Context selection → assemble chunks, neighbors, and sources.
7) Reasoning → local LLM first, deterministic external fallback.


## Architecture & Components
- Agent layer: Pydantic AI agent with tools for vector_search, graph_search, hybrid_search, doc retrieval; system prompts govern tool choice.
- API layer: FastAPI with streaming (SSE) responses, health checks, and tool-usage visibility.
- Storage: PostgreSQL + pgvector for chunks/embeddings; Neo4j (via Graphiti) for temporal knowledge graph; optional SQLite/DuckDB for local metadata.
- Ingestion: chunker + embedder + graph builder; supports clean re-ingest and batch processing.
- CLI: interactive client exposing tool usage and streaming responses.


## Filesystem Traversal
- Python stack: os/pathlib for traversal; filetype for MIME detection; watchdog optional for live updates.
- Store per-file nodes: id (hash), path, type, created/modified, tags, content pointer.
- Support incremental updates; avoid remote calls during scan.


## Docling Processing & Chunking
- Docling handles conversion and vector data chunking before embeddings.
- Supported formats (keep in sync with DOCLING_FORMATS):
  - Documents: .pdf, .docx, .pptx, .xlsx, .html, .htm
  - Text: .txt, .md, .rst, .latex, .tex, .xml, .json, .asciidoc, .adoc
  - Images (OCR): .jpg, .jpeg, .png, .gif, .bmp, .tiff, .tif, .webp
  - Videos (frames/metadata): .mp4, .avi, .mov, .mkv, .flv, .wmv, .webm, .m4v
  - Audio (transcription): .mp3, .wav, .aac, .flac, .m4a, .ogg, .wma, .opus
- Export text/markdown for downstream embedding and graph construction.


## Embedding Strategy
- Local models (primary): nomic-embed-text (Ollama), bge-small/base, all-MiniLM-L6-v2.
- External fallback (when internet available): OpenAI text-embedding-3-large, Gemini embeddings, RouteLLM via ChatLLM Teams.
- Decision logic: prefer local → else external → else skip; log chosen model.
- Persist embeddings with metadata references to enable re-embedding on change.


## Agent Reasoning & Retrieval
- Hybrid retrieval combining pgvector semantic search and Graphiti/Neo4j traversal; agent chooses vector vs graph vs hybrid.
- Prompts inject citations and relationships; outputs source-aware summaries/analysis/comparisons/decisions.
- Context payload: context_id, chunks, sources, relationships; enforce tool usage logging.


## Provider Configuration
- LLM providers: OpenAI, Ollama, OpenRouter, Gemini (configurable via env).
- Embedding providers: OpenAI or local Ollama; model choice configurable per task (chat vs ingestion).
- API/APP configuration via env: DATABASE_URL, NEO4J_URI/USER/PASSWORD, LLM_PROVIDER/BASE_URL/API_KEY/CHOICE, EMBEDDING_MODEL, APP_ENV/LOG_LEVEL/PORT.


## Quality & Constraints
- Local-first execution; no raw data leaves device unless user opts into fallback models.
- Deterministic fallback order; configurable timeouts and offline mode.
- Idempotent re-runs on changed files; robust to partially processed items.
- Logs for pipeline stages; surface errors with actionable messages.


## Deliverables
- Configurable pipeline scripts/services for traversal, extraction, embedding, graphing, and reasoning.
- Mind map export artifacts and APIs for context selection and reasoning requests.
- Clear model selection and fallback configuration defaults.

## Code structure


.
├── main.py                    # Document indexing pipeline
│   └── load_docs_with_docling() → process_directory() → FAISS index
├── rag_cli.py                 # Streamlit web interface (load_chain() + query loop)
├── docling_utils.py           # Docling wrapper API (DoclingConverter, process_directory())
├── utils.py                   # Embedding/LLM provider fallback logic (get_embeddings_model, get_llm_model)
├── config.yaml                # Provider priority lists + model-specific configs
├── requirements.txt           # Docling, LangChain 0.3.1+, FAISS, sentence-transformers
└── rag-data/                  # Document storage
    ├── data/                  # Place documents here (all formats)
    └── index/                 # Generated FAISS index (index.faiss + index.pkl)


Ensure robust error handling and recovery mechanisms in all pipeline stages.
Ensure proper logging, error handling, and recovery mechanisms are implemented across all pipeline stages.
Ensure no document is updated during development, only README.md is updated and AGENT.md is modified ONLY if needed. Don't waste time in generating intermediate documents.
Refer to the code at test-code/agentic-rag-knowledge-graph/ and ensure the code best practices are followed in the code generated. Some examples
  1. Architecture, if there are good ones
  2. .env file format and configurations in test-code/agentic-rag-knowledge-graph/ looks good
  3. Ensure all pipeline stages have unit tests and integration tests to validate functionality and robustness.
  4. Code snippets