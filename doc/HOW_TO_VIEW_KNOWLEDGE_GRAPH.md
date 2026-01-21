# How to View the Knowledge Graph

**Status**: Phase 5 (Knowledge Graph) ✅ Complete
**Visualization Options**: 3+ methods available

---

## 🎯 Quick Answer

There are **3 ways** to view your knowledge graph:

1. **Neo4j Browser** (Interactive UI) - Best for exploration
2. **Python API** (Programmatic) - Best for analysis
3. **Export & Visualize** (Mermaid/Graphviz) - Best for sharing

---

## 1️⃣ Neo4j Browser (Easiest & Most Interactive)

### Prerequisites
- ✅ Neo4j running on `bolt://localhost:7687`
- ✅ Neo4j Browser accessible at `http://localhost:7474`

### Access Neo4j Browser
```bash
# Open in browser
open http://localhost:7474

# Or navigate to
http://localhost:7474/browser/
```

### Login
- **Username**: neo4j
- **Password**: password (or your configured password)

### Explore the Graph

**View All Entities & Relationships**
```cypher
MATCH (n)-[r]->(m)
RETURN n, r, m
LIMIT 50
```

**View Entity Types Distribution**
```cypher
MATCH (n)
WHERE any(l in labels(n) WHERE l != 'Document' AND l != 'Chunk')
RETURN labels(n) as entity_type, count(n) as count
```

**View Top Entities (by connections)**
```cypher
MATCH (n)-[rel]-(connected)
WITH n, count(rel) as degree
WHERE degree > 0
RETURN n.name, degree
ORDER BY degree DESC
LIMIT 20
```

**View Relationships**
```cypher
MATCH (n)-[r]->(m)
RETURN type(r) as relationship_type, count(r) as count
```

**Find Entity by Name**
```cypher
MATCH (n)
WHERE n.name CONTAINS "machine learning"
RETURN n, [(n)-[r]->(m) | {rel: type(r), target: m.name}] as connections
```

**View Connected Entities (1-hop from entity)**
```cypher
MATCH (source {name: "entity name"})-[r]-(target)
RETURN source, r, target
```

**View Connected Entities (2-hops)**
```cypher
MATCH (source {name: "entity name"})-[r1]-(middle)-[r2]-(target)
RETURN source, r1, middle, r2, target
LIMIT 30
```

---

## 2️⃣ Python API (Programmatic Access)

### Basic Usage

#### Initialize
```python
from src.storage.neo4j_graph import Neo4jGraphStore

graph = Neo4jGraphStore(
    uri="bolt://localhost:7687",
    username="neo4j",
    password="password"
)
```

#### View Graph Statistics
```python
stats = graph.get_graph_stats()
print("Knowledge Graph Statistics:")
print(f"  Total Nodes: {stats['total_nodes']}")
print(f"  Total Relationships: {stats['total_relationships']}")
print(f"  Documents: {stats['document_count']}")
print(f"  Entities: {stats['entity_count']}")
print(f"  Chunks: {stats['chunk_count']}")
```

#### Search Entities
```python
# Find specific entity
entity_id = "entity-12345"
context = graph.get_entity_context(entity_id)
print(f"Entity: {context['name']}")
print(f"Type: {context['type']}")
print(f"Relationships: {context['relationships']}")
```

#### Find Highly Connected Entities (Hubs)
```python
clusters = graph.get_entity_clusters(min_connections=5)
for cluster in clusters[:10]:
    print(f"{cluster['entity_name']}: {cluster['connections']} connections")
    print(f"  Connected to: {', '.join(cluster['neighbors'][:5])}")
```

#### Custom Cypher Query
```python
query = """
MATCH (n)-[r]->(m)
WHERE n.type = 'PERSON'
RETURN n.name, type(r), m.name
LIMIT 20
"""

with graph.driver.session() as session:
    results = session.run(query)
    for record in results:
        print(f"{record['n.name']} --{record['type(r)']}-> {record['m.name']}")
```

### Advanced: Export to JSON
```python
import json

def export_graph_to_json(graph, output_file="graph.json"):
    """Export knowledge graph to JSON."""
    
    # Get all entities and relationships
    query = """
    MATCH (n)-[r]->(m)
    RETURN {
        source: {
            id: n.id,
            name: n.name,
            type: labels(n)
        },
        relationship: type(r),
        target: {
            id: m.id,
            name: m.name,
            type: labels(m)
        }
    } as connection
    """
    
    connections = []
    with graph.driver.session() as session:
        results = session.run(query)
        for record in results:
            connections.append(record['connection'])
    
    with open(output_file, 'w') as f:
        json.dump(connections, f, indent=2)
    
    print(f"Exported {len(connections)} connections to {output_file}")

export_graph_to_json(graph)
```

