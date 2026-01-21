"""Integration tests for agent layer with full workflow."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.agent.agent import RAGAgent, RAGTools, ToolUsageLog


@pytest.fixture
def mock_storage_full():
    """Create fully mocked storage with all backends."""
    storage = MagicMock()
    
    # PostgreSQL mock
    storage.postgres = AsyncMock()
    storage.postgres.similarity_search = AsyncMock(return_value=[
        {
            "id": "chunk-1",
            "text": "PostgreSQL search result",
            "similarity": 0.95,
            "metadata": {"file_path": "test.pdf", "chunk_index": 0}
        }
    ])
    storage.postgres.get_file_chunks = AsyncMock(return_value=[
        {"text": "Chunk 1"},
        {"text": "Chunk 2"}
    ])
    
    # Neo4j mock
    storage.neo4j = AsyncMock()
    storage.neo4j.search_entities = AsyncMock(return_value=[
        {"id": "ent-1", "name": "John Doe", "type": "PERSON", "score": 0.9},
        {"id": "ent-2", "name": "Acme Corp", "type": "ORGANIZATION", "score": 0.85}
    ])
    storage.neo4j.search_relationships = AsyncMock(return_value=[
        {
            "id": "rel-1",
            "source": "ent-1",
            "target": "ent-2",
            "type": "WORKS_FOR",
            "score": 0.88
        }
    ])
    storage.neo4j.get_entity_context = AsyncMock(return_value={
        "id": "ent-1",
        "name": "John Doe",
        "type": "PERSON",
        "relationships": [
            {"type": "WORKS_FOR", "target": "ent-2"},
            {"type": "KNOWS", "target": "ent-3"}
        ]
    })
    
    # SQLite metadata mock
    storage.metadata = AsyncMock()
    storage.metadata.get_file_info = AsyncMock(return_value={
        "path": "test.pdf",
        "size": 1000,
        "mime_type": "application/pdf",
        "indexed": True
    })
    
    return storage


@pytest.fixture
def agent(mock_storage_full):
    """Create agent with mocked storage."""
    return RAGAgent(
        mock_storage_full,
        llm_provider="ollama",
        llm_model="llama3.2:latest"
    )


@pytest.fixture
def tools(mock_storage_full):
    """Create tools with mocked storage."""
    return RAGTools(mock_storage_full)


class TestAgentIntegration:
    """Integration tests for agent with tools."""

    @pytest.mark.asyncio
    async def test_vector_search_integration(self, tools, mock_storage_full):
        """Test vector search integration with storage."""
        with patch('src.agent.agent.SentenceTransformer') as mock_embed:
            mock_embed.return_value.encode.return_value = [0.1, 0.2, 0.3]
            
            result = await tools.vector_search("test query", limit=5)
        
        # Verify search was called
        mock_storage_full.postgres.similarity_search.assert_called_once()
        
        # Verify result structure
        assert result.query == "test query"
        assert len(result.results) == 1
        assert result.results[0].text == "PostgreSQL search result"

    @pytest.mark.asyncio
    async def test_graph_search_integration(self, tools, mock_storage_full):
        """Test graph search integration with storage."""
        result = await tools.graph_search("test query", entity_types=["PERSON"])
        
        # Verify Neo4j was called
        mock_storage_full.neo4j.search_entities.assert_called_once()
        mock_storage_full.neo4j.search_relationships.assert_called_once()
        
        # Verify result structure
        assert result.entity_count == 2
        assert result.relationship_count == 1
        assert result.entities[0]["name"] == "John Doe"

    @pytest.mark.asyncio
    async def test_hybrid_search_integration(self, tools, mock_storage_full):
        """Test hybrid search integration combining both backends."""
        with patch('src.agent.agent.SentenceTransformer'):
            result = await tools.hybrid_search("test query", limit=5)
        
        # Verify both backends were called
        mock_storage_full.postgres.similarity_search.assert_called()
        mock_storage_full.neo4j.search_entities.assert_called()
        
        # Verify merged results
        assert result.total_count > 0
        assert len(result.merged_results) > 0

    @pytest.mark.asyncio
    async def test_document_retrieval_integration(self, tools, mock_storage_full):
        """Test document retrieval from PostgreSQL and metadata."""
        result = await tools.retrieve_document("doc-1")
        
        # Verify backends were called
        mock_storage_full.metadata.get_file_info.assert_called_once()
        mock_storage_full.postgres.get_file_chunks.assert_called_once()
        
        # Verify result
        assert result.document_id == "doc-1"
        assert result.chunks == 2
        assert "Chunk 1" in result.content

    @pytest.mark.asyncio
    async def test_entity_context_integration(self, tools, mock_storage_full):
        """Test entity context retrieval from Neo4j."""
        result = await tools.get_entity_context("ent-1", depth=2)
        
        # Verify Neo4j was called
        mock_storage_full.neo4j.get_entity_context.assert_called_once()
        
        # Verify result
        assert result["name"] == "John Doe"
        assert len(result["relationships"]) == 2

    @pytest.mark.asyncio
    async def test_hybrid_search_result_merging(self, tools, mock_storage_full):
        """Test that hybrid search properly merges vector and graph results."""
        with patch('src.agent.agent.SentenceTransformer'):
            result = await tools.hybrid_search("test", limit=5)
        
        # Verify merged results contain both vector and graph results
        assert len(result.vector_results) > 0
        assert len(result.graph_results) > 0
        
        # Verify results are scored and sorted
        if len(result.merged_results) > 1:
            scores = [r.score for r in result.merged_results]
            assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_tool_call_logging_in_agent(self, agent):
        """Test tool call logging within agent context."""
        tool_call = agent._current_tool_calls if hasattr(agent, "_current_tool_calls") else []
        initial_count = len(tool_call)
        
        from src.agent.agent import ToolCall
        call = ToolCall(
            tool_name="test_tool",
            timestamp=datetime.now(),
            arguments={"test": "arg"},
            result="result"
        )
        agent._record_tool_call(call)
        
        assert len(agent._current_tool_calls) == initial_count + 1


class TestMultiBackendCoordination:
    """Test coordination between multiple storage backends."""

    @pytest.mark.asyncio
    async def test_vector_and_graph_consistency(self, tools, mock_storage_full):
        """Test vector and graph results can be correlated."""
        with patch('src.agent.agent.SentenceTransformer'):
            vector_result = await tools.vector_search("test")
            graph_result = await tools.graph_search("test")
        
        # Both should return results
        assert vector_result.count >= 0
        assert graph_result.entity_count >= 0

    @pytest.mark.asyncio
    async def test_metadata_during_retrieval(self, tools, mock_storage_full):
        """Test metadata is properly retrieved during document retrieval."""
        result = await tools.retrieve_document("doc-1")
        
        # Verify metadata is included
        assert result.metadata is not None
        assert "path" in result.metadata

    @pytest.mark.asyncio
    async def test_error_handling_across_backends(self, tools, mock_storage_full):
        """Test error handling when one backend fails."""
        # Make PostgreSQL fail
        mock_storage_full.postgres.similarity_search.side_effect = Exception("DB Error")
        
        with patch('src.agent.agent.SentenceTransformer'):
            with pytest.raises(Exception):
                await tools.vector_search("test")

    @pytest.mark.asyncio
    async def test_partial_failure_in_hybrid_search(self, tools, mock_storage_full):
        """Test hybrid search handles partial failures gracefully."""
        # Make Neo4j fail while PostgreSQL succeeds
        mock_storage_full.neo4j.search_entities.side_effect = Exception("Neo4j Error")
        
        with patch('src.agent.agent.SentenceTransformer'):
            with pytest.raises(Exception):
                # Should fail because hybrid search requires both
                await tools.hybrid_search("test")


class TestToolUsageLogging:
    """Test tool usage logging functionality."""

    def test_tool_usage_log_structure(self, agent):
        """Test tool usage log has correct structure."""
        log = ToolUsageLog(
            query="test query",
            timestamp=datetime.now(),
            tool_calls=[],
            total_duration_ms=150.0,
            final_answer="test answer"
        )
        
        assert log.query == "test query"
        assert log.total_duration_ms == 150.0
        assert log.final_answer == "test answer"
        assert isinstance(log.tool_calls, list)

    def test_tool_call_success_logging(self, agent):
        """Test successful tool call logging."""
        from src.agent.agent import ToolCall
        
        call = ToolCall(
            tool_name="vector_search",
            timestamp=datetime.now(),
            arguments={"query": "test"},
            result="search results",
            success=True
        )
        
        assert call.success is True
        assert call.result == "search results"
        assert call.error is None

    def test_tool_call_failure_logging(self, agent):
        """Test failed tool call logging."""
        from src.agent.agent import ToolCall
        
        call = ToolCall(
            tool_name="graph_search",
            timestamp=datetime.now(),
            arguments={"query": "test"},
            success=False,
            error="Connection timeout"
        )
        
        assert call.success is False
        assert call.error == "Connection timeout"

    def test_tool_usage_export_preparation(self, agent):
        """Test tool usage logs are prepared for export."""
        from src.agent.agent import ToolCall
        
        log = ToolUsageLog(
            query="test",
            timestamp=datetime.now(),
            tool_calls=[
                ToolCall(
                    tool_name="vector_search",
                    timestamp=datetime.now(),
                    arguments={"query": "test"},
                    result="results"
                )
            ]
        )
        
        # Should be serializable to dict
        log_dict = log.model_dump()
        assert "query" in log_dict
        assert "tool_calls" in log_dict


class TestAgentFormatting:
    """Test agent result formatting."""

    def test_format_vector_results_display(self, agent):
        """Test formatting of vector search results for display."""
        from src.agent.agent import SearchResult
        
        results = [
            SearchResult(id="1", score=0.95, text="Result A", source="doc1.pdf"),
            SearchResult(id="2", score=0.87, text="Result B", source="doc2.pdf")
        ]
        
        formatted = agent._format_search_results(results)
        
        assert "Search Results" in formatted
        assert "Result A" in formatted
        assert "Result B" in formatted
        assert "0.95" in formatted
        assert "doc1.pdf" in formatted

    def test_format_graph_display(self, agent):
        """Test formatting of graph results for display."""
        from src.agent.agent import GraphSearchResponse
        
        response = GraphSearchResponse(
            query="test",
            entities=[
                {"name": "Entity A", "type": "PERSON"},
                {"name": "Entity B", "type": "ORG"}
            ],
            relationships=[
                {"source": "A", "type": "KNOWS", "target": "B"}
            ],
            entity_count=2,
            relationship_count=1
        )
        
        formatted = agent._format_graph_results(response)
        
        assert "Graph Search Results" in formatted
        assert "Entities (2)" in formatted
        assert "Entity A" in formatted
        assert "PERSON" in formatted

    def test_format_entity_context_display(self, agent):
        """Test formatting entity context for display."""
        context = {
            "name": "Jane Smith",
            "type": "PERSON",
            "relationships": [
                {"type": "WORKS_FOR", "target": "TechCorp"},
                {"type": "KNOWS", "target": "John Doe"}
            ]
        }
        
        formatted = agent._format_entity_context(context)
        
        assert "Jane Smith" in formatted
        assert "PERSON" in formatted
        assert "WORKS_FOR" in formatted
        assert "TechCorp" in formatted
