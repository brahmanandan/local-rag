import os
# Set USER_AGENT environment variable early to avoid warnings
os.environ['USER_AGENT'] = os.getenv("USER_AGENT", "rag-chatbot/1.0")

import streamlit as st
import yaml
import logging
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from utils import get_embeddings_model, get_llm_model

load_dotenv()

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
        
        # Use modern LangChain API - try new API first, fallback to old if needed
        try:
            from langchain.chains import create_retrieval_chain
            from langchain.chains.combine_documents import create_stuff_documents_chain
            from langchain_core.prompts import ChatPromptTemplate
            
            # Create prompt template (simplified for compatibility)
            prompt = ChatPromptTemplate.from_template(
                "You are a helpful assistant that answers questions based on the provided context.\n\n"
                "Context: {context}\n\n"
                "Question: {input}\n\n"
                "Answer based on the context above. If the context doesn't contain the answer, say so."
            )
            
            # Create document chain
            document_chain = create_stuff_documents_chain(llm, prompt)
            
            # Create retrieval chain
            chain = create_retrieval_chain(retriever, document_chain)
            
            logger.info("Successfully loaded RAG chain with modern API")
            return chain, "modern"
        except (ImportError, AttributeError) as e:
            logger.warning(f"Modern API not available: {e}")
            # Fallback to ConversationalRetrievalChain for older LangChain versions
            try:
                from langchain.chains import ConversationalRetrievalChain
                chain = ConversationalRetrievalChain.from_llm(
                    llm, retriever, return_source_documents=True)
                logger.info("Successfully loaded RAG chain with legacy API")
                return chain, "legacy"
            except Exception as e:
                logger.error(f"Failed to load chain with legacy API: {e}")
                raise
    except Exception as e:
        st.error(f"Failed to load the RAG chain: {e}")
        st.info("Please check your API keys and ensure the index has been created.")
        st.info("Supported providers: OpenAI, Perplexity, Google Gemini, Ollama, llama.cpp, HuggingFace")
        return None, None

chain, chain_type = load_chain()

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
            if chain_type == "modern":
                # Modern API format
                result = chain.invoke({"input": question})
                
                answer = result.get("answer", "")
                # In modern API, documents are retrieved separately
                # The retrieval chain returns documents in the result
                source_docs = []
                
                # Check various possible keys for documents
                for key in ["documents", "context", "retrieved_documents"]:
                    if key in result:
                        docs = result[key]
                        if isinstance(docs, list):
                            source_docs = docs
                            break
                        elif hasattr(docs, "__iter__") and not isinstance(docs, str):
                            source_docs = list(docs)
                            break
                
                # If still no docs, try to get from retriever directly
                if not source_docs:
                    try:
                        if hasattr(st.session_state, 'vectorstore'):
                            retriever = st.session_state.vectorstore.as_retriever(
                                search_type="similarity", search_kwargs={"k": 5}
                            )
                            source_docs = retriever.get_relevant_documents(question)
                    except Exception as e:
                        logger.warning(f"Could not retrieve source documents: {e}")
                
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
            else:
                # Legacy API format
                result = chain.invoke({"question": question, "chat_history": st.session_state["history"]})
                st.session_state["history"].append((question, result["answer"]))

                st.write("**Answer:**")
                st.write(result["answer"])

                with st.expander("Source Documents"):
                    for doc in result.get("source_documents", []):
                        st.write(f"- **{doc.metadata.get('source', 'Unknown')}**: {doc.page_content[:500]}...")
        except Exception as e:
            st.error(f"Error processing your question: {e}")
            logger.exception("Error in chain invocation")
            st.info("Please try again or check your API quota.")
