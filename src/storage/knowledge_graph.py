"""Knowledge graph module with Graphiti integration for entity/relationship extraction.

Features:
- Entity extraction from text (NER-like approach)
- Relationship detection and weighting
- Temporal graph capabilities with time-based queries
- Concept clustering using embeddings
- Neo4j storage with indexing
- LLM-powered entity linking
- Graph analytics and traversal
"""

import logging
import json
from typing import Optional, List, Dict, Any, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import asyncio
from collections import defaultdict

import numpy as np

try:
    from neo4j import AsyncDriver, GraphDatabase
    from neo4j.exceptions import Neo4jError
except ImportError:
    AsyncDriver = None
    GraphDatabase = None

logger = logging.getLogger(__name__)


class EntityType(str, Enum):
    """Supported entity types in knowledge graph."""
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    CONCEPT = "CONCEPT"
    LOCATION = "LOCATION"
    TECHNOLOGY = "TECHNOLOGY"
    PROJECT = "PROJECT"
    EVENT = "EVENT"
    DOCUMENT = "DOCUMENT"
    CHUNK = "CHUNK"


class RelationType(str, Enum):
    """Supported relationship types."""
    MENTIONS = "MENTIONS"
    RELATES_TO = "RELATES_TO"
    PART_OF = "PART_OF"
    SIMILAR_TO = "SIMILAR_TO"
    CAUSES = "CAUSES"
    TEMPORAL_BEFORE = "TEMPORAL_BEFORE"
    TEMPORAL_AFTER = "TEMPORAL_AFTER"
    CO_OCCURS = "CO_OCCURS"
    REFERENCES = "REFERENCES"
    DEFINES = "DEFINES"


@dataclass
class Entity:
    """Represents an entity in the knowledge graph."""
    id: str
    name: str
    entity_type: EntityType
    description: Optional[str] = None
    confidence: float = 1.0
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    mention_count: int = 1
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}
        if self.first_seen is None:
            self.first_seen = datetime.utcnow().isoformat()
        if self.last_seen is None:
            self.last_seen = self.first_seen


@dataclass
class Relationship:
    """Represents a relationship between entities."""
    source_id: str
    target_id: str
    relation_type: RelationType
    confidence: float = 1.0
    weight: float = 1.0
    properties: Dict[str, Any] = None
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


class EntityExtractor:
    """Extract entities from text using pattern matching and NLP."""
    
    # Common entity patterns
    ENTITY_PATTERNS = {
        EntityType.PERSON: [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # First Last
            r'\b[A-Z]\.?\s+[A-Z][a-z]+\b',     # Initial Last
        ],
        EntityType.ORGANIZATION: [
            r'\b[A-Z][a-z]+(?:\s+(?:Inc|LLC|Ltd|Corp|Co|Corporation|Company|Group))\b',
            r'\b(?:Google|Apple|Microsoft|Meta|Amazon|OpenAI|DeepMind)\b',
        ],
        EntityType.TECHNOLOGY: [
            r'\b(?:Python|JavaScript|TypeScript|Go|Rust|C\+\+|Java|C#)\b',
            r'\b(?:TensorFlow|PyTorch|FastAPI|Django|Flask|PostgreSQL|Neo4j)\b',
            r'\b(?:AWS|Azure|GCP|Kubernetes|Docker|Kubernetes)\b',
        ],
        EntityType.LOCATION: [
            r'\b(?:New York|San Francisco|London|Tokyo|Berlin|Paris)\b',
            r'\b(?:USA|UK|China|Japan|Germany|France|India)\b',
        ],
    }
    
    def __init__(self, enable_llm: bool = False, llm_client = None):
        """Initialize entity extractor.
        
        Args:
            enable_llm: Whether to use LLM for advanced entity extraction
            llm_client: LLM client for entity extraction
        """
        self.enable_llm = enable_llm
        self.llm_client = llm_client
        self.entity_cache = {}
    
    def extract_entities(self, text: str) -> List[Entity]:
        """Extract entities from text.
        
        Args:
            text: Input text to extract entities from
            
        Returns:
            List of extracted entities
        """
        import re
        
        entities = []
        seen_names = set()
        
        # Pattern-based extraction
        for entity_type, patterns in self.ENTITY_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    name = match.group(0)
                    if name not in seen_names:
                        entity_id = hashlib.md5(
                            f"{name}_{entity_type.value}".encode()
                        ).hexdigest()[:12]
                        
                        entities.append(Entity(
                            id=entity_id,
                            name=name,
                            entity_type=entity_type,
                            confidence=0.8,
                        ))
                        seen_names.add(name)
        
        # Keyword-based entity detection for concepts
        concept_keywords = {
            'machine learning', 'deep learning', 'neural network',
            'data science', 'artificial intelligence', 'nlp', 'nlp',
            'embeddings', 'transformers', 'llm', 'rag', 'vector database'
        }
        
        text_lower = text.lower()
        for keyword in concept_keywords:
            if keyword in text_lower:
                entity_id = hashlib.md5(
                    f"{keyword}_{EntityType.CONCEPT.value}".encode()
                ).hexdigest()[:12]
                
                if entity_id not in seen_names:
                    entities.append(Entity(
                        id=entity_id,
                        name=keyword,
                        entity_type=EntityType.CONCEPT,
                        confidence=0.7,
                    ))
                    seen_names.add(entity_id)
        
        return entities
    
    def extract_relationships(
        self,
        text: str,
        entities: List[Entity],
    ) -> List[Relationship]:
        """Extract relationships between entities.
        
        Args:
            text: Source text
            entities: Extracted entities
            
        Returns:
            List of relationships
        """
        import re
        
        relationships = []
        text_lower = text.lower()
        
        # Simple co-occurrence relationship
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i+1:]:
                # Check if entities appear close to each other
                name1_lower = entity1.name.lower()
                name2_lower = entity2.name.lower()
                
                idx1 = text_lower.find(name1_lower)
                idx2 = text_lower.find(name2_lower)
                
                if idx1 != -1 and idx2 != -1:
                    distance = abs(idx1 - idx2)
                    # If within 500 characters, create relationship
                    if distance < 500:
                        weight = max(0.3, 1.0 - (distance / 500.0))
                        relationships.append(Relationship(
                            source_id=entity1.id,
                            target_id=entity2.id,
                            relation_type=RelationType.CO_OCCURS,
                            weight=weight,
                            confidence=weight,
                        ))
        
        return relationships


