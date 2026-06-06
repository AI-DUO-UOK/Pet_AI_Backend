"""
Agentic RAG System

Instead of always retrieving from knowledge base, the LLM agent decides:
- Whether to use the retriever tool
- Whether to answer directly from general knowledge
- Whether to ask for clarification

This is the professional, production-grade approach used by ChatGPT, Claude, etc.
"""

from chatbot.rag.retriever import get_advanced_retriever
from chatbot.llm import llm
import logging

logger = logging.getLogger(__name__)


def search_veterinary_knowledge_base(query: str) -> str:
    """
    Search the veterinary knowledge base for information about pet diseases,
    symptoms, treatments, and healthcare.
    
    Use this ONLY for veterinary/medical questions.
    Do NOT use for casual conversation or personal information.
    """
    try:
        retriever = get_advanced_retriever()
        search_results = retriever.search(query=query, top_k=3)
        
        # Filter results by confidence threshold
        rag_threshold = 0.7
        relevant_results = [
            result for result in search_results
            if result.get('score', 0) >= rag_threshold
        ]
        
        if not relevant_results:
            return "No relevant veterinary information found in the knowledge base for this query."
        
        # Build context from retrieved chunks
        context = "\n\n".join([
            f"Source: {result.get('source', 'Unknown')}\n{result.get('content', '')}"
            for result in relevant_results
        ])
        
        return context
    except Exception:
        logging.exception("Error searching knowledge base")
        return "Error retrieving information from knowledge base."


def is_skin_or_eye_issue(question: str) -> bool:
    """
    Detect if the question is about skin or eye issues.
    If yes, ask for an image first before searching the knowledge base.
    
    Args:
        question: The user's question
        
    Returns:
        True if this is a skin or eye issue, False otherwise
    """
    # Keywords for skin/eye issues
    skin_keywords = [
        "skin", "rash", "itching", "itch", "scratching", "scratch",
        "hives", "mange", "dryness", "scabs", "wounds", "infection",
        "fungal", "bacterial", "dermatitis", "allergies", "spots",
        "bumps", "lesions", "sores", "patches", "flaky", "scaly"
    ]
    
    eye_keywords = [
        "eye", "eyes", "vision", "sight", "blind", "blindness",
        "discharge", "tearing", "tear", "redness", "red eye",
        "cloudiness", "cloudy", "squinting", "squint", "pupil",
        "glaucoma", "cataract", "cornea", "iris", "conjunctivitis",
        "conjunctivitis", "stye", "swelling", "bulging", "watery"
    ]
    
    question_lower = question.lower()
    
    # Check for skin or eye keywords
    for keyword in skin_keywords + eye_keywords:
        if keyword in question_lower:
            return True
    
    return False


def query_agentic_rag(
    question: str,
    chat_history: str = "",
    force_rag: bool = False
) -> str:
    """
    Query the agentic RAG system using intelligent routing.
    
    The LLM decides:
    1. Whether this question needs veterinary knowledge retrieval
    2. Whether it's casual conversation that doesn't need RAG
    3. For skin/eye issues: ask for an image first before searching RAG
    4. For CV predictions: ALWAYS use RAG (force_rag=True)
    
    This approach is simpler, more reliable, and uses native LLM capabilities
    instead of complex agent frameworks.
    
    Args:
        question: The user's question
        chat_history: Previous conversation context for memory
        force_rag: If True, ALWAYS use RAG (for CV model predictions)
        
    Returns:
        The LLM's response with or without RAG context
    """
    try:
        # If force_rag is True, skip all other logic and go straight to RAG search
        if force_rag:
            rag_context = search_veterinary_knowledge_base(question)
            
            if "No relevant" in rag_context or "Error" in rag_context:
                # If RAG fails, still provide general knowledge answer
                final_prompt = f"""You are a helpful veterinary assistant AI.

PREVIOUS CONVERSATION (if any):
{chat_history}

USER QUESTION: {question}

Answer this question using your general veterinary knowledge. Be thorough and informative."""
            else:
                # Use RAG context
                final_prompt = f"""You are a helpful veterinary assistant AI.

Use the following retrieved context from the veterinary knowledge base to answer the user's question:

VETERINARY KNOWLEDGE BASE CONTEXT:
{rag_context}

PREVIOUS CONVERSATION (if any):
{chat_history}

USER QUESTION: {question}

Answer based on the retrieved context. Provide detailed, accurate veterinary advice."""
            
            response = llm.invoke(final_prompt)
            return response.content
        
        # Check if this is a skin or eye issue - if so, ask for image first
        # BUT skip this if the question already contains a CV model prediction
        if "computer vision model detected" not in question.lower() and is_skin_or_eye_issue(question):
            image_request_prompt = f"""You are a helpful veterinary assistant AI.

The user is asking about a potential skin or eye issue with their pet.

PREVIOUS CONVERSATION (if any):
{chat_history}

USER QUESTION: {question}

Your response should:
1. Acknowledge their concern
2. Ask them to share an image/photo of the affected area/eye
3. Explain why the image is important for diagnosis
4. Be empathetic and reassuring
5. DO NOT search medical knowledge base or provide detailed medical explanations yet
6. Keep your response focused on requesting the image first

Respond in a friendly, professional manner."""
            
            response = llm.invoke(image_request_prompt)
            return response.content
        
        # For non-skin/eye issues, proceed with regular RAG routing
        # First, ask the LLM to decide: should we use RAG?
        routing_prompt = f"""Given this user question, decide if it requires veterinary knowledge base retrieval.

USER QUESTION: {question}

Answer with ONLY 'YES' or 'NO':
- YES if this is a medical/veterinary question that needs knowledge base lookup
- NO if this is casual conversation, personal chat, or non-medical information

Answer (YES/NO):"""
        
        routing_response = llm.invoke(routing_prompt)
        should_use_rag = "YES" in routing_response.content.upper()
        
        # Get veterinary context if needed
        rag_context = ""
        if should_use_rag:
            rag_context = search_veterinary_knowledge_base(question)
            # Check if we got useful information
            if "No relevant" in rag_context or "Error" in rag_context:
                # RAG didn't find relevant info, fall back to general knowledge
                should_use_rag = False
                rag_context = ""
        
        # Build the final prompt with or without RAG context
        if should_use_rag and rag_context:
            # Use RAG context
            final_prompt = f"""You are a helpful veterinary assistant AI.

Use the following retrieved context from the veterinary knowledge base to answer the user's question:

VETERINARY KNOWLEDGE BASE CONTEXT:
{rag_context}

PREVIOUS CONVERSATION (if any):
{chat_history}

USER QUESTION: {question}

Answer based on the retrieved context. Provide detailed, accurate veterinary advice."""
        else:
            # Use general knowledge (no RAG)
            final_prompt = f"""You are a helpful veterinary assistant AI.

PREVIOUS CONVERSATION (if any):
{chat_history}

USER QUESTION: {question}

Answer this question. If it's a veterinary question that needs specific knowledge, provide your general veterinary knowledge.
If it's casual conversation, respond naturally and friendly."""
        
        # Get the final response
        response = llm.invoke(final_prompt)
        return response.content
    
    except Exception:
        logging.exception("Error in agentic RAG")
        # Fallback: just answer the question directly
        try:
            fallback_prompt = f"""You are a helpful veterinary assistant.

Previous conversation:
{chat_history}

User question: {question}

Please answer this question to the best of your ability."""
            
            response = llm.invoke(fallback_prompt)
            return response.content
        except Exception:
            return "I encountered an error processing your question. Please try again."

