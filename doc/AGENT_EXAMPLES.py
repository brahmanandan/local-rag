"""
Phase 6: Agent Layer - Usage Examples

Demonstrates how to use the RAGAgent with different tools and configurations.
"""

import asyncio
import json
from datetime import datetime
from src.agent.agent import RAGAgent
from src.storage import StorageOrchestrator


# ============================================================================
# Example 1: Basic Query with Default Settings
# ============================================================================

async def example_basic_query():
    """Simple query using default agent setup."""
    print("\n" + "="*70)
    print("Example 1: Basic Query")
    print("="*70)
    
    # Initialize storage and agent
    storage = StorageOrchestrator(
        postgres_config={
            "host": "localhost",
            "port": 5432,
            "user": "rag_user",
            "password": "rag_password",
            "database": "rag_db"
        },
        neo4j_config={
            "uri": "bolt://localhost:7687",
            "user": "neo4j",
            "password": "password"
        }
    )
    
    agent = RAGAgent(storage, llm_provider="ollama")
    
    # Query
    result = await agent.query("What are the main topics in the knowledge base?")
    
    print(f"\nQuery: {result['query']}")
    print(f"Answer: {result['answer']}")
    print(f"Duration: {result['duration_ms']:.1f}ms")
    print(f"Tool calls: {len(result['tool_usage'].tool_calls)}")


# ============================================================================
# Example 2: Vector Search for Semantic Similarity
# ============================================================================

async def example_vector_search():
    """Search using vector similarity."""
    print("\n" + "="*70)
    print("Example 2: Vector Search")
    print("="*70)
    
    storage = StorageOrchestrator(...)
    agent = RAGAgent(storage)
    
    # Semantic similarity search
    results = await agent.tools.vector_search(
        query="neural networks and deep learning",
        limit=5,
        threshold=0.7
    )
    
    print(f"\nSearch Query: {results.query}")
    print(f"Results Found: {results.count}")
    
    for i, result in enumerate(results.results, 1):
        print(f"\n{i}. Score: {result.score:.3f}")
        print(f"   Text: {result.text[:200]}...")
        print(f"   Source: {result.source}")


# ============================================================================
# Example 3: Graph Search for Entities and Relationships
# ============================================================================

async def example_graph_search():
    """Search using knowledge graph."""
    print("\n" + "="*70)
    print("Example 3: Graph Search")
    print("="*70)
    
    storage = StorageOrchestrator(...)
    agent = RAGAgent(storage)
    
    # Entity and relationship search
    results = await agent.tools.graph_search(
        query="machine learning",
        entity_types=["TECHNOLOGY", "CONCEPT"],
        relationship_types=["RELATES_TO", "PART_OF"]
    )
    
    print(f"\nSearch Query: {results.query}")
    print(f"Entities Found: {results.entity_count}")
    print(f"Relationships Found: {results.relationship_count}")
    
    print("\nEntities:")
    for entity in results.entities[:5]:
        print(f"  - {entity['name']} ({entity['type']})")
    
    print("\nSample Relationships:")
    for rel in results.relationships[:3]:
        print(f"  - {rel['source']} --{rel['type']}--> {rel['target']}")


# ============================================================================
# Example 4: Hybrid Search (Vector + Graph)
# ============================================================================

async def example_hybrid_search():
    """Combine vector and graph search."""
    print("\n" + "="*70)
    print("Example 4: Hybrid Search")
    print("="*70)
    
    storage = StorageOrchestrator(...)
    agent = RAGAgent(storage)
    
    # Hybrid search with weighted results
    results = await agent.tools.hybrid_search(
        query="what technologies are used for NLP?",
        vector_weight=0.6,    # 60% semantic weight
        graph_weight=0.4,     # 40% entity weight
        limit=10
    )
    
    print(f"\nSearch Query: {results.query}")
    print(f"Vector Results: {results.vector_count}")
    print(f"Graph Results: {results.graph_count}")
    print(f"Merged Results: {results.total_count}")
    
    print("\nTop Results (merged):")
    for i, result in enumerate(results.merged_results[:5], 1):
        print(f"{i}. Score: {result.score:.3f} | {result.text[:150]}...")


# ============================================================================
# Example 5: Document Retrieval
# ============================================================================

async def example_document_retrieval():
    """Get full document by ID."""
    print("\n" + "="*70)
    print("Example 5: Document Retrieval")
    print("="*70)
    
    storage = StorageOrchestrator(...)
    agent = RAGAgent(storage)
    
    # Retrieve document
    doc = await agent.tools.retrieve_document(document_id="doc-12345")
    
    print(f"\nDocument ID: {doc.document_id}")
    print(f"Title: {doc.title}")
    print(f"Chunks: {doc.chunk_count}")
    print(f"Metadata: {json.dumps(doc.metadata, indent=2)}")
    
    print(f"\nContent Preview (first 500 chars):")
    print(doc.content[:500])
    print("...")


