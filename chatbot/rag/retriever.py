"""
Retrieval Module - Supports both Legacy and Advanced RAG

Provides:
- Legacy LangChain retriever (for backwards compatibility)
- Advanced LlamaIndex retriever (new)
- Unified interface for both
"""

import logging
from pathlib import Path
from typing import Optional, List, Any

# Legacy imports
from langchain_chroma import Chroma as LangChainChroma
from langchain_huggingface import HuggingFaceEmbeddings

# Advanced imports
from llama_index.core import VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from .config import CHROMA_DB_DIR, COLLECTION_NAME, EMBED_MODEL_NAME
from .retrieval import SemanticRetriever
from .vectorstore import ChromaStore


logger = logging.getLogger(__name__)

DB_PATH = "chatbot/db"  # Legacy path


# ─────────────────────────────────────────────────────────────────
# Legacy LangChain Retriever (Backwards Compatible)
# ─────────────────────────────────────────────────────────────────

def get_retriever():
    """
    Get legacy LangChain-based retriever
    
    For backwards compatibility with existing code.
    Falls back to old implementation if new vector store not available.
    
    Returns:
        LangChain retriever
    """
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    db = LangChainChroma(
        persist_directory=DB_PATH,
        embedding_function=embeddings
    )

    retriever = db.as_retriever(search_kwargs={"k": 3})

    return retriever


# ─────────────────────────────────────────────────────────────────
# Advanced LlamaIndex Retriever
# ─────────────────────────────────────────────────────────────────

class AdvancedRetriever:
    """
    Advanced retriever using new RAG pipeline
    
    Integrates:
    - LlamaIndex vector indexing
    - ChromaDB vector store
    - Semantic retrieval with metadata
    - Multiple retrieval modes
    """
    
    _instance: Optional['AdvancedRetriever'] = None
    
    def __new__(cls):
        """Singleton pattern to reuse initialized retriever"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize advanced retriever"""
        if self._initialized:
            return
        
        try:
            logger.info("Initializing AdvancedRetriever...")
            
            # Initialize vector store
            self.vector_store_manager = ChromaStore(
                chroma_db_dir=CHROMA_DB_DIR,
                collection_name=COLLECTION_NAME,
            )
            
            # Initialize embedding model
            self.embed_model = HuggingFaceEmbedding(
                model_name=EMBED_MODEL_NAME
            )
            
            # Try to load existing index
            try:
                self.index = VectorStoreIndex.from_vector_store(
                    vector_store=self.vector_store_manager.get_vector_store(),
                    embed_model=self.embed_model,
                )
                logger.info("Loaded existing vector index")
            except Exception as e:
                logger.warning(f"Could not load existing index: {e}")
                logger.info("Index will be created during ingestion")
                self.index = None
            
            # Initialize semantic retriever if index exists
            if self.index:
                self.semantic_retriever = SemanticRetriever(self.index)
            else:
                self.semantic_retriever = None
            
            self._initialized = True
            logger.info("AdvancedRetriever initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AdvancedRetriever: {e}")
            self._initialized = True  # Mark as attempted
            self.semantic_retriever = None
    
    def search(self, query: str, top_k: int = 3) -> List[dict]:
        """
        Perform semantic search
        
        Args:
            query: Search query
            top_k: Number of results
            
        Returns:
            List of result dicts with content and metadata
        """
        if not self.semantic_retriever:
            logger.warning("Semantic retriever not initialized")
            return []
        
        try:
            return self.semantic_retriever.search(query, top_k=top_k)
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def get_context(self, query: str, top_k: int = 3) -> str:
        """
        Get context string for LLM
        
        Args:
            query: Search query
            top_k: Number of chunks
            
        Returns:
            Combined context string
        """
        results = self.search(query, top_k=top_k)
        
        if not results:
            return ""
        
        context_parts = [r["content"] for r in results]
        return "\n\n".join(context_parts)
    
    def reload_index(self):
        """Reload index from vector store"""
        try:
            self.index = VectorStoreIndex.from_vector_store(
                vector_store=self.vector_store_manager.get_vector_store(),
                embed_model=self.embed_model,
            )
            self.semantic_retriever = SemanticRetriever(self.index)
            logger.info("Index reloaded successfully")
        except Exception as e:
            logger.error(f"Failed to reload index: {e}")


def get_advanced_retriever() -> AdvancedRetriever:
    """
    Get the advanced retriever instance (singleton)
    
    Returns:
        AdvancedRetriever instance
    """
    return AdvancedRetriever()