"""Pydantic AI agent with ReAct reasoning and tool calling."""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class SearchResult(BaseModel):
    """Result from a search operation."""
    id: str
    score: float
    text: str
    source: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    """Record of a tool call for logging."""
    tool_name: str
    timestamp: datetime
    arguments: Dict[str, Any]
    result: Optional[Any] = None
    duration_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None


class ToolUsageLog(BaseModel):
    """Log of tool usage for a query."""
    query: str
    timestamp: datetime
    tool_calls: List[ToolCall] = Field(default_factory=list)
    total_duration_ms: float = 0.0
    final_answer: Optional[str] = None


class AgentState(BaseModel):
    """State maintained by the agent during reasoning."""
    query: str
    context_sources: List[SearchResult] = Field(default_factory=list)
    reasoning_steps: List[str] = Field(default_factory=list)
    tool_usage: List[ToolCall] = Field(default_factory=list)
    final_answer: Optional[str] = None


# ============================================================================
# Tool Response Models
# ============================================================================

class VectorSearchResponse(BaseModel):
    """Response from vector search tool."""
    query: str
    results: List[SearchResult]
    count: int
    method: str = "vector_similarity"


class GraphSearchResponse(BaseModel):
    """Response from graph search tool."""
    query: str
    entities: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    entity_count: int
    relationship_count: int


class HybridSearchResponse(BaseModel):
    """Response from hybrid search tool."""
    query: str
    vector_results: List[SearchResult]
    graph_results: List[Dict[str, Any]]
    merged_results: List[SearchResult]
    total_count: int


class DocumentRetrievalResponse(BaseModel):
    """Response from document retrieval tool."""
    document_id: str
    title: Optional[str] = None
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    chunks: int = 0


# ============================================================================
# Tool Implementations
# ============================================================================