---

## 3️⃣ Export & Visualize (Mermaid/Graphviz)

### Option A: Mermaid (Best for Web Display)

#### Python Script
```python
def export_graph_to_mermaid(graph, output_file="graph.md", limit=30):
    """Export knowledge graph to Mermaid format."""
    
    query = f"""
    MATCH (n)-[r]->(m)
    RETURN n.name, type(r), m.name
    LIMIT {limit}
    """
    
    mermaid_lines = ["graph TD"]
    
    with graph.driver.session() as session:
        results = session.run(query)
        for record in results:
            source = record['n.name'].replace('"', '\\"')
            rel = record['type(r)']
            target = record['m.name'].replace('"', '\\"')
            
            # Create unique node IDs
            source_id = source.replace(' ', '_')
            target_id = target.replace(' ', '_')
            
            mermaid_lines.append(f'    {source_id}["{source}"]')
            mermaid_lines.append(f'    {target_id}["{target}"]')
            mermaid_lines.append(f'    {source_id} -->|{rel}| {target_id}')
    
    mermaid_code = '\n'.join(mermaid_lines)
    
    # Write to file
    with open(output_file, 'w') as f:
        f.write(f"```mermaid\n{mermaid_code}\n```")
    
    print(f"Exported Mermaid graph to {output_file}")
    return mermaid_code

# Use it
graph = Neo4jGraphStore(...)
mermaid = export_graph_to_mermaid(graph, limit=20)
```

#### View Mermaid
- Copy output to: https://mermaid.live
- Or include in markdown file and view on GitHub

### Option B: Graphviz (Best for Complex Graphs)

#### Python Script
```python
def export_graph_to_graphviz(graph, output_file="graph", format="svg", limit=30):
    """Export knowledge graph to Graphviz format."""
    
    try:
        import graphviz
    except ImportError:
        print("Install graphviz: pip install graphviz")
        return
    
    query = f"""
    MATCH (n)-[r]->(m)
    RETURN n.name, n.type, type(r), m.name, m.type
    LIMIT {limit}
    """
    
    dot = graphviz.Digraph()
    dot.attr(rankdir='LR', size='12,8')
    
    seen_nodes = set()
    
    with graph.driver.session() as session:
        results = session.run(query)
        for record in results:
            source = record['n.name']
            target = record['m.name']
            rel = record['type(r)']
            
            # Add nodes
            if source not in seen_nodes:
                dot.node(source, label=source, shape='ellipse')
                seen_nodes.add(source)
            
            if target not in seen_nodes:
                dot.node(target, label=target, shape='ellipse')
                seen_nodes.add(target)
            
            # Add edge
            dot.edge(source, target, label=rel)
    
    # Save and render
    dot.render(output_file, format=format, cleanup=True)
    print(f"Generated {output_file}.{format}")

# Use it
graph = Neo4jGraphStore(...)
export_graph_to_graphviz(graph, limit=25)
```

---

## 🔍 Common Queries

### View Complete Subgraph Around Entity
```cypher
MATCH (center {name: "Python"})-[r1]-(connected1)-[r2]-(connected2)
RETURN center, r1, connected1, r2, connected2
LIMIT 100
```

### Find Path Between Two Entities
```cypher
MATCH path = shortestPath(
    (start {name: "entity1"})-[*]-(end {name: "entity2"})
)
RETURN path
```

### View All Relationship Types
```cypher
MATCH ()-[r]->()
RETURN DISTINCT type(r) as relationship_type, count(r) as frequency
ORDER BY frequency DESC
```

### Find Isolated Entities
```cypher
MATCH (n)
WHERE NOT (n)--()
RETURN n.name, labels(n)
```

### View Entities by Type
```cypher
MATCH (n:PERSON)
RETURN n.name, n.id
LIMIT 20
```

---

## 📊 Accessing via Agent

The agent can also help explore the graph:

