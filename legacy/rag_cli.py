import os
# Set USER_AGENT environment variable early to avoid warnings
os.environ['USER_AGENT'] = os.getenv("USER_AGENT", "rag-chatbot/1.0")

import streamlit as st
import yaml
import logging
from dotenv import load_dotenv

# Load environment variables before importing local modules that may read them
load_dotenv()

from langchain_community.vectorstores import FAISS
from utils import get_embeddings_model, get_llm_model

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load config from YAML file
def load_config(config_path='config.yaml'):
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

config = load_config()
INDEX_DIR = config['INDEX_DIR']


@st.cache_resource
def load_chain():
    """Load the RAG chain with modern LangChain API."""
    try:
        embeddings = get_embeddings_model()
        vectorstore = FAISS.load_local(INDEX_DIR, embeddings, allow_dangerous_deserialization=True)
        
        # Get LLM with fallback options
        llm = get_llm_model()

        retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})
        
        # Store vectorstore in session for document retrieval if needed
        if not hasattr(st.session_state, 'vectorstore'):
            st.session_state.vectorstore = vectorstore
        
        # Store retriever in session
        if not hasattr(st.session_state, 'retriever'):
            st.session_state.retriever = retriever
        
        # Use modern LangChain API - build chain with available components
        try:
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import StrOutputParser
            from langchain_core.runnables import RunnablePassthrough, RunnableLambda
            
            # Create prompt template
            prompt = ChatPromptTemplate.from_template(
                "You are a helpful assistant that answers questions based on the provided context.\n\n"
                "Context: {context}\n\n"
                "Question: {input}\n\n"
                "Answer based on the context above. If the context doesn't contain the answer, say so."
            )
            
            # Format documents helper
            def format_docs(docs):
                return "\n\n".join(doc.page_content for doc in docs)
            
            # Extract just the input string from the dict
            def get_input(x):
                return x["input"] if isinstance(x, dict) else x
            
            # Build chain manually with available components
            chain = (
                {
                    "context": RunnableLambda(get_input) | retriever | RunnableLambda(format_docs),
                    "input": RunnableLambda(get_input)
                }
                | prompt
                | llm
                | StrOutputParser()
            )
            
            logger.info("Successfully loaded RAG chain with core API")
            return chain
        except Exception as e:
            logger.error(f"Failed to load chain: {e}")
            raise
    except Exception as e:
        st.error(f"Failed to load the RAG chain: {e}")
        st.info("Please check your API keys and ensure the index has been created.")
        st.info("Supported providers: OpenAI, Perplexity, Google Gemini, Ollama, llama.cpp, HuggingFace")
        return None

chain = load_chain()

st.title("📚 RAG Course Chatbot")

if chain is None:
    st.error("❌ Failed to load the RAG system. Please check your configuration and try again.")
    st.info("Make sure you have:")
    st.info("1. Set up your API keys in the environment (OpenAI, Perplexity, or Google)")
    st.info("2. Or install Ollama: https://ollama.ai (for local LLMs)")
    st.info("3. Or set LLAMA_CPP_MODEL_PATH for llama.cpp models")
    st.info("4. Run `python main.py` to create the index first")
    st.info("5. Installed all required dependencies")
    st.stop()

if "history" not in st.session_state:
    st.session_state["history"] = []

question = st.text_input("Ask something from your course content:", "")
if question:
    with st.spinner("Thinking..."):
        try:
            # Query the chain
            answer = chain.invoke({"input": question})
            
            # Get source documents from retriever using invoke instead of get_relevant_documents
            source_docs = st.session_state.retriever.invoke(question)
            
            # Update history
            st.session_state["history"].append((question, answer))
            
            st.write("**Answer:**")
            st.write(answer)
            
            with st.expander("Source Documents"):
                if source_docs:
                    for doc in source_docs:
                        if hasattr(doc, 'metadata') and hasattr(doc, 'page_content'):
                            st.write(f"- **{doc.metadata.get('source', 'Unknown')}**: {doc.page_content[:500]}...")
                        else:
                            st.write(f"- {str(doc)[:500]}...")
                else:
                    st.write("No source documents available.")
        except Exception as e:
            st.error(f"Error processing your question: {e}")
            logger.exception("Error in chain invocation")
            st.info("Please try again or check your API quota.")