class RAGTools:
    """Collection of tools for RAG operations."""

    def __init__(self, storage_orchestrator):
        """Initialize tools with storage backend.
        
        Args:
            storage_orchestrator: StorageOrchestrator instance
        """
        self.storage = storage_orchestrator
        logger.info("RAGTools initialized with storage backend")

    async def vector_search(
        self,
        query: str,
        limit: int = 5,
        threshold: float = 0.0,
    ) -> VectorSearchResponse:
        """Search for documents using vector similarity.
        
        Args:
            query: Search query text
            limit: Maximum results to return
            threshold: Minimum similarity score
            
        Returns:
            VectorSearchResponse with matching chunks
        """
        logger.debug(f"Vector search: query={query}, limit={limit}")
        
        try:
            # Compute query embedding
            from sentence_transformers import SentenceTransformer
            embedder = SentenceTransformer("BAAI/bge-small-en-v1.5")
            query_embedding = embedder.encode(query).tolist()
            
            # Search in PostgreSQL
            results = await self.storage.postgres.similarity_search(
                query_embedding,
                limit=limit,
                threshold=threshold
            )
            
            # Convert to SearchResult objects
            search_results = [
                SearchResult(
                    id=r["id"],
                    score=float(r.get("similarity", 0.0)),
                    text=r["text"],
                    source=r.get("metadata", {}).get("file_path"),
                    metadata=r.get("metadata", {})
                )
                for r in results
            ]
            
            logger.info(f"Vector search returned {len(search_results)} results")
            return VectorSearchResponse(
                query=query,
                results=search_results,
                count=len(search_results)
            )
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise

    async def graph_search(
        self,
        query: str,
        entity_types: Optional[List[str]] = None,
        relationship_types: Optional[List[str]] = None,
    ) -> GraphSearchResponse:
        """Search knowledge graph for entities and relationships.
        
        Args:
            query: Search query
            entity_types: Filter by entity types
            relationship_types: Filter by relationship types
            
        Returns:
            GraphSearchResponse with entities and relationships
        """
        logger.debug(f"Graph search: query={query}, entity_types={entity_types}")
        
        try:
            # Query graph for matching entities
            entities = await self.storage.neo4j.search_entities(
                query,
                entity_types=entity_types
            )
            
            # Query for relationships
            relationships = await self.storage.neo4j.search_relationships(
                query,
                relationship_types=relationship_types
            )
            
            logger.info(
                f"Graph search returned {len(entities)} entities "
                f"and {len(relationships)} relationships"
            )
            
            return GraphSearchResponse(
                query=query,
                entities=entities,
                relationships=relationships,
                entity_count=len(entities),
                relationship_count=len(relationships)
            )
        except Exception as e:
            logger.error(f"Graph search failed: {e}")
            raise

    async def hybrid_search(
        self,
        query: str,
        vector_weight: float = 0.6,
        graph_weight: float = 0.4,
        limit: int = 5,
    ) -> HybridSearchResponse:
        """Hybrid search combining vector and graph search.
        
        Args:
            query: Search query
            vector_weight: Weight for vector results (0-1)
            graph_weight: Weight for graph results (0-1)
            limit: Maximum results to return
            
        Returns:
            HybridSearchResponse with merged results
        """
        logger.debug(f"Hybrid search: query={query}, weights=({vector_weight}, {graph_weight})")
        
        try:
            # Run both searches in parallel
            vector_results = await self.vector_search(query, limit=limit)
            graph_results = await self.graph_search(query)
            
            # Merge and score results
            merged_results = []
            seen_ids = set()
            
            # Add vector results
            for result in vector_results.results:
                if result.id not in seen_ids:
                    result.score = result.score * vector_weight
                    merged_results.append(result)
                    seen_ids.add(result.id)
            
            # Add graph results (converted to SearchResult)
            for entity in graph_results.entities:
                entity_id = entity.get("id")
                if entity_id not in seen_ids:
                    merged_results.append(
                        SearchResult(
                            id=entity_id,
                            score=entity.get("score", 0.0) * graph_weight,
                            text=entity.get("name", ""),
                            metadata={"entity_type": entity.get("type")}
                        )
                    )
                    seen_ids.add(entity_id)
            
            # Sort by score and limit
            merged_results = sorted(
                merged_results,
                key=lambda x: x.score,
                reverse=True
            )[:limit]
            
            logger.info(f"Hybrid search returned {len(merged_results)} merged results")
            
            return HybridSearchResponse(
                query=query,
                vector_results=vector_results.results,
                graph_results=graph_results.entities,
                merged_results=merged_results,
                total_count=len(merged_results)
            )
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            raise

    async def retrieve_document(
        self,
        document_id: str,
    ) -> DocumentRetrievalResponse:
        """Retrieve a complete document by ID.
        
        Args:
            document_id: Document file ID
            
        Returns:
            DocumentRetrievalResponse with document content
        """
        logger.debug(f"Retrieving document: {document_id}")
        
        try:
            # Get document info from metadata
            doc_info = await self.storage.metadata.get_file_info(document_id)
            
            # Get all chunks for document
            chunks = await self.storage.postgres.get_file_chunks(document_id)
            
            # Reconstruct document from chunks
            content = "\n\n".join([chunk["text"] for chunk in chunks])
            
            logger.info(f"Retrieved document {document_id} with {len(chunks)} chunks")
            
            return DocumentRetrievalResponse(
                document_id=document_id,
                title=doc_info.get("path") if doc_info else None,
                content=content,
                metadata=doc_info or {},
                chunks=len(chunks)
            )
        except Exception as e:
            logger.error(f"Document retrieval failed: {e}")
            raise

    async def get_entity_context(
        self,
        entity_id: str,
        depth: int = 2,
    ) -> Dict[str, Any]:
        """Get context around an entity in the knowledge graph.
        
        Args:
            entity_id: Entity node ID
            depth: Relationship traversal depth
            
        Returns:
            Dictionary with entity context and relationships
        """
        logger.debug(f"Getting entity context: {entity_id}, depth={depth}")
        
        try:
            context = await self.storage.neo4j.get_entity_context(
                entity_id,
                depth=depth
            )
            
            logger.info(f"Retrieved context for entity {entity_id}")
            return context
        except Exception as e:
            logger.error(f"Entity context retrieval failed: {e}")
            raise


# ============================================================================
# Pydantic AI Agent
# ============================================================================

