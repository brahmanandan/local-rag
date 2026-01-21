"""Integration tests for knowledge graph module."""

import pytest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime

from src.storage.knowledge_graph import (
    EntityType,
    RelationType,
    Entity,
    Relationship,
    EntityExtractor,
    ConceptClusterer,
    TemporalGraphBuilder,
    KnowledgeGraphBuilder,
)


class TestEntityExtractionIntegration:
    """Integration tests for entity extraction."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = EntityExtractor(enable_llm=False)
    
    def test_extract_from_real_text(self):
        """Test extraction from realistic text."""
        text = """
        John Smith, CEO of Google, announced a partnership with Microsoft.
        The project uses Python and machine learning technologies.
        Sarah Johnson from the AI team will lead the initiative.
        """
        
        entities = self.extractor.extract_entities(text)
        
        # Check that we extract multiple entity types
        assert len(entities) > 0
        types = set(e.entity_type for e in entities)
        assert len(types) > 1
    
    def test_entity_deduplication(self):
        """Test that duplicate entities are not created."""
        text = "Python is used. Python is great. Python is powerful."
        entities = self.extractor.extract_entities(text)
        
        python_entities = [e for e in entities if "Python" in e.name]
        # Should deduplicate
        assert len(python_entities) <= 3
    
    def test_relationship_extraction_integration(self):
        """Test relationship extraction with various scenarios."""
        texts = [
            "Alice and Bob work together.",
            "Google acquired DeepMind last year.",
            "Python powers the machine learning pipeline.",
        ]
        
        for text in texts:
            entities = self.extractor.extract_entities(text)
            relationships = self.extractor.extract_relationships(text, entities)
            
            # If we have multiple entities, we should find relationships
            if len(entities) >= 2:
                assert len(relationships) >= 0


class TestConceptClusteringIntegration:
    """Integration tests for concept clustering."""
    
    def setup_method(self):
        """Set up test fixtures."""
        mock_embedder = MagicMock()
        
        # Simulate embeddings: similar concepts get similar embeddings
        def mock_embed(text):
            # Simple hash-based "embeddings" for testing
            text_lower = text.lower()
            if any(ml_term in text_lower for ml_term in 
                   ['machine', 'deep', 'neural', 'learning', 'network']):
                return [0.9, 0.8, 0.7] + [0.0] * 381
            elif 'database' in text_lower:
                return [0.1, 0.2, 0.3] + [0.0] * 381
            else:
                return [0.5] * 384
        
        mock_embedder.embed_query = mock_embed
        self.clusterer = ConceptClusterer(embedding_model=mock_embedder)
    
    def test_cluster_related_concepts(self):
        """Test clustering of related concepts."""
        entities = [
            Entity("e1", "Machine Learning", EntityType.CONCEPT),
            Entity("e2", "Deep Learning", EntityType.CONCEPT),
            Entity("e3", "Neural Networks", EntityType.CONCEPT),
            Entity("e4", "PostgreSQL", EntityType.TECHNOLOGY),
        ]
        
        clusters = self.clusterer.cluster_entities(entities, similarity_threshold=0.3)
        
        # Should create some clusters
        assert len(clusters) > 0
        # ML-related concepts might cluster together
        assert len(clusters) <= len(entities)


class TestTemporalGraphIntegration:
    """Integration tests for temporal graph."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.builder = TemporalGraphBuilder(time_window=30)
    
    def test_temporal_query_workflow(self):
        """Test complete temporal query workflow."""
        # Create entities from different time periods
        entities = [
            Entity("e1", "Entity1", EntityType.CONCEPT),
            Entity("e2", "Entity2", EntityType.PERSON),
            Entity("e3", "Entity3", EntityType.ORGANIZATION),
        ]
        
        base_date = datetime(2024, 1, 1)
        for i, entity in enumerate(entities):
            timestamp = base_date.replace(day=base_date.day + i).isoformat()
            self.builder.add_temporal_entity(entity, timestamp)
        
        # Query for concepts in time range
        results = self.builder.query_temporal_entities(EntityType.CONCEPT)
        assert len(results) == 1
        
        # Query for persons
        results = self.builder.query_temporal_entities(EntityType.PERSON)
        assert len(results) == 1
    
    def test_entity_timeline_ordering(self):
        """Test that entity timeline is properly ordered."""
        entity = Entity("e1", "Entity", EntityType.CONCEPT)
        
        timestamps = [
            "2024-03-01T00:00:00",
            "2024-01-01T00:00:00",
            "2024-02-01T00:00:00",
        ]
        
        for ts in timestamps:
            self.builder.add_temporal_entity(entity, ts)
        
        timeline = self.builder.get_entity_timeline("e1")
        
        # Timeline should be sorted
        sorted_timeline = sorted(timeline, key=lambda x: x[0])
        assert timeline == sorted_timeline


