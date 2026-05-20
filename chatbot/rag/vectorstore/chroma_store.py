"""
ChromaDB Vector Store Integration with LlamaIndex

Provides persistent vector storage with:
- LlamaIndex integration
- Semantic search
- Metadata filtering
- Batch indexing
"""

import logging
from pathlib import Path
from typing import Optional

import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext

from ..config import CHROMA_DB_DIR, COLLECTION_NAME


logger = logging.getLogger(__name__)


class ChromaStore:
    """
    ChromaDB Vector Store for LlamaIndex
    
    Manages:
    - Persistent vector storage
    - Collection management
    - Semantic search
    - Metadata preservation
    """
    
    def __init__(
        self,
        chroma_db_dir: Path = CHROMA_DB_DIR,
        collection_name: str = COLLECTION_NAME,
    ):
        """
        Initialize ChromaDB store
        
        Args:
            chroma_db_dir: Path to ChromaDB directory
            collection_name: Name of Chroma collection
        """
        self.chroma_db_dir = Path(chroma_db_dir)
        self.collection_name = collection_name
        
        # Ensure directory exists
        self.chroma_db_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initializing ChromaDB at {self.chroma_db_dir}")
        
        # Initialize Chroma client
        self.client = chromadb.PersistentClient(
            path=str(self.chroma_db_dir)
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={
                "hnsw:space": "cosine",
                "description": "Pet health RAG vector store"
            }
        )
        
        # Initialize ChromaVectorStore for LlamaIndex
        self.vector_store = ChromaVectorStore(
            chroma_collection=self.collection
        )
        
        logger.info(
            f"ChromaDB initialized with collection: {self.collection_name}"
        )
    
    def get_vector_store(self) -> ChromaVectorStore:
        """
        Get ChromaVectorStore instance
        
        Returns:
            ChromaVectorStore for LlamaIndex
        """
        return self.vector_store
    
    def get_storage_context(self) -> StorageContext:
        """
        Get LlamaIndex StorageContext
        
        Returns:
            StorageContext configured with ChromaVectorStore
        """
        return StorageContext.from_defaults(
            vector_store=self.vector_store
        )
    
    def get_collection_stats(self) -> dict:
        """
        Get statistics about the collection
        
        Returns:
            Dictionary with collection info
        """
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "document_count": count,
                "location": str(self.chroma_db_dir),
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {}
    
    def delete_collection(self) -> bool:
        """
        Delete the entire collection
        
        WARNING: This is destructive!
        
        Returns:
            True if successful
        """
        try:
            self.client.delete_collection(name=self.collection_name)
            logger.warning(f"Deleted collection: {self.collection_name}")
            
            # Reinitialize
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name
            )
            self.vector_store = ChromaVectorStore(
                chroma_collection=self.collection
            )
            
            return True
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            return False
    
    def clear_collection(self) -> bool:
        """
        Clear all documents from collection
        
        WARNING: This is destructive!
        
        Returns:
            True if successful
        """
        try:
            # Get all IDs
            all_data = self.collection.get()
            if all_data["ids"]:
                self.collection.delete(ids=all_data["ids"])
                logger.warning(f"Cleared {len(all_data['ids'])} documents from collection")
            
            return True
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
            return False
    
    def persist(self) -> bool:
        """
        Persist the store (ChromaDB persists automatically)
        
        Returns:
            True if successful
        """
        try:
            logger.info("ChromaDB store persisted")
            return True
        except Exception as e:
            logger.error(f"Error persisting store: {e}")
            return False
