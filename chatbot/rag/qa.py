"""
RAG Question-Answering Module

Provides ask_rag() function that implements full RAG pipeline:
- Retrieve relevant chunks with confidence scores
- Filter by confidence threshold
- Build context from high-confidence chunks
- Generate answers using LLM with retrieved context
- Fallback to general knowledge for uncertain queries
"""

import logging
from typing import Optional, List, Dict, Any

from chatbot.rag.retriever import get_retriever, get_advanced_retriever
from chatbot.llm import llm


logger = logging.getLogger(__name__)

# Confidence threshold for using retrieved context
CONFIDENCE_THRESHOLD = 0.65


def ask_rag(
    question: str,
    use_advanced_rag: bool = True,
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
    top_k: int = 5,
) -> str:
    """
    Answer question using complete RAG pipeline
    
    Pipeline:
    1. Retrieve relevant chunks with similarity scores
    2. Filter by confidence threshold
    3. Build context from high-confidence chunks
    4. Generate answer using LLM with context
    5. Fallback to general knowledge if needed
    
    Args:
        question: User question
        use_advanced_rag: Use advanced retriever with confidence filtering
        confidence_threshold: Minimum similarity score to use chunk (0-1)
        top_k: Number of chunks to retrieve
        
    Returns:
        Final synthesized answer from LLM
    """
    try:
        context = ""
        retrieval_info = {}
        
        # Step 1: Retrieve relevant chunks
        if use_advanced_rag:
            logger.info(f"Retrieving top {top_k} chunks using advanced RAG")
            advanced_retriever = get_advanced_retriever()
            
            if advanced_retriever.semantic_retriever:
                # Get all results first
                results = advanced_retriever.search(question, top_k=top_k)
                
                # Step 2: Filter by confidence threshold
                filtered_results = [
                    r for r in results 
                    if r.get("score", 0) > confidence_threshold
                ]
                
                retrieval_info = {
                    "total_retrieved": len(results),
                    "confidence_filtered": len(filtered_results),
                    "threshold": confidence_threshold,
                }
                
                if filtered_results:
                    logger.info(
                        f"After confidence filtering: "
                        f"{len(filtered_results)}/{len(results)} results passed "
                        f"threshold ({confidence_threshold})"
                    )
                    
                    # Step 3: Build context from high-confidence chunks
                    context_parts = []
                    for result in filtered_results:
                        content = result.get("content", "")
                        score = result.get("score", 0)
                        source = result.get("source", "Unknown")
                        chunk_type = result.get("chunk_type", "text")
                        
                        # Log retrieval details
                        logger.debug(
                            f"Including chunk: {source} "
                            f"(type: {chunk_type}, score: {score:.3f})"
                        )
                        context_parts.append(content)
                    
                    context = "\n\n".join(context_parts)
                    logger.info(f"Built context from {len(context_parts)} chunks")
                else:
                    logger.warning(
                        f"No chunks passed confidence threshold ({confidence_threshold}). "
                        f"Will answer using general knowledge."
                    )
                    retrieval_info["fallback_reason"] = "low_confidence"
            else:
                logger.warning("Advanced retriever not initialized, using legacy")
                retrieval_info["fallback_reason"] = "advanced_not_ready"
        
        # Fallback to legacy retriever if needed
        if not context and not use_advanced_rag:
            logger.info("Using legacy LangChain retriever")
            retriever = get_retriever()
            docs = retriever.invoke(question)
            context_parts = [doc.page_content for doc in docs]
            context = "\n\n".join(context_parts)
            retrieval_info["method"] = "legacy"
        
        # Step 4: Create prompt with context
        if context:
            prompt = f"""You are a helpful veterinary AI assistant.

Use the following context to answer the question as accurately as possible.

Context:
{context}

Question:
{question}

Answer:"""
            logger.info("Using retrieved context for answer generation")
        else:
            # Fallback: answer using general knowledge
            prompt = f"""You are a helpful veterinary AI assistant.

Answer the following question using your general knowledge.

Question:
{question}

Answer:"""
            logger.info("No context available, using general knowledge")
        
        # Step 5: Send to LLM
        logger.info("Sending prompt to LLM for answer generation")
        response = llm.invoke(prompt)
        
        # Step 6: Extract and return answer
        answer = response.content if hasattr(response, "content") else str(response)
        
        logger.info(f"Generated answer ({len(answer)} chars)")
        logger.debug(f"Retrieval info: {retrieval_info}")
        
        return answer
    
    except Exception as e:
        logger.error(f"Error in ask_rag: {e}", exc_info=True)
        return f"Error processing question: {str(e)}"