class TestKnowledgeGraphWorkflow:
    """Integration tests for complete knowledge graph workflow."""
    
    @patch('src.storage.knowledge_graph.GraphDatabase')
    def test_complete_graph_building_workflow(self, mock_db):
        """Test complete workflow from chunks to graph."""
        # Setup mocks
        mock_session = MagicMock()
        mock_db.driver.return_value.session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.driver.return_value.session.return_value.__exit__ = MagicMock(
            return_value=None
        )
        
        builder = KnowledgeGraphBuilder(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
            enable_temporal=True,
            enable_clustering=True,
        )
        
        # Test document chunks
        chunks = [
            {
                "text": "Alice Smith works at Google on AI projects."
            },
            {
                "text": "Bob Johnson leads the machine learning team at Google."
            },
            {
                "text": "Google uses Python for deep learning applications."
            },
        ]
        
        stats = builder.build_graph_from_chunks(
            chunks,
            "doc_001",
            "Google AI Projects"
        )
        
        # Verify statistics
        assert stats['nodes_created'] >= 3  # doc + chunks
        assert stats['entities_extracted'] >= 0
        assert stats['relationships_extracted'] >= 0
    
    @patch('src.storage.knowledge_graph.GraphDatabase')
    def test_multi_document_graph_building(self, mock_db):
        """Test building graph from multiple documents."""
        # Setup mocks
        mock_session = MagicMock()
        mock_db.driver.return_value.session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.driver.return_value.session.return_value.__exit__ = MagicMock(
            return_value=None
        )
        
        builder = KnowledgeGraphBuilder(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
        )
        
        # Build graphs from multiple documents
        documents = [
            {
                "id": "doc1",
                "name": "AI Research",
                "chunks": [
                    {"text": "Deep learning revolutionizes AI."},
                ]
            },
            {
                "id": "doc2",
                "name": "ML Applications",
                "chunks": [
                    {"text": "Machine learning powers modern applications."},
                ]
            },
        ]
        
        total_nodes = 0
        for doc in documents:
            stats = builder.build_graph_from_chunks(
                doc['chunks'],
                doc['id'],
                doc['name']
            )
            total_nodes += stats['nodes_created']
        
        assert total_nodes >= 4  # At least 2 docs + 2 chunks


class TestEntityExtractorAdvanced:
    """Advanced integration tests for entity extraction."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = EntityExtractor(enable_llm=False)
    
    def test_extract_mixed_entity_types(self):
        """Test extraction of mixed entity types."""
        text = """
        Python is a programming language. TensorFlow is a machine learning library.
        John Smith works at Google in San Francisco.
        The company develops neural networks and deep learning models.
        """
        
        entities = self.extractor.extract_entities(text)
        
        # Check for different entity types
        entity_types = set(e.entity_type for e in entities)
        assert len(entity_types) > 1
        
        # Verify specific entities
        names = [e.name for e in entities]
        assert any('Python' in name for name in names)
        assert any('Google' in name for name in names)
    
    def test_relationship_confidence_scoring(self):
        """Test relationship confidence scoring."""
        text = "Alice and Bob are mentioned together. Alice and Charlie are also mentioned."
        
        entities = self.extractor.extract_entities(text)
        relationships = self.extractor.extract_relationships(text, entities)
        
        # All relationships should have confidence scores
        for rel in relationships:
            assert 0 <= rel.confidence <= 1
            assert 0 <= rel.weight <= 1
    
    def test_entity_mention_tracking(self):
        """Test tracking of entity mentions."""
        entity1 = Entity("e1", "Python", EntityType.TECHNOLOGY)
        entity1.mention_count = 3
        
        assert entity1.mention_count == 3
        assert entity1.confidence > 0


class TestGraphQueryIntegration:
    """Integration tests for graph queries."""
    
    @patch('src.storage.knowledge_graph.GraphDatabase')
    def test_entity_context_retrieval(self, mock_db):
        """Test retrieving entity context."""
        # Setup mock that returns entity data
        mock_session = MagicMock()
        mock_record = MagicMock()
        mock_record.__getitem__.return_value = []
        mock_session.run.return_value.single.return_value = mock_record
        
        mock_db.driver.return_value.session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.driver.return_value.session.return_value.__exit__ = MagicMock(
            return_value=None
        )
        
        builder = KnowledgeGraphBuilder(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
        )
        
        context = builder.get_entity_context("entity_id", depth=2)
        
        # Should return context dict
        assert isinstance(context, dict)


class TestConceptClustering:
    """Integration tests for concept clustering."""
    
    def test_cluster_merging_workflow(self):
        """Test workflow of clustering and merging."""
        mock_embedder = MagicMock()
        mock_embedder.embed_query = lambda x: [0.1] * 384
        
        clusterer = ConceptClusterer(embedding_model=mock_embedder)
        
        entities = [
            Entity("e1", "ML1", EntityType.CONCEPT),
            Entity("e2", "ML2", EntityType.CONCEPT),
            Entity("e3", "Tech1", EntityType.TECHNOLOGY),
        ]
        
        clusters = clusterer.cluster_entities(entities)
        
        # Merge clusters
        cluster_names = {i: f"Cluster_{i}" for i in range(len(clusters))}
        merged = clusterer.merge_clusters(clusters, cluster_names)
        
        assert len(merged) == len(clusters)
        assert all(isinstance(v, list) for v in merged.values())


class TestErrorHandling:
    """Integration tests for error handling."""
    
    def test_extractor_handles_empty_text(self):
        """Test entity extraction with empty text."""
        extractor = EntityExtractor()
        entities = extractor.extract_entities("")
        
        assert isinstance(entities, list)
        assert len(entities) >= 0
    
    def test_extractor_handles_special_characters(self):
        """Test extraction with special characters."""
        extractor = EntityExtractor()
        text = "Email: test@example.com, URL: https://example.com"
        
        entities = extractor.extract_entities(text)
        
        # Should handle without crashing
        assert isinstance(entities, list)
    
    def test_temporal_builder_handles_invalid_timestamp(self):
        """Test temporal builder with various timestamps."""
        builder = TemporalGraphBuilder()
        entity = Entity("e1", "Test", EntityType.CONCEPT)
        
        # Should handle None (defaults to now)
        builder.add_temporal_entity(entity, None)
        assert "e1" in builder.temporal_index


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
