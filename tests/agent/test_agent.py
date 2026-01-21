"""Unit tests for Pydantic AI agent."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.agent.agent import (
    RAGAgent,
    RAGTools,
    SearchResult,
    ToolCall,
    ToolUsageLog,
    VectorSearchResponse,
    GraphSearchResponse,
    HybridSearchResponse,
    DocumentRetrievalResponse,
)


@pytest.fixture
def mock_storage():
    """Create mock storage orchestrator."""
    storage = MagicMock()
    storage.postgres = AsyncMock()
    storage.neo4j = AsyncMock()
    storage.metadata = AsyncMock()
    return storage


@pytest.fixture
def rag_tools(mock_storage):
    """Create RAGTools instance with mock storage."""
    return RAGTools(mock_storage)


@pytest.fixture
def rag_agent(mock_storage):
    """Create RAGAgent instance with mock storage."""
    return RAGAgent(
        mock_storage,
        llm_provider="ollama",
        llm_model="llama3.2:latest"
    )


# ============================================================================
# Data Model Tests
# ============================================================================

class TestDataModels:
    """Test data models."""

    def test_search_result_creation(self):
        """Test SearchResult creation."""
        result = SearchResult(
            id="test-1",
            score=0.95,
            text="Test document",
            source="test.pdf",
            metadata={"type": "chunk"}
        )
        assert result.id == "test-1"
        assert result.score == 0.95
        assert result.text == "Test document"
        assert result.source == "test.pdf"

    def test_tool_call_creation(self):
        """Test ToolCall creation."""
        now = datetime.now()
        call = ToolCall(
            tool_name="vector_search",
            timestamp=now,
            arguments={"query": "test"},
            result="results",
            success=True
        )
        assert call.tool_name == "vector_search"
        assert call.arguments["query"] == "test"
        assert call.success is True

    def test_tool_usage_log_creation(self):
        """Test ToolUsageLog creation."""
        log = ToolUsageLog(
            query="test query",
            timestamp=datetime.now(),
            tool_calls=[],
            total_duration_ms=100.0,
            final_answer="test answer"
        )
        assert log.query == "test query"
        assert log.total_duration_ms == 100.0
        assert log.final_answer == "test answer"

    def test_vector_search_response_creation(self):
        """Test VectorSearchResponse creation."""
        results = [
            SearchResult(id="1", score=0.9, text="doc1"),
            SearchResult(id="2", score=0.8, text="doc2"),
        ]
        response = VectorSearchResponse(
            query="test",
            results=results,
            count=2
        )
        assert response.count == 2
        assert len(response.results) == 2


# ============================================================================
# RAGTools Tests
# ============================================================================

class TestRAGTools:
    """Test RAGTools functionality."""

    @pytest.mark.asyncio
    async def test_vector_search_success(self, rag_tools, mock_storage):
        """Test successful vector search."""
        # Mock the storage response
        mock_storage.postgres.similarity_search.return_value = [
            {
                "id": "chunk-1",
                "text": "Test content",
                "similarity": 0.95,
                "metadata": {"file_path": "test.pdf"}
            }
        ]
        
        # Mock embedder
        with patch('src.agent.agent.SentenceTransformer') as mock_embed:
            mock_embed.return_value.encode.return_value = [0.1, 0.2, 0.3]
            
            result = await rag_tools.vector_search("test query", limit=5)
        
        assert result.query == "test query"
        assert len(result.results) == 1
        assert result.results[0].id == "chunk-1"
        assert result.count == 1

    @pytest.mark.asyncio
    async def test_vector_search_empty_results(self, rag_tools, mock_storage):
        """Test vector search with no results."""
        mock_storage.postgres.similarity_search.return_value = []
        
        with patch('src.agent.agent.SentenceTransformer'):
            result = await rag_tools.vector_search("no results query")
        
        assert result.count == 0
        assert len(result.results) == 0

    @pytest.mark.asyncio
    async def test_vector_search_error_handling(self, rag_tools, mock_storage):
        """Test vector search error handling."""
        mock_storage.postgres.similarity_search.side_effect = Exception("DB error")
        
        with patch('src.agent.agent.SentenceTransformer'):
            with pytest.raises(Exception):
                await rag_tools.vector_search("test query")

    @pytest.mark.asyncio
    async def test_graph_search_success(self, rag_tools, mock_storage):
        """Test successful graph search."""
        mock_storage.neo4j.search_entities.return_value = [
            {"id": "ent-1", "name": "Test Entity", "type": "PERSON"}
        ]
        mock_storage.neo4j.search_relationships.return_value = [
            {
                "id": "rel-1",
                "source": "ent-1",
                "target": "ent-2",
                "type": "KNOWS"
            }
        ]
        
        result = await rag_tools.graph_search("test query")
        
        assert result.entity_count == 1
        assert result.relationship_count == 1

    @pytest.mark.asyncio
    async def test_hybrid_search_merges_results(self, rag_tools, mock_storage):
        """Test hybrid search merges vector and graph results."""
        mock_storage.postgres.similarity_search.return_value = [
            {
                "id": "chunk-1",
                "text": "Vector result",
                "similarity": 0.9,
                "metadata": {}
            }
        ]
        mock_storage.neo4j.search_entities.return_value = [
            {"id": "ent-1", "name": "Graph Entity", "type": "PERSON", "score": 0.8}
        ]
        mock_storage.neo4j.search_relationships.return_value = []
        
        with patch('src.agent.agent.SentenceTransformer'):
            result = await rag_tools.hybrid_search("test query", limit=5)
        
        assert result.total_count > 0
        assert len(result.merged_results) > 0

    @pytest.mark.asyncio
    async def test_retrieve_document_success(self, rag_tools, mock_storage):
        """Test successful document retrieval."""
        mock_storage.metadata.get_file_info.return_value = {
            "path": "test.pdf",
            "size": 1000
        }
        mock_storage.postgres.get_file_chunks.return_value = [
            {"text": "Chunk 1"},
            {"text": "Chunk 2"}
        ]
        
        result = await rag_tools.retrieve_document("doc-1")
        
        assert result.document_id == "doc-1"
        assert result.chunks == 2
        assert "Chunk 1" in result.content
        assert "Chunk 2" in result.content

    @pytest.mark.asyncio
    async def test_get_entity_context_success(self, rag_tools, mock_storage):
        """Test successful entity context retrieval."""
        mock_storage.neo4j.get_entity_context.return_value = {
            "id": "ent-1",
            "name": "Test Entity",
            "type": "PERSON",
            "relationships": [
                {"type": "KNOWS", "target": "ent-2"}
            ]
        }
        
        result = await rag_tools.get_entity_context("ent-1", depth=2)
        
        assert result["id"] == "ent-1"
        assert result["name"] == "Test Entity"


# ============================================================================
# RAGAgent Tests
# ============================================================================

class TestRAGAgent:
    """Test RAGAgent functionality."""

    def test_agent_initialization(self, rag_agent, mock_storage):
        """Test agent initialization."""
        assert rag_agent.storage == mock_storage
        assert rag_agent.agent is not None
        assert len(rag_agent.tool_usage_logs) == 0

    def test_default_system_prompt(self, rag_agent):
        """Test default system prompt generation."""
        prompt = rag_agent._default_system_prompt()
        assert "vector search" in prompt.lower()
        assert "graph search" in prompt.lower()
        assert "hybrid search" in prompt.lower()
        assert "knowledge graph" in prompt.lower()

    def test_format_search_results_with_results(self, rag_agent):
        """Test formatting search results."""
        results = [
            SearchResult(id="1", score=0.95, text="Result 1", source="doc1.pdf"),
            SearchResult(id="2", score=0.85, text="Result 2", source="doc2.pdf"),
        ]
        
        formatted = rag_agent._format_search_results(results)
        
        assert "Search Results" in formatted
        assert "Result 1" in formatted
        assert "Result 2" in formatted
        assert "0.95" in formatted
        assert "0.85" in formatted
        assert "doc1.pdf" in formatted

    def test_format_search_results_no_results(self, rag_agent):
        """Test formatting empty search results."""
        formatted = rag_agent._format_search_results([])
        assert "No results found" in formatted

    def test_format_graph_results(self, rag_agent):
        """Test formatting graph results."""
        response = GraphSearchResponse(
            query="test",
            entities=[
                {"name": "Entity 1", "type": "PERSON"},
                {"name": "Entity 2", "type": "ORGANIZATION"}
            ],
            relationships=[
                {"source": "Entity 1", "type": "KNOWS", "target": "Entity 2"}
            ],
            entity_count=2,
            relationship_count=1
        )
        
        formatted = rag_agent._format_graph_results(response)
        
        assert "Graph Search Results" in formatted
        assert "Entities (2)" in formatted
        assert "Entity 1" in formatted
        assert "PERSON" in formatted

    def test_format_entity_context(self, rag_agent):
        """Test formatting entity context."""
        context = {
            "name": "Test Entity",
            "type": "PERSON",
            "relationships": [
                {"type": "KNOWS", "target": "Other Entity"}
            ]
        }
        
        formatted = rag_agent._format_entity_context(context)
        
        assert "Test Entity" in formatted
        assert "PERSON" in formatted
        assert "KNOWS" in formatted

    def test_tool_call_recording(self, rag_agent):
        """Test tool call recording."""
        tool_call = ToolCall(
            tool_name="test_tool",
            timestamp=datetime.now(),
            arguments={"test": "arg"},
            result="test result"
        )
        
        rag_agent._record_tool_call(tool_call)
        
        assert len(rag_agent._current_tool_calls) == 1
        assert rag_agent._current_tool_calls[0].tool_name == "test_tool"

    def test_get_tool_usage_logs(self, rag_agent):
        """Test getting tool usage logs."""
        log1 = ToolUsageLog(
            query="test 1",
            timestamp=datetime.now(),
            tool_calls=[],
            total_duration_ms=100.0
        )
        log2 = ToolUsageLog(
            query="test 2",
            timestamp=datetime.now(),
            tool_calls=[],
            total_duration_ms=200.0
        )
        
        rag_agent.tool_usage_logs.append(log1)
        rag_agent.tool_usage_logs.append(log2)
        
        logs = rag_agent.get_tool_usage_logs()
        assert len(logs) == 2

    @patch("builtins.open", create=True)
    def test_export_tool_usage(self, mock_open, rag_agent):
        """Test exporting tool usage logs."""
        log = ToolUsageLog(
            query="test query",
            timestamp=datetime.now(),
            tool_calls=[],
            final_answer="test answer"
        )
        rag_agent.tool_usage_logs.append(log)
        
        rag_agent.export_tool_usage("test_export.json")
        
        # Verify file was opened
        mock_open.assert_called_once_with("test_export.json", "w")

    def test_tool_registration(self, rag_agent):
        """Test that tools are registered with agent."""
        # Check that agent has tool decorators set up
        assert rag_agent.agent is not None
        # Note: Full tool testing requires running the agent


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for agent and tools."""

    @pytest.mark.asyncio
    async def test_full_query_workflow(self, rag_agent, mock_storage):
        """Test complete query workflow."""
        # This would require mocking the full pydantic_ai execution
        # For now, we test the components individually
        
        # Setup mocks
        mock_storage.postgres.similarity_search.return_value = [
            {"id": "1", "text": "Test", "similarity": 0.9, "metadata": {}}
        ]
        
        with patch('src.agent.agent.SentenceTransformer'):
            result = await rag_agent.tools.vector_search("test")
        
        assert result.count >= 0

    @pytest.mark.asyncio
    async def test_multi_tool_usage(self, rag_agent, mock_storage):
        """Test using multiple tools in sequence."""
        mock_storage.postgres.similarity_search.return_value = []
        mock_storage.neo4j.search_entities.return_value = []
        mock_storage.neo4j.search_relationships.return_value = []
        
        with patch('src.agent.agent.SentenceTransformer'):
            # Call multiple tools
            vs_result = await rag_agent.tools.vector_search("test")
            gs_result = await rag_agent.tools.graph_search("test")
        
        assert vs_result is not None
        assert gs_result is not None
