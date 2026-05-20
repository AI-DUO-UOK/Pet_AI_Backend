"""
Advanced Retrieval Module

Provides:
- Semantic retrieval
- Metadata filtering
- Reranking capabilities
- Contextualized results
"""

import logging
from typing import List, Dict, Any, Optional

from llama_index.core import VectorStoreIndex
from llama_index.core.schema import NodeWithScore

from ..config import SIMILARITY_TOP_K


logger = logging.getLogger(__name__)


class SemanticRetriever:
    """
    Advanced semantic retriever for RAG
    
    Features:
    - Semantic similarity search
    - Metadata-aware filtering
    - Result ranking
    - Source tracking
    """
    
    def __init__(self, index: VectorStoreIndex):
        """
        Initialize retriever with LlamaIndex
        
        Args:
            index: VectorStoreIndex from ingestion pipeline
        """
        self.index = index
        logger.info("Initialized SemanticRetriever")
    
    def search(
        self,
        query: str,
        top_k: int = SIMILARITY_TOP_K,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for documents
        
        Args:
            query: Search query
            top_k: Number of top results
            filters: Optional metadata filters
            
        Returns:
            List of result dictionaries with content and metadata
        """
        try:
            logger.info(f"Searching for: {query}")
            
            # Create retriever
            retriever = self.index.as_retriever(
                similarity_top_k=top_k
            )
            
            # Retrieve nodes
            nodes = retriever.retrieve(query)
            
            # Convert to result dictionaries
            results = []
            for node in nodes:
                result = {
                    "content": node.get_content(),
                    "score": node.score,
                    "metadata": node.metadata,
                    "source": node.metadata.get("source", "unknown"),
                    "chunk_id": node.metadata.get("chunk_id"),
                    "chunk_type": node.metadata.get("chunk_type", "text"),
                }
                results.append(result)
            
            logger.info(f"Found {len(results)} relevant chunks")
            return results
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def search_by_source(
        self,
        query: str,
        source_file: str,
        top_k: int = SIMILARITY_TOP_K,
    ) -> List[Dict[str, Any]]:
        """
        Search within specific source document
        
        Args:
            query: Search query
            source_file: Filename to filter by
            top_k: Number of results
            
        Returns:
            List of filtered results
        """
        results = self.search(query, top_k=top_k * 2)  # Get more, then filter
        
        # Filter by source
        filtered = [
            r for r in results
            if r.get("source") == source_file
        ]
        
        return filtered[:top_k]
    
    def search_by_chunk_type(
        self,
        query: str,
        chunk_type: str,
        top_k: int = SIMILARITY_TOP_K,
    ) -> List[Dict[str, Any]]:
        """
        Search for specific chunk types
        
        Args:
            query: Search query
            chunk_type: Filter by type (text, table, code)
            top_k: Number of results
            
        Returns:
            List of filtered results
        """
        results = self.search(query, top_k=top_k * 2)
        
        # Filter by chunk type
        filtered = [
            r for r in results
            if r.get("chunk_type") == chunk_type
        ]
        
        return filtered[:top_k]
    
    def search_with_metadata(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = SIMILARITY_TOP_K,
    ) -> List[Dict[str, Any]]:
        """
        Search with metadata filtering
        
        Example filters:
        {
            "source_type": "markdown",
            "section": "Heart Failure",
        }
        
        Args:
            query: Search query
            filters: Metadata filters
            top_k: Number of results
            
        Returns:
            List of filtered results
        """
        results = self.search(query, top_k=top_k * 3)
        
        if not filters:
            return results[:top_k]
        
        # Apply filters
        filtered = results
        for key, value in filters.items():
            filtered = [
                r for r in filtered
                if r.get("metadata", {}).get(key) == value
            ]
        
        return filtered[:top_k]