# ============================================================================
# Example 6: Entity Context and Relationships
# ============================================================================

async def example_entity_context():
    """Get entity relationships."""
    print("\n" + "="*70)
    print("Example 6: Entity Context")
    print("="*70)
    
    storage = StorageOrchestrator(...)
    agent = RAGAgent(storage)
    
    # Get entity context
    context = await agent.tools.get_entity_context(
        entity_id="entity-42",
        depth=2
    )
    
    print(f"\nEntity: {context['name']}")
    print(f"Type: {context['type']}")
    print(f"Properties: {json.dumps(context['properties'], indent=2)}")
    
    print(f"\nRelationships ({len(context['relationships'])}):")
    for rel in context['relationships']:
        print(f"  - {rel['type']}: {rel['target']} ({rel['target_type']})")


# ============================================================================
# Example 7: Multi-Tool Query Workflow
# ============================================================================

async def example_multi_tool_query():
    """Complex query using multiple tools."""
    print("\n" + "="*70)
    print("Example 7: Multi-Tool Query Workflow")
    print("="*70)
    
    storage = StorageOrchestrator(...)
    agent = RAGAgent(storage)
    
    # Complex query
    query = "Find all documents about machine learning and show their relationships"
    result = await agent.query(query)
    
    print(f"\nQuery: {query}")
    print(f"Answer: {result['answer']}\n")
    
    # Show tool usage
    log = result['tool_usage']
    print(f"Tool Calls ({len(log.tool_calls)}):")
    for call in log.tool_calls:
        status = "✓" if call.success else "✗"
        print(f"  {status} {call.tool_name}: {call.duration_ms:.1f}ms")
        if call.error:
            print(f"    Error: {call.error}")
    
    print(f"\nTotal Duration: {log.total_duration_ms:.1f}ms")


# ============================================================================
# Example 8: Tool Usage Logging and Analysis
# ============================================================================

async def example_tool_usage_logging():
    """Analyze tool usage across queries."""
    print("\n" + "="*70)
    print("Example 8: Tool Usage Logging")
    print("="*70)
    
    storage = StorageOrchestrator(...)
    agent = RAGAgent(storage)
    
    # Run multiple queries
    queries = [
        "What is deep learning?",
        "Show me papers on NLP",
        "What technologies use transformers?"
    ]
    
    for query in queries:
        await agent.query(query)
    
    # Get usage logs
    logs = agent.get_tool_usage_logs()
    
    print(f"\nTotal Queries: {len(logs)}")
    
    # Aggregate statistics
    total_tool_calls = sum(len(log.tool_calls) for log in logs)
    total_duration = sum(log.total_duration_ms for log in logs)
    
    print(f"Total Tool Calls: {total_tool_calls}")
    print(f"Total Duration: {total_duration:.1f}ms")
    print(f"Average Query Time: {total_duration / len(logs):.1f}ms")
    
    # Tool usage breakdown
    tool_stats = {}
    for log in logs:
        for call in log.tool_calls:
            if call.tool_name not in tool_stats:
                tool_stats[call.tool_name] = {
                    "count": 0,
                    "total_time": 0,
                    "errors": 0
                }
            tool_stats[call.tool_name]["count"] += 1
            tool_stats[call.tool_name]["total_time"] += call.duration_ms
            if not call.success:
                tool_stats[call.tool_name]["errors"] += 1
    
    print("\nTool Statistics:")
    for tool_name, stats in tool_stats.items():
        avg_time = stats["total_time"] / stats["count"] if stats["count"] > 0 else 0
        print(f"  {tool_name}:")
        print(f"    Calls: {stats['count']}")
        print(f"    Avg Time: {avg_time:.1f}ms")
        print(f"    Errors: {stats['errors']}")
    
    # Export logs
    agent.export_tool_usage("tool_usage_report.json")
    print("\n✓ Tool usage exported to tool_usage_report.json")


# ============================================================================
# Example 9: Custom System Prompt
# ============================================================================

async def example_custom_prompt():
    """Use custom system prompt."""
    print("\n" + "="*70)
    print("Example 9: Custom System Prompt")
    print("="*70)
    
    storage = StorageOrchestrator(...)
    
    custom_prompt = """
You are a specialized AI assistant for analyzing research papers.

Your role:
- Find and analyze academic content
- Identify key findings and methodologies
- Connect related research through citation graphs
- Provide structured summaries

Tools available:
- vector_search: Find papers by topic
- graph_search: Find citations and author relationships
- hybrid_search: Combine relevance and citation data
- retrieve_document: Get full paper content

Always cite sources and provide detailed explanations.
"""
    
    agent = RAGAgent(
        storage,
        system_prompt=custom_prompt,
        llm_provider="ollama"
    )
    
    # Query with custom prompt
    result = await agent.query("Analyze recent papers on transformer architectures")
    print(f"\nQuery: {result['query']}")
    print(f"Answer: {result['answer']}")