class RAGAgent:
    """Pydantic AI agent for RAG operations with ReAct reasoning."""

    def __init__(
        self,
        storage_orchestrator,
        llm_provider: str = "ollama",
        llm_model: str = "llama3.2:latest",
        system_prompt: Optional[str] = None,
    ):
        """Initialize RAG agent.
        
        Args:
            storage_orchestrator: StorageOrchestrator instance
            llm_provider: LLM provider (ollama, openai, gemini)
            llm_model: Model name
            system_prompt: Custom system prompt
        """
        self.storage = storage_orchestrator
        self.tools = RAGTools(storage_orchestrator)
        self.tool_usage_logs: List[ToolUsageLog] = []
        
        # Initialize Pydantic AI agent
        self.agent = Agent(
            model=f"{llm_provider}:{llm_model}",
            system_prompt=system_prompt or self._default_system_prompt(),
        )
        
        # Register tools
        self._register_tools()
        
        logger.info(f"RAGAgent initialized with model {llm_model}")

    def _default_system_prompt(self) -> str:
        """Get default system prompt for RAG agent."""
        return """You are a helpful AI assistant with access to a knowledge graph and document database.

Your capabilities:
1. Vector Search: Search documents using semantic similarity (vector_search)
2. Graph Search: Query the knowledge graph for entities and relationships (graph_search)
3. Hybrid Search: Combine vector and graph searches for comprehensive results (hybrid_search)
4. Document Retrieval: Get full documents by ID (retrieve_document)
5. Entity Context: Get relationships around specific entities (get_entity_context)

Instructions:
- Always start by understanding the user's question
- Choose the appropriate search method based on the query type
- For factual questions, use graph_search to find relevant entities
- For semantic similarity, use vector_search
- For comprehensive searches, use hybrid_search
- Cite your sources in the answer
- If you don't find relevant information, say so
- Use entity_context to understand relationships between concepts

Remember to think step by step and use tools appropriately."""

    def _register_tools(self):
        """Register tools with the agent."""
        
        @self.agent.tool
        async def vector_search(
            ctx: RunContext,
            query: str,
            limit: int = 5,
        ) -> str:
            """Search documents by semantic similarity.
            
            Args:
                query: Search query
                limit: Max results
            
            Returns:
                Search results as formatted string
            """
            logger.info(f"Tool called: vector_search, query={query}")
            
            tool_call = ToolCall(
                tool_name="vector_search",
                timestamp=datetime.now(),
                arguments={"query": query, "limit": limit}
            )
            
            try:
                results = await self.tools.vector_search(query, limit=limit)
                
                # Format results
                formatted = self._format_search_results(results.results)
                
                tool_call.result = formatted
                tool_call.success = True
            except Exception as e:
                tool_call.error = str(e)
                tool_call.success = False
                formatted = f"Error: {e}"
            
            self._record_tool_call(tool_call)
            return formatted

        @self.agent.tool
        async def graph_search(
            ctx: RunContext,
            query: str,
            entity_types: Optional[List[str]] = None,
        ) -> str:
            """Search knowledge graph for entities and relationships.
            
            Args:
                query: Search query
                entity_types: Filter by entity types
            
            Returns:
                Entities and relationships as formatted string
            """
            logger.info(f"Tool called: graph_search, query={query}")
            
            tool_call = ToolCall(
                tool_name="graph_search",
                timestamp=datetime.now(),
                arguments={"query": query, "entity_types": entity_types}
            )
            
            try:
                results = await self.tools.graph_search(query, entity_types=entity_types)
                
                # Format results
                formatted = self._format_graph_results(results)
                
                tool_call.result = formatted
                tool_call.success = True
            except Exception as e:
                tool_call.error = str(e)
                tool_call.success = False
                formatted = f"Error: {e}"
            
            self._record_tool_call(tool_call)
            return formatted

        @self.agent.tool
        async def hybrid_search(
            ctx: RunContext,
            query: str,
            limit: int = 5,
        ) -> str:
            """Hybrid search combining vector and graph results.
            
            Args:
                query: Search query
                limit: Max results
            
            Returns:
                Merged results as formatted string
            """
            logger.info(f"Tool called: hybrid_search, query={query}")
            
            tool_call = ToolCall(
                tool_name="hybrid_search",
                timestamp=datetime.now(),
                arguments={"query": query, "limit": limit}
            )
            
            try:
                results = await self.tools.hybrid_search(query, limit=limit)
                
                # Format results
                formatted = self._format_search_results(results.merged_results)
                
                tool_call.result = formatted
                tool_call.success = True
            except Exception as e:
                tool_call.error = str(e)
                tool_call.success = False
                formatted = f"Error: {e}"
            
            self._record_tool_call(tool_call)
            return formatted

        @self.agent.tool
        async def retrieve_document(
            ctx: RunContext,
            document_id: str,
        ) -> str:
            """Retrieve complete document by ID.
            
            Args:
                document_id: Document ID
            
            Returns:
                Document content as formatted string
            """
            logger.info(f"Tool called: retrieve_document, document_id={document_id}")
            
            tool_call = ToolCall(
                tool_name="retrieve_document",
                timestamp=datetime.now(),
                arguments={"document_id": document_id}
            )
            
            try:
                doc = await self.tools.retrieve_document(document_id)
                
                # Format document
                formatted = f"Document: {doc.title}\n\n{doc.content}"
                
                tool_call.result = formatted
                tool_call.success = True
            except Exception as e:
                tool_call.error = str(e)
                tool_call.success = False
                formatted = f"Error: {e}"
            
            self._record_tool_call(tool_call)
            return formatted

        @self.agent.tool
        async def get_entity_context(
            ctx: RunContext,
            entity_id: str,
            depth: int = 2,
        ) -> str:
            """Get context around an entity.
            
            Args:
                entity_id: Entity node ID
                depth: Traversal depth
            
            Returns:
                Entity context as formatted string
            """
            logger.info(f"Tool called: get_entity_context, entity_id={entity_id}")
            
            tool_call = ToolCall(
                tool_name="get_entity_context",
                timestamp=datetime.now(),
                arguments={"entity_id": entity_id, "depth": depth}
            )
            
            try:
                context = await self.tools.get_entity_context(entity_id, depth=depth)
                
                # Format context
                formatted = self._format_entity_context(context)
                
                tool_call.result = formatted
                tool_call.success = True
            except Exception as e:
                tool_call.error = str(e)
                tool_call.success = False
                formatted = f"Error: {e}"
            
            self._record_tool_call(tool_call)
            return formatted

    async def query(self, query: str) -> Dict[str, Any]:
        """Query the agent with ReAct reasoning.
        
        Args:
            query: User query
            
        Returns:
            Dictionary with answer and metadata
        """
        logger.info(f"Agent query: {query}")
        
        start_time = datetime.now()
        log = ToolUsageLog(query=query, timestamp=start_time)
        
        try:
            # Run agent reasoning
            response = await self.agent.run(query)
            
            log.final_answer = response.data
            log.tool_calls = list(self._current_tool_calls)
            
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            log.total_duration_ms = duration_ms
            
            logger.info(f"Query completed in {duration_ms:.1f}ms with {len(log.tool_calls)} tool calls")
            
            self.tool_usage_logs.append(log)
            self._current_tool_calls = []
            
            return {
                "answer": response.data,
                "sources": self._extract_sources(log),
                "tool_usage": log,
                "duration_ms": duration_ms
            }
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise

    def _record_tool_call(self, tool_call: ToolCall):
        """Record a tool call for logging."""
        if not hasattr(self, "_current_tool_calls"):
            self._current_tool_calls = []
        self._current_tool_calls.append(tool_call)

    def _format_search_results(self, results: List[SearchResult]) -> str:
        """Format search results for display."""
        if not results:
            return "No results found."
        
        formatted = "Search Results:\n"
        for i, result in enumerate(results, 1):
            formatted += f"\n{i}. (Score: {result.score:.2f})\n{result.text}"
            if result.source:
                formatted += f"\nSource: {result.source}"
        return formatted

    def _format_graph_results(self, results: GraphSearchResponse) -> str:
        """Format graph search results."""
        formatted = "Graph Search Results:\n"
        
        if results.entities:
            formatted += f"\nEntities ({results.entity_count}):\n"
            for entity in results.entities:
                formatted += f"- {entity.get('name')} ({entity.get('type')})\n"
        
        if results.relationships:
            formatted += f"\nRelationships ({results.relationship_count}):\n"
            for rel in results.relationships:
                formatted += f"- {rel.get('source')} -> {rel.get('type')} -> {rel.get('target')}\n"
        
        return formatted or "No entities or relationships found."

    def _format_entity_context(self, context: Dict[str, Any]) -> str:
        """Format entity context for display."""
        formatted = f"Entity: {context.get('name')}\n"
        formatted += f"Type: {context.get('type')}\n"
        
        if "relationships" in context:
            formatted += f"\nRelationships:\n"
            for rel in context["relationships"]:
                formatted += f"- {rel.get('type')} -> {rel.get('target')}\n"
        
        return formatted

    def _extract_sources(self, log: ToolUsageLog) -> List[str]:
        """Extract unique sources from tool usage log."""
        sources = set()
        for tool_call in log.tool_calls:
            if isinstance(tool_call.result, str) and "Source:" in tool_call.result:
                # Parse source from formatted result
                pass
        return list(sources)

    def get_tool_usage_logs(self) -> List[ToolUsageLog]:
        """Get all tool usage logs."""
        return self.tool_usage_logs

    def export_tool_usage(self, filepath: str):
        """Export tool usage logs to JSON file.
        
        Args:
            filepath: Path to export to
        """
        data = [log.model_dump() for log in self.tool_usage_logs]
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Exported {len(self.tool_usage_logs)} tool usage logs to {filepath}")
