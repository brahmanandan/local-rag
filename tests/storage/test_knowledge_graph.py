"""Unit tests for knowledge graph module."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
import hashlib

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


class TestEntity:
    """Test Entity dataclass."""
    
    def test_entity_creation(self):
        """Test basic entity creation."""
        entity = Entity(
            id="e1",
            name="John Doe",
            entity_type=EntityType.PERSON,
        )
        assert entity.id == "e1"
        assert entity.name == "John Doe"
        assert entity.entity_type == EntityType.PERSON
        assert entity.confidence == 1.0
        assert entity.mention_count == 1
    
    def test_entity_with_properties(self):
        """Test entity with custom properties."""
        props = {"age": 30, "location": "NYC"}
        entity = Entity(
            id="e1",
            name="John",
            entity_type=EntityType.PERSON,
            properties=props,
        )
        assert entity.properties == props
    
    def test_entity_timestamps(self):
        """Test entity timestamps are set."""
        entity = Entity(
            id="e1",
            name="Concept",
            entity_type=EntityType.CONCEPT,
        )
        assert entity.first_seen is not None
        assert entity.last_seen is not None
        assert entity.first_seen == entity.last_seen


class TestRelationship:
    """Test Relationship dataclass."""
    
    def test_relationship_creation(self):
        """Test basic relationship creation."""
        rel = Relationship(
            source_id="e1",
            target_id="e2",
            relation_type=RelationType.MENTIONS,
        )
        assert rel.source_id == "e1"
        assert rel.target_id == "e2"
        assert rel.relation_type == RelationType.MENTIONS
        assert rel.confidence == 1.0
        assert rel.weight == 1.0
    
    def test_relationship_with_confidence(self):
        """Test relationship with confidence score."""
        rel = Relationship(
            source_id="e1",
            target_id="e2",
            relation_type=RelationType.RELATES_TO,
            confidence=0.75,
            weight=0.75,
        )
        assert rel.confidence == 0.75
        assert rel.weight == 0.75


class TestEntityExtractor:
    """Test EntityExtractor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = EntityExtractor(enable_llm=False)
    
    def test_extract_entities_person(self):
        """Test person extraction."""
        text = "John Smith met with Sarah Johnson yesterday."
        entities = self.extractor.extract_entities(text)
        
        names = [e.name for e in entities]
        assert any("John" in name for name in names)
        assert any("Sarah" in name for name in names)
    
    def test_extract_entities_technology(self):
        """Test technology extraction."""
        text = "We built the system using Python and PostgreSQL."
        entities = self.extractor.extract_entities(text)
        
        names = [e.name for e in entities]
        assert any("Python" in name for name in names)
        assert any("PostgreSQL" in name for name in names)
    
    def test_extract_entities_concept(self):
        """Test concept extraction."""
        text = "The model uses machine learning and deep learning techniques."
        entities = self.extractor.extract_entities(text)
        
        types = [e.entity_type for e in entities]
        assert EntityType.CONCEPT in types
    
    def test_extract_relationships_cooccurrence(self):
        """Test relationship extraction."""
        text = "John Smith works at Google with Sarah Johnson."
        entities = self.extractor.extract_entities(text)
        relationships = self.extractor.extract_relationships(text, entities)
        
        # Should find co-occurrence relationship
        assert len(relationships) > 0
        assert all(r.relation_type == RelationType.CO_OCCURS 
                   for r in relationships)
    
    def test_extract_no_relationships(self):
        """Test extraction with no relationships."""
        entities = [Entity("e1", "Entity1", EntityType.CONCEPT)]
        relationships = self.extractor.extract_relationships("text", entities)
        
        # Single entity should have no relationships
        assert len(relationships) == 0