# ============================================================================
# Example 10: Error Handling and Fallbacks
# ============================================================================

async def example_error_handling():
    """Handle errors gracefully."""
    print("\n" + "="*70)
    print("Example 10: Error Handling")
    print("="*70)
    
    storage = StorageOrchestrator(...)
    agent = RAGAgent(storage)
    
    try:
        # This query might fail if the tool is unavailable
        result = await agent.query("Query with potential issues")
        print(f"Query succeeded: {result['answer']}")
        
    except Exception as e:
        print(f"Error: {type(e).__name__}: {str(e)}")
        # Implement fallback logic
        print("→ Falling back to simpler search...")
        
        try:
            # Simpler fallback
            results = await agent.tools.vector_search("fallback query")
            print(f"Fallback succeeded: {results.count} results found")
        except Exception as fallback_error:
            print(f"Fallback also failed: {fallback_error}")


# ============================================================================
# Example 11: Batch Processing
# ============================================================================

async def example_batch_processing():
    """Process multiple queries efficiently."""
    print("\n" + "="*70)
    print("Example 11: Batch Processing")
    print("="*70)
    
    storage = StorageOrchestrator(...)
    agent = RAGAgent(storage)
    
    queries = [
        "What is machine learning?",
        "Explain deep learning",
        "How do neural networks work?",
        "What are transformers?",
        "Define NLP"
    ]
    
    results = []
    
    print(f"\nProcessing {len(queries)} queries...")
    
    for i, query in enumerate(queries, 1):
        print(f"  {i}/{len(queries)}: {query[:40]}...")
        result = await agent.query(query)
        results.append(result)
    
    # Summary
    total_duration = sum(r['duration_ms'] for r in results)
    print(f"\n✓ Completed {len(results)} queries")
    print(f"Total Time: {total_duration:.1f}ms")
    print(f"Average Time: {total_duration / len(results):.1f}ms")


# ============================================================================
# Example 12: Configuration and Initialization
# ============================================================================

async def example_configuration():
    """Various agent configurations."""
    print("\n" + "="*70)
    print("Example 12: Configuration Options")
    print("="*70)
    
    # Configuration 1: Ollama local
    config_ollama = {
        "llm_provider": "ollama",
        "llm_model": "llama3.2:latest",
        "embedding_model": "nomic-embed-text"
    }
    
    # Configuration 2: OpenRouter (fallback)
    config_openrouter = {
        "llm_provider": "openrouter",
        "llm_model": "meta-llama/llama-2-70b",
        "api_key": "your-openrouter-key"
    }
    
    # Configuration 3: Gemini
    config_gemini = {
        "llm_provider": "gemini",
        "llm_model": "gemini-2.0-flash",
        "api_key": "your-gemini-key"
    }
    
    print("\nExample Configurations:")
    print("1. Ollama (Local):")
    print(f"   {json.dumps(config_ollama, indent=2)}")
    print("\n2. OpenRouter (Fallback):")
    print(f"   {json.dumps(config_openrouter, indent=2)}")
    print("\n3. Gemini (Fallback):")
    print(f"   {json.dumps(config_gemini, indent=2)}")


# ============================================================================
# Main Runner
# ============================================================================

async def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("Phase 6: Agent Layer - Usage Examples")
    print("="*70)
    
    # Note: These are pseudocode examples
    # In practice, you'll have real storage configured
    
    examples = [
        ("Basic Query", example_basic_query),
        ("Vector Search", example_vector_search),
        ("Graph Search", example_graph_search),
        ("Hybrid Search", example_hybrid_search),
        ("Document Retrieval", example_document_retrieval),
        ("Entity Context", example_entity_context),
        ("Multi-Tool Query", example_multi_tool_query),
        ("Tool Usage Logging", example_tool_usage_logging),
        ("Custom Prompt", example_custom_prompt),
        ("Error Handling", example_error_handling),
        ("Batch Processing", example_batch_processing),
        ("Configuration", example_configuration),
    ]
    
    print("\nAvailable Examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    
    print("\nTo run specific examples:")
    print("  python examples_agent_phase6.py")
    print("\nOr import and run individually:")
    print("  from examples_agent_phase6 import example_vector_search")
    print("  await example_vector_search()")


if __name__ == "__main__":
    asyncio.run(main())