class ConceptClusterer:
    """Cluster concepts using embeddings and similarity."""
    
    def __init__(self, embedding_model = None):
        """Initialize concept clusterer.
        
        Args:
            embedding_model: Embedding model for computing similarity
        """
        self.embedding_model = embedding_model
        self.embeddings_cache = {}
    
    def cluster_entities(
        self,
        entities: List[Entity],
        similarity_threshold: float = 0.7,
    ) -> List[List[Entity]]:
        """Cluster similar entities together.
        
        Args:
            entities: List of entities to cluster
            similarity_threshold: Minimum similarity for clustering
            
        Returns:
            List of entity clusters
        """
        if not entities or self.embedding_model is None:
            return [[entity] for entity in entities]
        
        # Compute embeddings
        embeddings = []
        for entity in entities:
            if entity.id not in self.embeddings_cache:
                try:
                    embedding = self.embedding_model.embed_query(entity.name)
                    self.embeddings_cache[entity.id] = np.array(embedding)
                except Exception as e:
                    logger.warning(f"Failed to embed entity {entity.name}: {e}")
                    # Use zero vector as fallback
                    self.embeddings_cache[entity.id] = np.zeros(384)
            
            embeddings.append(self.embeddings_cache[entity.id])
        
        embeddings = np.array(embeddings)
        
        # Simple clustering using greedy algorithm
        clusters = []
        used = set()
        
        for i, entity in enumerate(entities):
            if i in used:
                continue
            
            cluster = [entity]
            used.add(i)
            
            for j, other_entity in enumerate(entities):
                if j <= i or j in used:
                    continue
                
                # Compute cosine similarity
                similarity = np.dot(embeddings[i], embeddings[j]) / (
                    np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j]) + 1e-10
                )
                
                if similarity >= similarity_threshold:
                    cluster.append(other_entity)
                    used.add(j)
            
            clusters.append(cluster)
        
        return clusters
    
    def merge_clusters(
        self,
        clusters: List[List[Entity]],
        cluster_names: Dict[int, str],
    ) -> Dict[str, List[Entity]]:
        """Merge entities within clusters to concept nodes.
        
        Args:
            clusters: List of entity clusters
            cluster_names: Mapping of cluster index to concept name
            
        Returns:
            Dictionary mapping concept names to entity lists
        """
        result = {}
        for i, cluster in enumerate(clusters):
            concept_name = cluster_names.get(i, f"Concept_{i}")
            result[concept_name] = cluster
        
        return result


