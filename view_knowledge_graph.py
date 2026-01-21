#!/usr/bin/env python3
"""
Quick script to view knowledge graph statistics and explore it.
Run this to get a quick overview of your knowledge graph.
"""

from src.storage.neo4j_graph import Neo4jGraphStore
import json
from pathlib import Path


def view_graph_stats():
    """View basic graph statistics."""
    try:
        graph = Neo4jGraphStore(
            uri="bolt://localhost:7687",
            username="neo4j",
            password="password"
        )
    except Exception as e:
        print(f"❌ Failed to connect to Neo4j: {e}")
        print("\nMake sure Neo4j is running:")
        print("  docker run --rm -p 7474:7474 -p 7687:7687 \\")
        print("    -e NEO4J_AUTH=neo4j/password neo4j")
        return

    print("\n" + "="*60)
    print("KNOWLEDGE GRAPH OVERVIEW")
    print("="*60)
    
    stats = graph.get_graph_stats()
    print(f"\n📊 Statistics:")
    print(f"  • Total Nodes: {stats.get('total_nodes', 0)}")
    print(f"  • Total Relationships: {stats.get('total_relationships', 0)}")
    print(f"  • Documents: {stats.get('document_count', 0)}")
    print(f"  • Entities: {stats.get('entity_count', 0)}")
    print(f"  • Chunks: {stats.get('chunk_count', 0)}")
    
    # Get hub entities
    print(f"\n🌟 Top Connected Entities (Hubs):")
    try:
        hubs = graph.get_entity_clusters(min_connections=2, limit=10)
        if hubs:
            for i, hub in enumerate(hubs, 1):
                print(f"  {i}. {hub['entity_name']} - {hub['connections']} connections")
        else:
            print("  (No highly connected entities found)")
    except Exception as e:
        print(f"  (Could not fetch hubs: {e})")
    
    graph.close()
    
    print("\n" + "="*60)
    print("HOW TO VIEW THE GRAPH")
    print("="*60)
    print("""
1. 🌐 NEO4J BROWSER (Best for Interactive Exploration)
   → Open: http://localhost:7474
   → Login: neo4j / password
   → Try this query:
      MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50

2. 🐍 PYTHON API (Programmatic Access)
   → See: doc/HOW_TO_VIEW_KNOWLEDGE_GRAPH.md (Section 2)
   → Example:
      from src.storage.neo4j_graph import Neo4jGraphStore
      graph = Neo4jGraphStore(...)
      stats = graph.get_graph_stats()

3. 📊 EXPORT & VISUALIZE (Mermaid/Graphviz)
   → See: doc/HOW_TO_VIEW_KNOWLEDGE_GRAPH.md (Section 3)
   → Run: python scripts/export_graph.py

4. 🤖 AGENT ACCESS (Semantic Search)
   → Use RAGAgent.tools.graph_search()
   → Example:
      results = await agent.tools.graph_search("machine learning")

📖 Complete Guide: doc/HOW_TO_VIEW_KNOWLEDGE_GRAPH.md
    """)


if __name__ == "__main__":
    view_graph_stats()