class TestConceptClusterer:
    """Test ConceptClusterer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        mock_embedder = Mock()
        mock_embedder.embed_query = Mock(
            side_effect=lambda x: [0.1] * 384
        )
        self.clusterer = ConceptClusterer(embedding_model=mock_embedder)
    
    def test_cluster_entities_no_embedder(self):
        """Test clustering without embedder."""
        clusterer = ConceptClusterer(embedding_model=None)
        entities = [
            Entity("e1", "Entity1", EntityType.CONCEPT),
            Entity("e2", "Entity2", EntityType.CONCEPT),
        ]
        
        clusters = clusterer.cluster_entities(entities)
        
        # Without embedder, each entity is in its own cluster
        assert len(clusters) == 2
    
    def test_cluster_entities_with_embedder(self):
        """Test clustering with embedder."""
        entities = [
            Entity("e1", "Machine Learning", EntityType.CONCEPT),
            Entity("e2", "Deep Learning", EntityType.CONCEPT),
            Entity("e3", "Neural Network", EntityType.CONCEPT),
        ]
        
        clusters = self.clusterer.cluster_entities(entities)
        
        # Should create clusters
        assert len(clusters) > 0
        assert all(isinstance(c, list) for c in clusters)
    
    def test_merge_clusters(self):
        """Test cluster merging."""
        entities = [
            Entity("e1", "Entity1", EntityType.CONCEPT),
            Entity("e2", "Entity2", EntityType.CONCEPT),
        ]
        clusters = [[entities[0]], [entities[1]]]
        cluster_names = {0: "Concept1", 1: "Concept2"}
        
        result = self.clusterer.merge_clusters(clusters, cluster_names)
        
        assert "Concept1" in result
        assert "Concept2" in result
        assert result["Concept1"] == [entities[0]]


class TestTemporalGraphBuilder:
    """Test TemporalGraphBuilder class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.builder = TemporalGraphBuilder(time_window=7)
    
    def test_add_temporal_entity(self):
        """Test adding temporal entity."""
        entity = Entity("e1", "Entity1", EntityType.CONCEPT)
        self.builder.add_temporal_entity(entity)
        
        assert "e1" in self.builder.temporal_index
    
    def test_add_temporal_entity_with_timestamp(self):
        """Test adding entity with specific timestamp."""
        entity = Entity("e1", "Entity1", EntityType.CONCEPT)
        timestamp = "2024-01-15T10:30:00"
        
        self.builder.add_temporal_entity(entity, timestamp)
        
        records = self.builder.temporal_index["e1"]
        assert len(records) == 1
        assert records[0]['timestamp'] == timestamp
    
    def test_query_temporal_entities(self):
        """Test querying temporal entities."""
        entity1 = Entity("e1", "Entity1", EntityType.CONCEPT)
        entity2 = Entity("e2", "Entity2", EntityType.PERSON)
        
        now = datetime.utcnow()
        self.builder.add_temporal_entity(entity1, now.isoformat())
        self.builder.add_temporal_entity(entity2, now.isoformat())
        
        results = self.builder.query_temporal_entities(EntityType.CONCEPT)
        
        assert len(results) == 1
        assert results[0].entity_type == EntityType.CONCEPT
    
    def test_get_entity_timeline(self):
        """Test getting entity timeline."""
        entity = Entity("e1", "Entity1", EntityType.CONCEPT)
        
        self.builder.add_temporal_entity(entity, "2024-01-10T00:00:00")
        self.builder.add_temporal_entity(entity, "2024-01-15T00:00:00")
        self.builder.add_temporal_entity(entity, "2024-01-20T00:00:00")
        
        timeline = self.builder.get_entity_timeline("e1")
        
        assert len(timeline) == 3
        # Timeline should be sorted
        assert timeline[0][0] <= timeline[1][0] <= timeline[2][0]
    
    def test_get_empty_timeline(self):
        """Test getting timeline for non-existent entity."""
        timeline = self.builder.get_entity_timeline("nonexistent")
        
        assert timeline == []


class TestKnowledgeGraphBuilder:
    """Test KnowledgeGraphBuilder class."""
    
    @pytest.fixture
    def mock_driver(self):
        """Create mock Neo4j driver."""
        driver = MagicMock()
        session = MagicMock()
        driver.session.return_value.__enter__ = Mock(return_value=session)
        driver.session.return_value.__exit__ = Mock(return_value=None)
        return driver
    
    @patch('src.storage.knowledge_graph.GraphDatabase')
    def test_builder_initialization(self, mock_db):
        """Test builder initialization."""
        mock_db.driver.return_value = MagicMock()
        
        builder = KnowledgeGraphBuilder(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
        )
        
        assert builder is not None
        assert builder.entity_extractor is not None
        assert builder.concept_clusterer is not None
        assert builder.enable_temporal is True
    
    @patch('src.storage.knowledge_graph.GraphDatabase')
    def test_build_graph_from_chunks(self, mock_db):
        """Test graph building from chunks."""
        mock_session = MagicMock()
        mock_db.driver.return_value.session.return_value.__enter__ = Mock(
            return_value=mock_session
        )
        mock_db.driver.return_value.session.return_value.__exit__ = Mock(
            return_value=None
        )
        
        builder = KnowledgeGraphBuilder(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
        )
        
        chunks = [
            {"text": "John Smith works at Google on machine learning projects."},
            {"text": "Sarah Johnson leads the AI team with deep learning expertise."},
        ]
        
        stats = builder.build_graph_from_chunks(chunks, "doc1", "Test Document")
        
        assert stats['nodes_created'] >= 2  # At least document and chunks
        assert stats['entities_extracted'] >= 0
        assert 'relationships_extracted' in stats


class TestEntityTypes:
    """Test EntityType enum."""
    
    def test_entity_type_values(self):
        """Test entity type values."""
        assert EntityType.PERSON.value == "PERSON"
        assert EntityType.ORGANIZATION.value == "ORGANIZATION"
        assert EntityType.CONCEPT.value == "CONCEPT"
        assert EntityType.TECHNOLOGY.value == "TECHNOLOGY"


class TestRelationTypes:
    """Test RelationType enum."""
    
    def test_relation_type_values(self):
        """Test relation type values."""
        assert RelationType.MENTIONS.value == "MENTIONS"
        assert RelationType.CO_OCCURS.value == "CO_OCCURS"
        assert RelationType.RELATES_TO.value == "RELATES_TO"
        assert RelationType.TEMPORAL_BEFORE.value == "TEMPORAL_BEFORE"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