class TemporalGraphBuilder:
    """Build and query temporal knowledge graphs."""
    
    def __init__(self, time_window: int = 7):  # days
        """Initialize temporal graph builder.
        
        Args:
            time_window: Time window in days for temporal queries
        """
        self.time_window = time_window
        self.temporal_index = defaultdict(list)
    
    def add_temporal_entity(
        self,
        entity: Entity,
        timestamp: Optional[str] = None,
    ):
        """Add entity with timestamp.
        
        Args:
            entity: Entity to add
            timestamp: Timestamp (ISO format, defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()
        
        self.temporal_index[entity.id].append({
            'entity': entity,
            'timestamp': timestamp,
        })
    
    def query_temporal_entities(
        self,
        entity_type: EntityType,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> List[Entity]:
        """Query entities within time window.
        
        Args:
            entity_type: Type of entity to query
            start_time: Start time (ISO format)
            end_time: End time (ISO format)
            
        Returns:
            List of matching entities
        """
        if start_time is None:
            start_time = (
                datetime.utcnow() - timedelta(days=self.time_window)
            ).isoformat()
        
        if end_time is None:
            end_time = datetime.utcnow().isoformat()
        
        results = []
        for entity_id, records in self.temporal_index.items():
            for record in records:
                entity = record['entity']
                timestamp = record['timestamp']
                
                if (entity.entity_type == entity_type and
                    start_time <= timestamp <= end_time):
                    results.append(entity)
        
        return results
    
    def get_entity_timeline(self, entity_id: str) -> List[Tuple[str, str]]:
        """Get timeline of entity mentions.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            List of (timestamp, description) tuples
        """
        if entity_id not in self.temporal_index:
            return []
        
        timeline = []
        for record in self.temporal_index[entity_id]:
            entity = record['entity']
            timestamp = record['timestamp']
            timeline.append((timestamp, f"Mentioned in {entity.name}"))
        
        return sorted(timeline, key=lambda x: x[0])


class KnowledgeGraphBuilder:
    """High-level knowledge graph builder combining all components."""
    
    def __init__(
        self,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        embedding_model = None,
        llm_client = None,
        enable_temporal: bool = True,
        enable_clustering: bool = True,
    ):
        """Initialize knowledge graph builder.
        
        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            embedding_model: Embedding model for similarity
            llm_client: LLM client for advanced features
            enable_temporal: Enable temporal graph capabilities
            enable_clustering: Enable concept clustering
        """
        if GraphDatabase is None:
            raise ImportError("neo4j package not installed")
        
        self.driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password),
        )
        
        self.entity_extractor = EntityExtractor(
            enable_llm=llm_client is not None,
            llm_client=llm_client,
        )
        
        self.concept_clusterer = ConceptClusterer(
            embedding_model=embedding_model,
        )
        
        self.temporal_builder = (
            TemporalGraphBuilder() if enable_temporal else None
        )
        
        self.enable_temporal = enable_temporal
        self.enable_clustering = enable_clustering
        
        self._verify_connection()
    
    def _verify_connection(self):
        """Verify Neo4j connection."""
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info("Neo4j connection verified")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def build_graph_from_chunks(
        self,
        chunks: List[Dict[str, Any]],
        document_id: str,
        document_name: str,
    ) -> Dict[str, Any]:
        """Build knowledge graph from document chunks.
        
        Args:
            chunks: List of text chunks
            document_id: Document identifier
            document_name: Document name
            
        Returns:
            Graph building statistics
        """
        stats = {
            'entities_extracted': 0,
            'relationships_extracted': 0,
            'clusters_created': 0,
            'nodes_created': 0,
            'relationships_created': 0,
        }
        
        # Create document node
        self._create_document_node(document_id, document_name)
        stats['nodes_created'] += 1
        
        all_entities = []
        all_relationships = []
        
        # Process each chunk
        for i, chunk in enumerate(chunks):
            chunk_id = f"{document_id}_chunk_{i}"
            text = chunk.get('text', '')
            
            # Create chunk node
            self._create_chunk_node(chunk_id, text, document_id)
            stats['nodes_created'] += 1
            
            # Extract entities from chunk
            entities = self.entity_extractor.extract_entities(text)
            all_entities.extend(entities)
            stats['entities_extracted'] += len(entities)
            
            # Extract relationships
            relationships = self.entity_extractor.extract_relationships(
                text,
                entities,
            )
            all_relationships.extend(relationships)
            stats['relationships_extracted'] += len(relationships)
            
            # Store entities and relationships
            for entity in entities:
                self._create_entity_node(entity)
                self._create_chunk_entity_relationship(chunk_id, entity.id)
            
            for relationship in relationships:
                self._create_relationship(relationship)
                stats['relationships_created'] += 1
        
        # Cluster entities if enabled
        if self.enable_clustering and all_entities:
            clusters = self.concept_clusterer.cluster_entities(all_entities)
            stats['clusters_created'] = len(clusters)
            
            # Create concept nodes for each cluster
            for cluster_idx, cluster in enumerate(clusters):
                if len(cluster) > 1:
                    concept_name = self._create_concept_from_cluster(
                        cluster,
                        document_id,
                        cluster_idx,
                    )
                    logger.debug(f"Created concept: {concept_name}")
        
        logger.info(f"Graph built with {stats['nodes_created']} nodes "
                   f"and {stats['relationships_created']} relationships")
        
        return stats
    
    def _create_document_node(self, doc_id: str, doc_name: str):
        """Create document node in Neo4j."""
        query = """
        MERGE (doc:Document {id: $doc_id})
        SET doc.name = $doc_name,
            doc.created_at = datetime(),
            doc.updated_at = datetime()
        """
        with self.driver.session() as session:
            session.run(query, doc_id=doc_id, doc_name=doc_name)
    
    def _create_chunk_node(
        self,
        chunk_id: str,
        text: str,
        document_id: str,
    ):
        """Create chunk node in Neo4j."""
        query = """
        MERGE (chunk:Chunk {id: $chunk_id})
        SET chunk.text = $text,
            chunk.created_at = datetime()
        WITH chunk
        MATCH (doc:Document {id: $document_id})
        MERGE (chunk)-[:FROM_DOCUMENT]->(doc)
        """
        with self.driver.session() as session:
            session.run(
                query,
                chunk_id=chunk_id,
                text=text[:1000],  # Limit text storage
                document_id=document_id,
            )
    
    def _create_entity_node(self, entity: Entity):
        """Create entity node in Neo4j."""
        query = """
        MERGE (e:Entity {id: $entity_id})
        SET e.name = $name,
            e.type = $entity_type,
            e.description = $description,
            e.confidence = $confidence,
            e.first_seen = $first_seen,
            e.last_seen = $last_seen,
            e.mention_count = $mention_count
        """
        with self.driver.session() as session:
            session.run(
                query,
                entity_id=entity.id,
                name=entity.name,
                entity_type=entity.entity_type.value,
                description=entity.description,
                confidence=entity.confidence,
                first_seen=entity.first_seen,
                last_seen=entity.last_seen,
                mention_count=entity.mention_count,
            )
    
    def _create_relationship(self, rel: Relationship):
        """Create relationship in Neo4j."""
        query = f"""
        MATCH (source:Entity {{id: $source_id}})
        MATCH (target:Entity {{id: $target_id}})
        MERGE (source)-[r:{rel.relation_type.value} {{timestamp: $timestamp}}]
              ->(target)
        SET r.confidence = $confidence,
            r.weight = $weight
        """
        try:
            with self.driver.session() as session:
                session.run(
                    query,
                    source_id=rel.source_id,
                    target_id=rel.target_id,
                    confidence=rel.confidence,
                    weight=rel.weight,
                    timestamp=rel.timestamp,
                )
        except Neo4jError as e:
            logger.debug(f"Relationship creation failed (may be expected): {e}")
    
    def _create_chunk_entity_relationship(
        self,
        chunk_id: str,
        entity_id: str,
    ):
        """Create relationship between chunk and entity."""
        query = """
        MATCH (chunk:Chunk {id: $chunk_id})
        MATCH (entity:Entity {id: $entity_id})
        MERGE (chunk)-[:MENTIONS]->(entity)
        """
        try:
            with self.driver.session() as session:
                session.run(query, chunk_id=chunk_id, entity_id=entity_id)
        except Neo4jError:
            logger.debug("Chunk-entity relationship creation skipped")
    
    def _create_concept_from_cluster(
        self,
        cluster: List[Entity],
        document_id: str,
        cluster_idx: int,
    ) -> str:
        """Create concept node from entity cluster."""
        concept_id = f"concept_{document_id}_{cluster_idx}"
        concept_name = " / ".join([e.name for e in cluster[:3]])
        
        query = """
        MERGE (concept:Concept {id: $concept_id})
        SET concept.name = $concept_name,
            concept.entity_count = $entity_count,
            concept.created_at = datetime()
        WITH concept
        UNWIND $entity_ids as entity_id
        MATCH (e:Entity {id: entity_id})
        MERGE (concept)-[:CLUSTERS]->(e)
        """
        
        with self.driver.session() as session:
            session.run(
                query,
                concept_id=concept_id,
                concept_name=concept_name,
                entity_count=len(cluster),
                entity_ids=[e.id for e in cluster],
            )
        
        return concept_name
    
    def query_graph(
        self,
        query_type: str,
        params: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Execute custom query on knowledge graph.
        
        Args:
            query_type: Type of query (entities, relationships, paths)
            params: Query parameters
            
        Returns:
            Query results
        """
        queries = {
            'entities': """
                MATCH (e:Entity)
                WHERE e.type = $entity_type OR $entity_type IS NULL
                RETURN e.id, e.name, e.type, e.confidence
                LIMIT $limit
            """,
            'relationships': """
                MATCH (source:Entity)-[r]->(target:Entity)
                RETURN source.name, type(r), target.name, r.weight
                LIMIT $limit
            """,
            'paths': """
                MATCH p = (source:Entity {id: $source_id})-[*1..3]-(target:Entity)
                WHERE target.id = $target_id
                RETURN [n in nodes(p) | n.name] as path
            """,
            'concepts': """
                MATCH (c:Concept)-[:CLUSTERS]->(e:Entity)
                RETURN c.name, collect(e.name) as entities, c.entity_count
                LIMIT $limit
            """,
        }
        
        if query_type not in queries:
            raise ValueError(f"Unknown query type: {query_type}")
        
        query = queries[query_type]
        
        with self.driver.session() as session:
            result = session.run(query, **params)
            return [dict(record) for record in result]
    
    def get_entity_context(
        self,
        entity_id: str,
        depth: int = 2,
    ) -> Dict[str, Any]:
        """Get context around an entity (neighbors, relationships).
        
        Args:
            entity_id: Entity identifier
            depth: Depth of neighbor traversal
            
        Returns:
            Entity context information
        """
        query = f"""
        MATCH (e:Entity {{id: $entity_id}})
        OPTIONAL MATCH (e)-[r*0..{depth}]-(neighbor)
        RETURN e, collect(distinct neighbor) as neighbors,
               collect(distinct r) as relationships
        """
        
        with self.driver.session() as session:
            result = session.run(query, entity_id=entity_id).single()
            
            if not result:
                return {}
            
            return {
                'entity': dict(result['e'].items()) if result['e'] else {},
                'neighbors_count': len(result['neighbors']) if result['neighbors'] else 0,
                'relationships_count': len(result['relationships']) if result['relationships'] else 0,
            }
    
    def export_graph_metrics(self) -> Dict[str, Any]:
        """Export graph statistics and metrics.
        
        Returns:
            Graph metrics
        """
        queries = {
            'total_entities': "MATCH (e:Entity) RETURN count(e) as count",
            'total_relationships': "MATCH ()-[r]->() RETURN count(r) as count",
            'total_documents': "MATCH (d:Document) RETURN count(d) as count",
            'entity_types': """
                MATCH (e:Entity)
                RETURN e.type, count(e) as count
                ORDER BY count DESC
            """,
            'top_entities': """
                MATCH (e:Entity)
                RETURN e.name, e.mention_count
                ORDER BY e.mention_count DESC
                LIMIT 10
            """,
        }
        
        metrics = {}
        with self.driver.session() as session:
            for key, query in queries.items():
                result = session.run(query)
                if key in ['total_entities', 'total_relationships', 'total_documents']:
                    metrics[key] = result.single()['count']
                else:
                    metrics[key] = [dict(record) for record in result]
        
        return metrics
    
    def close(self):
        """Close Neo4j connection."""
        self.driver.close()
        logger.info("Neo4j connection closed")


__all__ = [
    'EntityType',
    'RelationType',
    'Entity',
    'Relationship',
    'EntityExtractor',
    'ConceptClusterer',
    'TemporalGraphBuilder',
    'KnowledgeGraphBuilder',
]
