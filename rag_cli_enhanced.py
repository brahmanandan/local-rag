"""Enhanced Streamlit RAG Chat Interface with Storage Layer Integration.

Features:
- PostgreSQL-backed vector retrieval
- Neo4j knowledge graph traversal
- File metadata tracking
- Multi-source document retrieval
- Entity-aware search
"""

import os
os.environ['USER_AGENT'] = os.getenv("USER_AGENT", "rag-chatbot/1.0")

import asyncio
import streamlit as st
import yaml
import logging
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from langchain_community.vectorstores import FAISS
from utils import get_embeddings_model, get_llm_model

# Storage layer imports
from src.storage import StorageOrchestrator

# Load config
def load_config(config_path: str = 'config.yaml') -> Dict[str, Any]:
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

config = load_config()
INDEX_DIR = config['INDEX_DIR']


@st.cache_resource
def init_storage() -> Optional[StorageOrchestrator]:
    """Initialize storage orchestrator with streamlit caching."""
    try:
        storage = StorageOrchestrator(
            postgres_url=os.getenv(
                'DATABASE_URL',
                'postgresql://postgres:postgres@localhost:5432/rag_db'
            ),
            neo4j_uri=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            neo4j_user=os.getenv('NEO4J_USER', 'neo4j'),
            neo4j_password=os.getenv('NEO4J_PASSWORD', 'password'),
        )
        logger.info("Storage orchestrator initialized")
        return storage
    except Exception as e:
        logger.error(f"Failed to initialize storage: {e}")
        return None


@st.cache_resource
def load_chain_with_storage():
    """Load RAG chain with storage layer integration."""
    try:
        embeddings = get_embeddings_model()
        
        # Try to load FAISS index
        try:
            vectorstore = FAISS.load_local(INDEX_DIR, embeddings, allow_dangerous_deserialization=True)
            logger.info("Loaded FAISS index")
        except Exception as e:
            logger.warning(f"Could not load FAISS index: {e}")
            vectorstore = None
        
        # Get LLM
        llm = get_llm_model()
        
        # Initialize storage
        storage = init_storage()
        
        # Store references
        st.session_state.vectorstore = vectorstore
        st.session_state.llm = llm
        st.session_state.embeddings = embeddings
        st.session_state.storage = storage
        
        if vectorstore:
            retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})
            st.session_state.retriever = retriever
        
        # Build chain
        try:
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import StrOutputParser
            from langchain_core.runnables import RunnableLambda
            
            prompt = ChatPromptTemplate.from_template(
                "You are a helpful assistant that answers questions based on the provided context.\n\n"
                "Context: {context}\n\n"
                "Question: {input}\n\n"
                "Answer: "
            )
            
            def format_docs(docs):
                return "\n\n".join(doc.page_content for doc in docs)
            
            def get_input(x):
                return x["input"] if isinstance(x, dict) else x
            
            if vectorstore:
                chain = (
                    {
                        "context": RunnableLambda(get_input) | retriever | RunnableLambda(format_docs),
                        "input": RunnableLambda(get_input)
                    }
                    | prompt
                    | llm
                    | StrOutputParser()
                )
            else:
                # Fallback: just use LLM without retrieval
                chain = prompt | llm | StrOutputParser()
            
            logger.info("RAG chain loaded successfully")
            return chain
            
        except Exception as e:
            logger.error(f"Failed to build chain: {e}")
            raise
            
    except Exception as e:
        logger.error(f"Failed to load chain: {e}")
        st.error(f"Failed to load RAG system: {e}")
        return None


