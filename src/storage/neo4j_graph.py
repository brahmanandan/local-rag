"""Neo4j-based knowledge graph storage for entity/relationship tracking."""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import json

try:
    from neo4j import AsyncDriver, asyncio as neo4j_async, GraphDatabase
except ImportError:
    AsyncDriver = None
    GraphDatabase = None

logger = logging.getLogger(__name__)


class Neo4jGraphStore:
    """Neo4j knowledge graph store for entity/relationship tracking."""

    def __init__(self, uri: str, username: str, password: str):
        """Initialize Neo4j connection.
        
        Args:
            uri: Neo4j connection URI (e.g., "bolt://localhost:7687")
            username: Neo4j username
            password: Neo4j password
        """
        if GraphDatabase is None:
            raise ImportError("neo4j package not installed. Run: pip install neo4j")
        
        self.uri = uri
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        self._verify_connection()
        logger.info(f"Connected to Neo4j: {uri}")

    def _verify_connection(self):
        """Verify Neo4j connection is working."""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1")
                _ = result.single()
            logger.info("Neo4j connection verified")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def create_document_node(
        self,
        doc_id: str,
        file_path: str,
        doc_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create document node in graph.
        
        Args:
            doc_id: Document identifier
            file_path: Path to source file
            doc_type: Document type (pdf, docx, image, etc.)
            metadata: Additional document metadata
            
        Returns:
            Created node info
        """
        query = """
        CREATE (doc:Document {
            id: $doc_id,
            path: $file_path,
            type: $doc_type,
            created_at: datetime(),
            metadata: $metadata
        })
        RETURN doc.id as id
        """
        
        with self.driver.session() as session:
            result = session.run(
                query,
                doc_id=doc_id,
                file_path=file_path,
                doc_type=doc_type,
                metadata=json.dumps(metadata or {}),
            )
            record = result.single()
        
        return {"id": record["id"], "type": "Document"}

    def create_entity_node(
        self,
        entity_id: str,
        name: str,
        entity_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create entity node (Person, Organization, Concept, etc.).
        
        Args:
            entity_id: Entity identifier
            name: Entity name
            entity_type: Type of entity
            properties: Additional properties
            
        Returns:
            Created node info
        """
        query = f"""
        CREATE (entity:{entity_type} {{
            id: $entity_id,
            name: $name,
            created_at: datetime(),
            properties: $properties
        }})
        RETURN entity.id as id
        """
        
        with self.driver.session() as session:
            result = session.run(
                query,
                entity_id=entity_id,
                name=name,
                properties=json.dumps(properties or {}),
            )
            record = result.single()
        
        return {"id": record["id"], "type": entity_type}

    def create_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create relationship between entities.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            relationship_type: Type of relationship
            properties: Relationship properties
            
        Returns:
            Created relationship info
        """
        query = f"""
        MATCH (source {{id: $source_id}})
        MATCH (target {{id: $target_id}})
        CREATE (source)-[rel:{relationship_type} {{
            created_at: datetime(),
            properties: $properties
        }}]->(target)
        RETURN rel as relationship
        """
        
        with self.driver.session() as session:
            result = session.run(
                query,
                source_id=source_id,
                target_id=target_id,
                properties=json.dumps(properties or {}),
            )
            record = result.single()
        
        return {
            "source": source_id,
            "target": target_id,
            "type": relationship_type,
        }

    def extract_entities_from_chunk(
        self,
        chunk_id: str,
        text: str,
        doc_id: str,
        entities: List[Tuple[str, str]],
    ) -> List[Dict[str, Any]]:
        """Extract and store entities from a text chunk.
        
        Args:
            chunk_id: Chunk identifier
            text: Chunk text content
            doc_id: Associated document ID
            entities: List of (entity_name, entity_type) tuples
            
        Returns:
            List of created entity nodes
        """
        created_entities = []
        
        # Create chunk node
        chunk_query = """
        CREATE (chunk:Chunk {
            id: $chunk_id,
            text: $text,
            created_at: datetime()
        })
        RETURN chunk.id as id
        """
        
        with self.driver.session() as session:
            result = session.run(
                chunk_query,
                chunk_id=chunk_id,
                text=text[:5000],  # Truncate very long texts
            )
            session.run(
                """
                MATCH (chunk:Chunk {id: $chunk_id})
                MATCH (doc:Document {id: $doc_id})
                CREATE (chunk)-[:FROM_DOCUMENT]->(doc)
                """,
                chunk_id=chunk_id,
                doc_id=doc_id,
            )
        
        # Create entity nodes and mention relationships
        for entity_name, entity_type in entities:
            entity_id = f"{entity_type.lower()}_{entity_name.lower().replace(' ', '_')}"
            
            try:
                entity_query = f"""
                MERGE (entity:{entity_type} {{name: $name}})
                ON CREATE SET entity.id = $entity_id, entity.created_at = datetime()
                RETURN entity.id as id
                """
                
                with self.driver.session() as session:
                    result = session.run(
                        entity_query,
                        entity_id=entity_id,
                        name=entity_name,
                    )
                    record = result.single()
                
                # Create mention relationship
                mention_query = """
                MATCH (entity {id: $entity_id})
                MATCH (chunk:Chunk {id: $chunk_id})
                CREATE (entity)-[:MENTIONED_IN]->(chunk)
                """
                
                with self.driver.session() as session:
                    session.run(
                        mention_query,
                        entity_id=record["id"],
                        chunk_id=chunk_id,
                    )
                
                created_entities.append({
                    "id": record["id"],
                    "name": entity_name,
                    "type": entity_type,
                })
            except Exception as e:
                logger.warning(f"Failed to extract entity {entity_name}: {e}")
        
        return created_entities

    def get_entity_neighbors(
        self,
        entity_id: str,
        relationship_type: Optional[str] = None,
        depth: int = 1,
    ) -> List[Dict[str, Any]]:
        """Get neighboring entities in the knowledge graph.
        
        Args:
            entity_id: Entity identifier
            relationship_type: Filter by relationship type
            depth: Traversal depth
            
        Returns:
            List of neighboring entities and relationships
        """
        if relationship_type:
            query = f"""
            MATCH (entity {{id: $entity_id}})-[:{relationship_type}*1..{depth}]-(neighbor)
            RETURN neighbor.id as id, neighbor.name as name, labels(neighbor) as types
            """
        else:
            query = f"""
            MATCH (entity {{id: $entity_id}})-[*1..{depth}]-(neighbor)
            RETURN neighbor.id as id, neighbor.name as name, labels(neighbor) as types
            """
        
        with self.driver.session() as session:
            result = session.run(query, entity_id=entity_id)
            return [
                {
                    "id": record["id"],
                    "name": record.get("name"),
                    "types": record["types"],
                }
                for record in result
            ]

    def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_length: int = 5,
    ) -> List[List[Dict[str, Any]]]:
        """Find relationship paths between two entities.
        
        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            max_length: Maximum path length
            
        Returns:
            List of paths (each path is list of node dictionaries)
        """
        query = f"""
        MATCH paths = (source {{id: $source_id}}) 
            -[*1..{max_length}]- (target {{id: $target_id}})
        RETURN paths
        LIMIT 10
        """
        
        with self.driver.session() as session:
            result = session.run(query, source_id=source_id, target_id=target_id)
            paths = []
            for record in result:
                path = record["paths"]
                node_list = []
                for node in path.nodes:
                    node_list.append({
                        "id": node.get("id"),
                        "name": node.get("name"),
                        "types": list(node.labels),
                    })
                paths.append(node_list)
        
        return paths

    def get_concept_clusters(
        self,
        min_connections: int = 2,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get clusters of related concepts.
        
        Args:
            min_connections: Minimum entity connections for a cluster
            limit: Maximum clusters to return
            
        Returns:
            List of concept clusters
        """
        query = """
        MATCH (entity)-[rel]-(connected)
        WITH entity, count(rel) as degree, collect(distinct connected.name) as neighbors
        WHERE degree >= $min_connections
        RETURN entity.id as id, entity.name as name, degree, neighbors
        ORDER BY degree DESC
        LIMIT $limit
        """
        
        with self.driver.session() as session:
            result = session.run(query, min_connections=min_connections, limit=limit)
            clusters = [
                {
                    "entity_id": record["id"],
                    "entity_name": record["name"],
                    "connections": record["degree"],
                    "neighbors": record["neighbors"],
                }
                for record in result
            ]
        
        return clusters

    def get_graph_stats(self) -> Dict[str, Any]:
        """Get knowledge graph statistics.
        
        Returns:
            Graph metrics
        """
        stats = {}
        
        queries = {
            "total_nodes": "MATCH (n) RETURN count(n) as count",
            "total_relationships": "MATCH ()-[r]->() RETURN count(r) as count",
            "document_count": "MATCH (d:Document) RETURN count(d) as count",
            "entity_count": "MATCH (e) WHERE any(l in labels(e) WHERE l != 'Document' AND l != 'Chunk') RETURN count(e) as count",
            "chunk_count": "MATCH (c:Chunk) RETURN count(c) as count",
        }
        
        with self.driver.session() as session:
            for key, query in queries.items():
                result = session.run(query)
                record = result.single()
                stats[key] = record["count"] if record else 0
        
        return stats

    def close(self):
        """Close Neo4j driver."""
        self.driver.close()
        logger.info("Neo4j connection closed")


def init_neo4j_graph(
    uri: str = "bolt://localhost:7687",
    username: str = "neo4j",
    password: str = "password",
) -> Neo4jGraphStore:
    """Initialize Neo4j graph store.
    
    Args:
        uri: Neo4j connection URI
        username: Neo4j username
        password: Neo4j password
        
    Returns:
        Neo4jGraphStore instance
    """
    return Neo4jGraphStore(uri, username, password)