```python
from src.agent.agent import RAGAgent
from src.storage import StorageOrchestrator

storage = StorageOrchestrator(...)
agent = RAGAgent(storage)

# Query the graph
result = await agent.query("What entities are in the knowledge graph?")
print(result['answer'])

# Direct graph search
results = await agent.tools.graph_search(
    "machine learning",
    entity_types=["TECHNOLOGY", "CONCEPT"]
)
print(f"Found {results.entity_count} entities")
for entity in results.entities:
    print(f"  - {entity['name']} ({entity['type']})")
```

---

## 🎨 Visualization Tools

### Web-Based
1. **Neo4j Browser** (Built-in)
   - Best for: Interactive exploration
   - Access: http://localhost:7474

2. **Mermaid Live** (Online)
   - Best for: Creating diagrams
   - URL: https://mermaid.live

3. **Graphviz Online** (Online)
   - Best for: Complex graph visualization
   - URL: https://dreampuf.github.io/GraphvizOnline/

### Local Tools
1. **Graphviz** (Desktop)
   - Command: `dot -Tsvg graph.dot -o graph.svg`
   - Best for: High-quality outputs

2. **yEd** (Desktop)
   - Free graph editor
   - Import GraphML format

---

## 📝 Example: Complete Visualization Script

```python
#!/usr/bin/env python3
"""Complete script to visualize knowledge graph."""

from src.storage.neo4j_graph import Neo4jGraphStore
import json

# Initialize
graph = Neo4jGraphStore(
    uri="bolt://localhost:7687",
    username="neo4j",
    password="password"
)

# 1. Print statistics
print("=" * 50)
print("KNOWLEDGE GRAPH STATISTICS")
print("=" * 50)
stats = graph.get_graph_stats()
for key, value in stats.items():
    print(f"{key}: {value}")

# 2. Find hub entities
print("\n" + "=" * 50)
print("TOP CONNECTED ENTITIES (HUBS)")
print("=" * 50)
hubs = graph.get_entity_clusters(min_connections=5, limit=10)
for hub in hubs:
    print(f"{hub['entity_name']}: {hub['connections']} connections")

# 3. Export as JSON
print("\n" + "=" * 50)
print("EXPORTING GRAPH")
print("=" * 50)

query = """
MATCH (n)-[r]->(m)
RETURN {
    source: {id: n.id, name: n.name},
    relationship: type(r),
    target: {id: m.id, name: m.name}
} as connection
LIMIT 100
"""

connections = []
with graph.driver.session() as session:
    results = session.run(query)
    for record in results:
        connections.append(record['connection'])

with open("graph_export.json", "w") as f:
    json.dump(connections, f, indent=2)

print(f"Exported {len(connections)} relationships to graph_export.json")

# Close
graph.close()
print("\nDone!")
```

---

## 🚀 Quick Start Steps

1. **Start Neo4j** (if not running)
   ```bash
   # Docker
   docker run --rm -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j
   
   # Or local installation
   neo4j start
   ```

2. **Open Neo4j Browser**
   ```bash
   open http://localhost:7474
   ```

3. **Run a Query**
   ```cypher
   MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50
   ```

4. **Export Graph** (Optional)
   ```bash
   python export_graph.py
   ```

---

## 📖 Documentation References

- **Implementation**: `doc/KNOWLEDGE_GRAPH_IMPLEMENTATION.md`
- **Neo4j Driver**: `src/storage/neo4j_graph.py`
- **Agent Access**: `src/agent/agent.py` (graph_search tool)
- **Examples**: `doc/AGENT_EXAMPLES.py` (search examples)

---

## ❓ FAQ

**Q: The graph is empty. Where are my entities?**  
A: Entities are created during ingestion (Phase 4). Run the ingestion pipeline first to populate the graph.

**Q: How do I query Neo4j from Python?**  
A: Use `graph.driver.session()` and run Cypher queries (see examples above).

**Q: Can I see the graph visually?**  
A: Yes! Use Neo4j Browser UI or export to Mermaid/Graphviz (see Option 3).

**Q: How do I find a specific entity?**  
A: Use the Cypher query: `MATCH (n {name: "your entity"}) RETURN n`

**Q: What's the easiest way to start?**  
A: Open Neo4j Browser and run: `MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50`

---

## 🎓 Next Steps

1. Explore the graph in Neo4j Browser
2. Run the visualization scripts
3. Use the agent to query relationships
4. Export graphs for sharing
5. Continue to Phase 7 (API Layer)

---

**Last Updated**: January 21, 2026  
**Phase**: 5 (Knowledge Graph) ✅ Complete