def get_postgres_results(query_embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
    """Search PostgreSQL for similar chunks."""
    storage = st.session_state.get('storage')
    if not storage:
        return []
    
    try:
        async def search():
            postgres = await storage.init_postgres()
            results = await postgres.similarity_search(
                embedding=query_embedding,
                limit=limit,
                threshold=0.0
            )
            return results
        
        # Run async function in event loop
        loop = asyncio.new_event_loop()
        results = loop.run_until_complete(search())
        loop.close()
        return results
        
    except Exception as e:
        logger.error(f"PostgreSQL search failed: {e}")
        return []


def get_entity_graph_context(entity_name: str) -> Optional[Dict[str, Any]]:
    """Get entity context from Neo4j knowledge graph."""
    storage = st.session_state.get('storage')
    if not storage:
        return None
    
    try:
        neo4j = storage.init_neo4j()
        
        # Find entity
        neighbors = neo4j.get_entity_neighbors(entity_name, depth=2)
        concepts = neo4j.get_concept_clusters(min_connections=1, limit=5)
        
        return {
            'entity': entity_name,
            'neighbors': neighbors,
            'concepts': concepts,
        }
    except Exception as e:
        logger.debug(f"Entity lookup failed: {e}")
        return None


def get_file_metadata(source: str) -> Optional[Dict[str, Any]]:
    """Get file metadata from SQLite."""
    storage = st.session_state.get('storage')
    if not storage:
        return None
    
    try:
        metadata = storage.init_metadata()
        stats = metadata.get_file_stats()
        return stats
    except Exception as e:
        logger.debug(f"Metadata lookup failed: {e}")
        return None


# Initialize session state
if "history" not in st.session_state:
    st.session_state.history = []

if "storage" not in st.session_state:
    st.session_state.storage = init_storage()

# Page config
st.set_page_config(
    page_title="RAG Chatbot with Knowledge Graph",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title and description
st.title("📚 RAG Chatbot with Knowledge Graph")
st.markdown("""
Advanced RAG system with:
- 🔍 Vector similarity search (PostgreSQL + pgvector)
- 🧠 Knowledge graph navigation (Neo4j)
- 📊 File metadata tracking (SQLite)
- 🤖 Multi-provider LLM support
""")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Storage backend status
    st.subheader("Storage Status")
    if st.session_state.storage:
        if st.button("Check Backend Health"):
            async def health_check():
                health = await st.session_state.storage.health_check()
                return health
            
            loop = asyncio.new_event_loop()
            health = loop.run_until_complete(health_check())
            loop.close()
            
            for backend, status in health.items():
                color = "🟢" if status['status'] == 'healthy' else "🔴"
                st.write(f"{color} {backend}: {status['status']}")
    else:
        st.warning("⚠️ Storage not initialized")
    
    # Search options
    st.subheader("Search Options")
    search_limit = st.slider("Max results", 1, 10, 5)
    use_postgres = st.checkbox("Search PostgreSQL", value=True)
    use_graph = st.checkbox("Use Neo4j graph", value=True)
    
    # File metadata
    st.subheader("📊 Index Statistics")
    file_stats = get_file_metadata("dummy")
    if file_stats:
        st.metric("Total Files", file_stats.get('total_files', 0))
        st.metric("Indexed", file_stats.get('indexed_files', 0))
        st.metric("Pending", file_stats.get('pending_files', 0))
        st.metric("Total Size", f"{file_stats.get('total_size_bytes', 0) / 1024 / 1024:.2f} MB")

# Main chat interface
col1, col2 = st.columns([3, 1])

with col1:
    question = st.text_input("Ask a question:", placeholder="What would you like to know?")

with col2:
    if st.button("🔍 Search", use_container_width=True):
        question = st.session_state.get('last_question', '')

# Load chain
chain = load_chain_with_storage()

if chain is None:
    st.error("❌ Failed to load RAG system")
    st.info("Please ensure:")
    st.info("1. Database backends are running (PostgreSQL, Neo4j)")
    st.info("2. API keys are configured")
    st.info("3. Document index exists (run `python main_async.py`)")
    st.stop()

# Process question
if question:
    st.session_state['last_question'] = question
    
    with st.spinner("🤔 Thinking..."):
        try:
            # Get embeddings for question
            embeddings = st.session_state.get('embeddings')
            query_embedding = embeddings.embed_query(question) if embeddings else None
            
            # Multi-source retrieval
            all_sources = []
            
            # 1. FAISS retrieval (existing)
            if st.session_state.get('retriever'):
                faiss_docs = st.session_state.retriever.invoke(question)
                all_sources.extend([('FAISS', doc) for doc in faiss_docs])
            
            # 2. PostgreSQL retrieval
            if use_postgres and query_embedding:
                pg_results = get_postgres_results(query_embedding, search_limit)
                all_sources.extend([('PostgreSQL', result) for result in pg_results])
            
            # 3. Neo4j entity search
            if use_graph and st.session_state.storage:
                entity_context = get_entity_graph_context(question)
                if entity_context:
                    all_sources.append(('Knowledge Graph', entity_context))
            
            # Build context from all sources
            context_parts = []
            for source_type, source_data in all_sources:
                if isinstance(source_data, dict):
                    # Neo4j result
                    context_parts.append(f"[{source_type}] {str(source_data)}")
                else:
                    # FAISS or PostgreSQL result
                    if hasattr(source_data, 'page_content'):
                        content = source_data.page_content
                    else:
                        content = source_data.get('text', str(source_data))
                    context_parts.append(f"[{source_type}] {content[:500]}")
            
            combined_context = "\n\n".join(context_parts[:10])  # Limit context
            
            # Query chain
            answer = chain.invoke({"input": question, "context": combined_context})
            
            # Display answer
            st.success("✅ Answer Generated")
            st.markdown("### Answer")
            st.write(answer)
            
            # Sources
            st.markdown("### Sources")
            with st.expander(f"View {len(all_sources)} sources", expanded=False):
                for i, (source_type, source_data) in enumerate(all_sources, 1):
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        st.badge(source_type, "info")
                    with col2:
                        if isinstance(source_data, dict):
                            st.write(source_data)
                        elif hasattr(source_data, 'metadata'):
                            st.write(f"📄 **{source_data.metadata.get('source', 'Unknown')}**")
                            st.caption(source_data.page_content[:300])
                        else:
                            st.write(source_data)
            
            # Add to history
            st.session_state.history.append((question, answer))
            
        except Exception as e:
            st.error(f"❌ Error: {e}")
            logger.exception("Error processing question")
            st.info("Please check your configuration and try again")

# History
if st.session_state.history:
    st.markdown("---")
    st.subheader("📜 Conversation History")
    for i, (q, a) in enumerate(reversed(st.session_state.history[-5:]), 1):
        with st.expander(f"Q{i}: {q[:50]}..."):
            st.write(f"**Q:** {q}")
            st.write(f"**A:** {a}")
