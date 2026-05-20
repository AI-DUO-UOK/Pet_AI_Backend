"""
RAG Query Engine

Provides end-to-end RAG functionality:
- Document retrieval
- Context assembly
- LLM-based answering
- Response generation
"""

import logging
from typing import Optional, List, Dict, Any

from .retriever import SemanticRetriever
from ..config import SIMILARITY_TOP_K


logger = logging.getLogger(__name__)


class RAGQueryEngine:
    """
    Complete RAG query engine
    
    Combines:
    - Semantic retrieval
    - Context assembly
    - LLM integration
    """
    
    def __init__(
        self,
        retriever: SemanticRetriever,
        llm=None,
    ):
        """
        Initialize query engine
        
        Args:
            retriever: SemanticRetriever instance
            llm: LLM instance for answer generation (optional)
        """
        self.retriever = retriever
        self.llm = llm
        logger.info("Initialized RAGQueryEngine")
    
    def query(
        self,
        question: str,
        top_k: int = SIMILARITY_TOP_K,
        use_llm: bool = False,
    ) -> Dict[str, Any]:
        """
        Process query and generate answer
        
        Args:
            question: User question
            top_k: Number of context chunks to retrieve
            use_llm: Whether to use LLM for answer generation
            
        Returns:
            Response dictionary with context and answer
        """
        try:
            logger.info(f"Processing query: {question}")
            
            # Retrieve relevant documents
            results = self.retriever.search(question, top_k=top_k)
            
            if not results:
                return {
                    "question": question,
                    "answer": "No relevant information found.",
                    "context": [],
                    "sources": [],
                }
            
            # Assemble context
            context_chunks = [r["content"] for r in results]
            context = "\n\n".join(context_chunks)
            
            # Track sources
            sources = list(set([r["source"] for r in results]))
            
            # Generate answer if LLM available
            answer = None
            if use_llm and self.llm:
                answer = self._generate_answer(question, context)
            
            response = {
                "question": question,
                "context": context_chunks,
                "context_text": context,
                "answer": answer,
                "sources": sources,
                "retrieval_results": results,
                "num_chunks": len(results),
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Query error: {e}")
            return {
                "question": question,
                "error": str(e),
            }
    
    def _generate_answer(self, question: str, context: str) -> Optional[str]:
        """
        Generate answer using LLM
        
        Args:
            question: User question
            context: Retrieved context
            
        Returns:
            LLM-generated answer
        """
        if not self.llm:
            return None
        
        try:
            prompt = f"""Use the following context to answer the question.
If the context doesn't contain relevant information, say so clearly.

Context:
{context}

Question:
{question}

Answer:"""
            
            response = self.llm.invoke(prompt)
            
            if hasattr(response, "content"):
                return response.content
            
            return str(response)
            
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return None
    
    def explain_retrieval(
        self,
        question: str,
        top_k: int = SIMILARITY_TOP_K,
    ) -> Dict[str, Any]:
        """
        Explain retrieval process and results
        
        Useful for debugging and understanding why certain docs were retrieved
        
        Args:
            question: Query question
            top_k: Number of results
            
        Returns:
            Detailed retrieval explanation
        """
        results = self.retriever.search(question, top_k=top_k)
        
        explanation = {
            "question": question,
            "num_results": len(results),
            "results": []
        }
        
        for i, result in enumerate(results, 1):
            explanation["results"].append({
                "rank": i,
                "score": result.get("score"),
                "source": result.get("source"),
                "chunk_type": result.get("chunk_type"),
                "content_preview": result["content"][:200] + "...",
                "metadata": result.get("metadata"),
            })
        
        return explanation
