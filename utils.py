"""
Shared utilities for embeddings and LLM model loading with fallback support.
Optimized for macOS with local LLM support.
Uses config.yaml for priority configuration.
"""
import os
import yaml
import logging
import platform
import warnings
from typing import Optional, Any, List
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables as early as possible
load_dotenv()

# Set USER_AGENT environment variable early to avoid warnings
os.environ['USER_AGENT'] = os.getenv("USER_AGENT", "rag-chatbot/1.0")

# Suppress torch warnings
warnings.filterwarnings("ignore", category=UserWarning, module="torch")
warnings.filterwarnings("ignore", message=".*probability tensor.*")
warnings.filterwarnings("ignore", message=".*Token indices sequence length.*")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

logger = logging.getLogger(__name__)

# Quiet down overly chatty HTTP client logs (avoid surfacing provider 401/404 as INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

def load_config(config_path='config.yaml'):
    """Load configuration from YAML file."""
    try:
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        else:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return {}
    except Exception as e:
        logger.warning(f"Error loading config: {e}, using defaults")
        return {}

# Load config
_config = load_config()

# Default priorities if not in config
DEFAULT_EMBEDDINGS_PRIORITY = ["openai", "perplexity", "google", "huggingface_bge", "huggingface"]
DEFAULT_LLM_PRIORITY = ["openai", "perplexity", "google", "ollama", "llama_cpp", "huggingface"]

def detect_device():
    """Detect the best device for model inference."""
    try:
        import torch
        if torch.backends.mps.is_available():
            return "mps"  # Apple Silicon GPU
        elif torch.cuda.is_available():
            return "cuda"
        else:
            return "cpu"
    except ImportError:
        return "cpu"

def get_embeddings_model():
    """Get embeddings model based on config.yaml priority."""
    priority = _config.get("EMBEDDINGS_PRIORITY", DEFAULT_EMBEDDINGS_PRIORITY)
    model_config = _config.get("MODELS", {})
    
    for provider in priority:
        try:
            if provider == "openai":
                from langchain_openai import OpenAIEmbeddings
                model_name = model_config.get("openai", {}).get("embedding_model", "text-embedding-ada-002")
                embeddings = OpenAIEmbeddings(model=model_name)
                test_embedding = embeddings.embed_query("test")
                logger.info(f"Successfully loaded OpenAI embeddings ({model_name})")
                return embeddings
            elif provider == "perplexity":
                from langchain_perplexity import PerplexityEmbeddings
                embeddings = PerplexityEmbeddings()
                test_embedding = embeddings.embed_query("test")
                logger.info("Successfully loaded Perplexity embeddings")
                return embeddings
            elif provider == "google":
                from langchain_google_genai import GoogleGenerativeAIEmbeddings
                # Prefer modern embedding model; fall back to legacy if needed
                google_cfg = model_config.get("google", {})
                candidate_models: List[str] = []
                # Config-provided model first
                if google_cfg.get("embedding_model"):
                    candidate_models.append(google_cfg["embedding_model"])
                # Modern default, then legacy
                candidate_models.extend([
                    "models/text-embedding-004",
                    "text-embedding-004",
                    "models/embedding-001",
                    "embedding-001",
                ])

                last_err: Optional[Exception] = None
                for model_name in candidate_models:
                    try:
                        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
                        if not api_key:
                            raise ImportError("Missing GOOGLE_API_KEY/GEMINI_API_KEY")
                        embeddings = GoogleGenerativeAIEmbeddings(
                            model=model_name,
                            api_key=api_key,
                        )
                        _ = embeddings.embed_query("test")
                        logger.info(f"Successfully loaded Google Gemini embeddings ({model_name})")
                        return embeddings
                    except Exception as ge:
                        last_err = ge
                        continue
                if last_err:
                    raise last_err
            elif provider == "huggingface_bge":
                from langchain_huggingface import HuggingFaceEmbeddings
                embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
                test_embedding = embeddings.embed_query("test")
                logger.info("Successfully loaded HuggingFace BGE embeddings")
                return embeddings
            elif provider == "huggingface":
                from langchain_huggingface import HuggingFaceEmbeddings
                models = model_config.get("huggingface", {}).get("embedding_models", ["sentence-transformers/all-MiniLM-L6-v2"])
                for model_name in models:
                    try:
                        embeddings = HuggingFaceEmbeddings(model_name=model_name)
                        test_embedding = embeddings.embed_query("test")
                        logger.info(f"Successfully loaded HuggingFace embeddings ({model_name})")
                        return embeddings
                    except Exception as e:
                        logger.warning(f"HuggingFace model {model_name} failed: {e}")
                        continue
        except ImportError as e:
            logger.debug(f"{provider} not available: {e}")
            continue
        except Exception as e:
            # Suppress quota/rate limit errors - they're expected
            error_str = str(e).lower()
            if "quota" in error_str or "rate limit" in error_str or "429" in error_str:
                logger.debug(f"{provider} quota exceeded, trying next provider")
            elif "401" in error_str or "unauthorized" in error_str:
                logger.debug(f"{provider} authentication failed, trying next provider")
            else:
                logger.warning(f"{provider} embeddings failed: {e}")
            continue
    
    raise Exception("All embedding providers failed. Please check your API keys or install local models.")

def get_llm_model():
    """Get LLM model based on config.yaml priority."""
    priority = _config.get("LLM_PRIORITY", DEFAULT_LLM_PRIORITY)
    model_config = _config.get("MODELS", {})
    
    for provider in priority:
        try:
            if provider == "openai":
                from langchain_openai import ChatOpenAI
                config = model_config.get("openai", {})
                if not os.getenv("OPENAI_API_KEY"):
                    logger.debug("OPENAI_API_KEY not set; skipping OpenAI provider")
                    raise ImportError("Missing OPENAI_API_KEY")
                llm = ChatOpenAI(
                    temperature=config.get("temperature", 0.2),
                    model=config.get("llm_model", "gpt-3.5-turbo"),
                )
                _ = llm.invoke("test")
                logger.info(f"Successfully loaded OpenAI LLM ({config.get('llm_model', 'gpt-3.5-turbo')})")
                return llm
            elif provider == "perplexity":
                from langchain_perplexity import PerplexityLLM
                config = model_config.get("perplexity", {})
                llm = PerplexityLLM(
                    model=config.get("llm_model", "mistral-7b-instruct"),
                    temperature=config.get("temperature", 0.2)
                )
                test_response = llm.invoke("test")
                logger.info(f"Successfully loaded Perplexity LLM ({config.get('llm_model', 'mistral-7b-instruct')})")
                return llm
            elif provider == "google":
                from langchain_google_genai import ChatGoogleGenerativeAI
                config = model_config.get("google", {})
                api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
                if not api_key:
                    logger.debug("GOOGLE_API_KEY/GEMINI_API_KEY not set; skipping Google provider")
                    raise ImportError("Missing GOOGLE_API_KEY/GEMINI_API_KEY")

                # Try multiple model IDs to avoid 404 due to library/version diffs
                user_model = config.get("llm_model")
                candidate_models: List[str] = []
                if user_model:
                    candidate_models.append(user_model)
                candidate_models.extend([
                    "gemini-1.5-flash",
                    "gemini-1.5-flash-8b",
                    "gemini-1.5-pro",
                    "gemini-pro",
                    # Prefixed variants some SDKs expect
                    "models/gemini-1.5-flash",
                    "models/gemini-1.5-flash-8b",
                    "models/gemini-1.5-pro",
                    "models/gemini-pro",
                ])

                last_err: Optional[Exception] = None
                for model_name in candidate_models:
                    try:
                        llm = ChatGoogleGenerativeAI(
                            model=model_name,
                            temperature=config.get("temperature", 0.2),
                            api_key=api_key,
                        )
                        _ = llm.invoke("test")
                        logger.info(f"Successfully loaded Google Gemini LLM ({model_name})")
                        return llm
                    except Exception as ge:
                        last_err = ge
                        continue
                if last_err:
                    raise last_err
            elif provider == "ollama":
                # Try new langchain-ollama first, fallback to deprecated version
                try:
                    from langchain_ollama import ChatOllama
                    OllamaLLM = ChatOllama
                except ImportError:
                    try:
                        from langchain_community.chat_models import ChatOllama
                        OllamaLLM = ChatOllama
                    except ImportError:
                        logger.debug("Ollama not available")
                        continue
                
                models = model_config.get("ollama", {}).get("models", ["llama2", "mistral", "llama3", "phi3", "gemma"])
                config = model_config.get("ollama", {})
                for model_name in models:
                    try:
                        llm = OllamaLLM(
                            model=model_name,
                            temperature=config.get("temperature", 0.2)
                        )
                        test_response = llm.invoke("test")
                        logger.info(f"Successfully loaded Ollama LLM: {model_name}")
                        return llm
                    except Exception as e:
                        error_str = str(e).lower()
                        if "connection refused" in error_str or "connection" in error_str:
                            logger.debug(f"Ollama not running, trying next model")
                        else:
                            logger.debug(f"Ollama model {model_name} failed: {e}")
                        continue
            elif provider == "llama_cpp":
                try:
                    from langchain_community.llms import LlamaCpp
                except ImportError:
                    logger.debug("llama-cpp-python not available")
                    continue
                
                config = model_config.get("llama_cpp", {})
                model_paths = config.get("model_paths", [
                    os.path.expanduser("~/.cache/llama-cpp/llama-2-7b-chat.gguf"),
                    os.path.expanduser("~/.cache/llama-cpp/mistral-7b-instruct-v0.1.gguf"),
                ])
                
                # Check environment variable
                custom_path = os.getenv("LLAMA_CPP_MODEL_PATH")
                if custom_path:
                    model_paths.insert(0, custom_path)
                
                for model_path in model_paths:
                    if os.path.exists(model_path):
                        try:
                            n_threads = os.cpu_count() or 4
                            llm = LlamaCpp(
                                model_path=model_path,
                                temperature=config.get("temperature", 0.2),
                                n_ctx=config.get("n_ctx", 2048),
                                n_threads=n_threads,
                                verbose=False,
                            )
                            test_response = llm.invoke("test")
                            logger.info(f"Successfully loaded llama.cpp LLM: {model_path}")
                            return llm
                        except Exception as e:
                            logger.debug(f"llama.cpp model {model_path} failed: {e}")
                            continue
            elif provider == "huggingface":
                from langchain_huggingface import HuggingFacePipeline
                from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
                import torch
                
                device = detect_device()
                logger.debug(f"Using device: {device} for HuggingFace models")
                
                config = model_config.get("huggingface", {})
                models = config.get("llm_models", [
                    "TinyLlama/TinyLlama-1.1B-Chat-v1.0",  # Best for RAG, chat-optimized
                    "microsoft/DialoGPT-medium",  # Good for conversations
                    "gpt2",  # Reliable fallback
                    "distilgpt2",  # Smallest fallback
                ])
                max_length = config.get("max_length", 2048)
                
                for model_name in models:
                    try:
                        logger.debug(f"Trying HuggingFace model: {model_name}")
                        tokenizer = AutoTokenizer.from_pretrained(model_name)
                        
                        if tokenizer.pad_token is None:
                            tokenizer.pad_token = tokenizer.eos_token
                        
                        model_kwargs = {}
                        if device == "mps":
                            model_kwargs["torch_dtype"] = torch.float16
                        
                        model = AutoModelForCausalLM.from_pretrained(
                            model_name,
                            device_map="auto" if device != "mps" else None,
                            **model_kwargs
                        )
                        
                        if device == "mps":
                            model = model.to(device)
                        
                        pipe = pipeline(
                            "text-generation",
                            model=model,
                            tokenizer=tokenizer,
                            max_new_tokens=min(512, max_length // 4),  # Limit tokens to avoid sequence length issues
                            max_length=max_length,
                            temperature=config.get("temperature", 0.2),
                            do_sample=True,
                            pad_token_id=tokenizer.pad_token_id,
                            device=0 if device == "cuda" else -1,
                        )
                        
                        llm = HuggingFacePipeline(pipeline=pipe)
                        test_response = llm.invoke("test")
                        logger.info(f"Successfully loaded HuggingFace LLM: {model_name} on {device}")
                        return llm
                    except Exception as e:
                        error_str = str(e).lower()
                        if "probability tensor" in error_str or "nan" in error_str or "inf" in error_str:
                            logger.debug(f"HuggingFace model {model_name} has tensor issues, trying next")
                        else:
                            logger.debug(f"HuggingFace model {model_name} failed: {e}")
                        try:
                            del model, tokenizer, pipe
                            import gc
                            gc.collect()
                            if device == "mps":
                                torch.mps.empty_cache()
                            elif device == "cuda":
                                torch.cuda.empty_cache()
                        except:
                            pass
                        continue
        except ImportError as e:
            logger.debug(f"{provider} package not installed: {e}")
            continue
        except Exception as e:
            error_str = str(e).lower()
            if "quota" in error_str or "rate limit" in error_str or "429" in error_str:
                logger.debug(f"{provider} quota exceeded, trying next provider")
            elif "401" in error_str or "unauthorized" in error_str:
                logger.debug(f"{provider} authentication failed, trying next provider")
            elif "404" in error_str or "not found" in error_str:
                logger.debug(f"{provider} model not found, trying next provider")
            else:
                logger.warning(f"{provider} LLM failed: {e}")
            continue
    
    raise Exception(
        "All LLM providers failed. Please:\n"
        "1. Check your API keys for cloud providers\n"
        "2. Install Ollama and download a model: https://ollama.ai\n"
        "3. Or ensure HuggingFace models can be downloaded"
    )

