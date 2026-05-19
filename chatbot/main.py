import re
import os
import json
from pathlib import Path
from chatbot.agent import agent
from chatbot.llm import llm
from chatbot.memory import memory
from chatbot.langsmith_config import setup_langsmith
from chatbot.rag.retriever import get_advanced_retriever  # Import retriever for RAG context

# Keywords for intent detection
SKIN_KEYWORDS = [
    "skin", "rash", "itch", "fur", "hair loss", "scab", "wound",
    "dermatitis", "fungal", "ringworm", "mange", "scabies", "allergic",
    "infection", "lesion", "bump", "spot", "dry", "flaky", "irritation"
]

EYE_KEYWORDS = [
    "eye", "sight", "vision", "discharge", "redness", "cloudiness",
    "swelling", "inflammation", "keratitis", "blepharitis", "entropion",
    "eyelid", "tumor", "cornea", "conjunctive", "watery", "crusty"
]

def extract_image_path(user_input: str) -> str:
    """
    Extract image file path from user input.
    Handles filenames with spaces, dots, and special characters.
    Supports formats like:
    - /path/to/image file.jpg (with spaces)
    - image.jpg
    - ~/Documents/image.jpg
    """
    # More robust pattern that handles spaces in filenames
    # Matches paths starting with / or ~ followed by any mix of alphanumeric, 
    # spaces, dots, hyphens, underscores and slashes, ending in image extension
    pattern = r'(/[^\n]*\.(?:jpg|jpeg|png|gif|bmp)|~/[^\n]*\.(?:jpg|jpeg|png|gif|bmp))'
    
    match = re.search(pattern, user_input, re.IGNORECASE)
    if match:
        path = match.group(1).strip()
        # Expand home directory
        if path.startswith("~"):
            path = os.path.expanduser(path)
        return path
    
    return None

def clean_agent_response(response: str) -> str:
    """
    Clean up the agent response by extracting actual content from JSON.
    """
    response_str = str(response).strip()
    
    # Remove "Action:" prefix if present
    if response_str.startswith("Action:"):
        response_str = response_str[7:].strip()
    
    # Try to parse as JSON
    try:
        # Remove markdown code block markers if present
        if response_str.startswith("```json"):
            response_str = response_str[7:]
        if response_str.startswith("```"):
            response_str = response_str[3:]
        if response_str.endswith("```"):
            response_str = response_str[:-3]
        response_str = response_str.strip()
        
        # Parse JSON
        if response_str.startswith("{"):
            data = json.loads(response_str)
            # Extract action_input from agent action
            if 'action_input' in data:
                return str(data['action_input'])
    except json.JSONDecodeError:
        pass
    
    # If not JSON, return as-is
    return response_str

def detect_disease_type(user_input: str) -> str:
    """
    Detect if the user is asking about skin or eye disease.
    Returns 'skin', 'eye', or None
    """
    user_lower = user_input.lower()
    
    for keyword in SKIN_KEYWORDS:
        if keyword in user_lower:
            return "skin"
    
    for keyword in EYE_KEYWORDS:
        if keyword in user_lower:
            return "eye"
    
    return None

def run_chat():
    print("\n🐾 Pet AI Healthcare Chatbot Started")
    print("=" * 60)
    print("Welcome! I'm your veterinary assistant.")
    print("I can help with general pet health questions and diagnose")
    print("specific skin or eye issues with image analysis.\n")
    
    # Get pet type from user
    while True:
        animal = input("What type of pet do you have? (dog/cat): ").strip().lower()
        if animal in ["dog", "cat"]:
            break
        print("❌ Please enter 'dog' or 'cat'")
    
    print(f"\n✅ Great! I'll help you with your {animal.upper()}'s health.\n")
    
    # Track disease type and analysis across conversation turns
    current_disease_type = None
    analysis_done = False  # Track if we've already analyzed an image
    
    conversation_active = True
    while conversation_active:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["exit", "quit", "bye"]:
                print("Bot: Goodbye! Take care of your pet! 🐾")
                conversation_active = False
                break
            
            # Detect disease type from current message
            detected_disease_type = detect_disease_type(user_input)
            
            # Update current disease type if a new one is detected
            # Otherwise, keep the previous disease type for context
            if detected_disease_type:
                # If switching to a different disease, reset analysis flag
                if detected_disease_type != current_disease_type:
                    analysis_done = False
                current_disease_type = detected_disease_type
            
            disease_type = current_disease_type  # Use tracked disease type
            
            # Build context for the agent
            if disease_type:
                # Extract image path if provided
                image_path = extract_image_path(user_input)
                
                if image_path and os.path.isfile(image_path):
                    # SPECIAL CASE: User has skin/eye issue + provided image
                    # Call the tool directly to ensure we get the analysis
                    print("\n📸 Analyzing image with computer vision model...\n")
                    
                    from chatbot.tools import _analyze_pet_image_impl
                    try:
                        # Call the implementation function directly (not the @tool decorated version)
                        tool_result = _analyze_pet_image_impl(
                            image_path=image_path,
                            animal=animal,
                            disease_type=disease_type
                        )
                        
                        # Check if tool returned an error
                        if isinstance(tool_result, dict) and "error" in tool_result:
                            error_msg = tool_result['error']
                            print(f"Bot: I encountered an error while analyzing the image: {error_msg}")
                            print("     Please try again with a different image file.\n")
                            continue
                        else:
                            # Tool succeeded - use RAG to explain the diagnosis
                            disease_class = tool_result.get('class', 'Unknown')
                            confidence = tool_result.get('confidence', 'N/A')
                            
                            print("🔍 Searching knowledge base for detailed information...\n")
                            
                            # First, try to get RAG context for this disease
                            try:
                                retriever = get_advanced_retriever()
                                search_results = retriever.search(query=f"{disease_class} {disease_type} in {animal}s", top_k=5)
                                
                                # Filter results by confidence threshold
                                rag_threshold = 0.7
                                relevant_results = [
                                    result for result in search_results
                                    if result.get('score', 0) >= rag_threshold
                                ]
                                
                                if relevant_results:
                                    # Build context from retrieved chunks
                                    rag_context = "\n\n".join([
                                        f"Source: {result.get('source', 'Unknown')}\n{result.get('content', '')}"
                                        for result in relevant_results
                                    ])
                                    
                                    # Use RAG context for explanation
                                    explanation_prompt = f"""You are a veterinary expert. Based on the computer vision analysis of a {animal}'s {disease_type}, the detected condition is: {disease_class} (with {confidence:.1%} confidence).

User's original description: {user_input}

Use the following knowledge base context to provide a detailed explanation:

Knowledge Base Context:
{rag_context}

Provide a detailed veterinary explanation covering:
1. What is {disease_class}?
2. Common causes and risk factors for this condition
3. Treatment options and recommendations
4. When to seek professional veterinary care
5. Prevention and management tips

Be thorough and informative. Use formatting with headers and bullet points for clarity."""
                                else:
                                    # Fall back to general knowledge if RAG threshold not met
                                    explanation_prompt = f"""You are a veterinary expert. Based on the computer vision analysis of a {animal}'s {disease_type}, the detected condition is: {disease_class} (with {confidence:.1%} confidence).

User's original description: {user_input}

Provide a detailed veterinary explanation covering:
1. What is {disease_class}?
2. Common causes and risk factors for this condition
3. Treatment options and recommendations
4. When to seek professional veterinary care
5. Prevention and management tips

Be thorough and informative. Use formatting with headers and bullet points for clarity."""
                                
                                # Call LLM with RAG context or general knowledge
                                llm_response = llm.invoke(explanation_prompt)
                                explanation_text = llm_response.content
                            except Exception as e:
                                # Fallback: If RAG retrieval fails, use general knowledge
                                explanation_prompt = f"""You are a veterinary expert. Based on the computer vision analysis of a {animal}'s {disease_type}, the detected condition is: {disease_class} (with {confidence:.1%} confidence).

User's original description: {user_input}

Provide a detailed veterinary explanation covering:
1. What is {disease_class}?
2. Common causes and risk factors for this condition
3. Treatment options and recommendations
4. When to seek professional veterinary care
5. Prevention and management tips

Be thorough and informative. Use formatting with headers and bullet points for clarity."""
                                
                                llm_response = llm.invoke(explanation_prompt)
                                explanation_text = llm_response.content
                            
                            print(f"Bot: {explanation_text}\n")
                            analysis_done = True  # Mark that we've done analysis
                            
                            # IMPORTANT: Save the specific diagnosis to memory
                            # This ensures follow-up questions can reference the exact diagnosis
                            diagnosis_record = f"Diagnosed with {disease_class} (confidence: {confidence:.1%}) from {disease_type} image analysis"
                            memory.save_context(
                                {"input": user_input},
                                {"output": diagnosis_record}
                            )
                            continue
                    except Exception as e:
                        error_msg = str(e)
                        print(f"Bot: I encountered an error while analyzing the image: {error_msg}")
                        print("     Please try again with a different image file.\n")
                        continue
                else:
                    # User hasn't provided image yet for skin/eye issue
                    if analysis_done:
                        # We already analyzed an image - this is a follow-up question
                        # Use RAG first, then fall back to general knowledge if needed
                        memory_vars = memory.load_memory_variables({})
                        conversation_history = memory_vars.get('chat_history', '')
                        
                        print("🔍 Searching knowledge base...\n")
                        
                        try:
                            retriever = get_advanced_retriever()
                            search_results = retriever.search(query=user_input, top_k=5)
                            
                            # Filter results by confidence threshold
                            rag_threshold = 0.7
                            relevant_results = [
                                result for result in search_results
                                if result.get('score', 0) >= rag_threshold
                            ]
                            
                            if relevant_results:
                                # Build context from retrieved chunks
                                rag_context = "\n\n".join([
                                    f"Source: {result.get('source', 'Unknown')}\n{result.get('content', '')}"
                                    for result in relevant_results
                                ])
                                
                                # Use RAG context for follow-up question
                                followup_prompt = f"""You are a veterinary expert. You have already diagnosed and discussed a {disease_type} condition with this {animal}.

Previous Conversation:
{conversation_history}

Use the following knowledge base context to answer the follow-up question:

Knowledge Base Context:
{rag_context}

User's follow-up question: {user_input}

IMPORTANT: Reference the specific diagnosis and previous discussion from the conversation history.
Answer using the knowledge base context, in the context of the condition previously diagnosed.
Provide helpful, accurate veterinary advice based on the question asked."""
                            else:
                                # Fall back to general knowledge if RAG threshold not met
                                followup_prompt = f"""You are a veterinary expert. You have already diagnosed and discussed a {disease_type} condition with this {animal}.

Previous Conversation:
{conversation_history}

User's follow-up question: {user_input}

IMPORTANT: You MUST reference the specific diagnosis and previous discussion from the conversation history above.
Answer this question in the context of the condition you previously diagnosed. 
Provide helpful, accurate veterinary advice based on the question asked."""
                            
                            llm_response = llm.invoke(followup_prompt)
                            followup_answer = llm_response.content
                        except Exception as e:
                            # Fallback: If RAG retrieval fails, use general knowledge
                            followup_prompt = f"""You are a veterinary expert. You have already diagnosed and discussed a {disease_type} condition with this {animal}.

Previous Conversation:
{conversation_history}

User's follow-up question: {user_input}

IMPORTANT: You MUST reference the specific diagnosis and previous discussion from the conversation history above.
Answer this question in the context of the condition you previously diagnosed. 
Provide helpful, accurate veterinary advice based on the question asked."""
                            
                            llm_response = llm.invoke(followup_prompt)
                            followup_answer = llm_response.content
                        
                        print(f"Bot: {followup_answer}\n")
                        
                        # Save follow-up to memory for continued context
                        memory.save_context(
                            {"input": user_input},
                            {"output": followup_answer}
                        )
                    else:
                        # First time for this disease - try RAG for initial info, then ask for image
                        print("🔍 Searching knowledge base for general information...\n")
                        
                        try:
                            retriever = get_advanced_retriever()
                            search_results = retriever.search(query=f"{disease_type} in {animal}s", top_k=5)
                            
                            # Filter results by confidence threshold
                            rag_threshold = 0.7
                            relevant_results = [
                                result for result in search_results
                                if result.get('score', 0) >= rag_threshold
                            ]
                            
                            if relevant_results:
                                # Build context from retrieved chunks
                                rag_context = "\n\n".join([
                                    f"Source: {result.get('source', 'Unknown')}\n{result.get('content', '')}"
                                    for result in relevant_results[:2]  # Use top 2 for initial info
                                ])
                                
                                # Provide RAG-based initial information and ask for image
                                initial_prompt = f"""You are a veterinary expert. The user is asking about a {disease_type} issue in their {animal}.

Based on knowledge base information about {disease_type} in {animal}s:

Knowledge Base Context:
{rag_context}

User's description: {user_input}

Provide a brief initial response mentioning what the knowledge base says about {disease_type}, then ask the user to upload a clear image of the affected {disease_type} area for proper diagnosis. 
Guide them to provide the image file path."""
                                
                                llm_response = llm.invoke(initial_prompt)
                                clean_response = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)
                            else:
                                # Fall back to agent if no RAG context available
                                enriched_input = f"""
                        Pet Type: {animal}
                        Issue Type: {disease_type} disease
                        
                        User Query: {user_input}
                        
                        The user is asking about a {disease_type} issue. Ask them to upload a clear image
                        so you can provide a proper diagnosis. Guide them to provide the image file path.
                        Do NOT use the tool yet. Just ask for the image.
                        """
                                response = agent.run(enriched_input)
                                clean_response = clean_agent_response(response)
                        
                        except Exception as e:
                            # Fallback to agent on any error
                            enriched_input = f"""
                        Pet Type: {animal}
                        Issue Type: {disease_type} disease
                        
                        User Query: {user_input}
                        
                        The user is asking about a {disease_type} issue. Ask them to upload a clear image
                        so you can provide a proper diagnosis. Guide them to provide the image file path.
                        Do NOT use the tool yet. Just ask for the image.
                        """
                            response = agent.run(enriched_input)
                            clean_response = clean_agent_response(response)
                        
                        print(f"Bot: {clean_response}\n")
                        
                        # Save to memory
                        memory.save_context(
                            {"input": user_input},
                            {"output": clean_response}
                        )
            else:
                # General health question (no disease keywords detected)
                # Use RAG retriever to get knowledge base context
                analysis_done = False  # Reset for general questions
                
                # Get conversation history from memory for better context
                memory_vars = memory.load_memory_variables({})
                conversation_history = memory_vars.get('chat_history', '')
                
                # Check if there was a previous diagnosis in the conversation
                has_previous_diagnosis = False
                if conversation_history:
                    # Look for diagnosis records in history (they contain "Diagnosed with")
                    has_previous_diagnosis = 'Diagnosed with' in conversation_history or any(
                        disease in conversation_history.lower() 
                        for disease in ['dermatitis', 'mange', 'infection', 'blepharitis', 'keratitis', 'conjunctiv']
                    )
                
                # Get RAG context from knowledge base
                print("🔍 Searching knowledge base...\n")
                try:
                    retriever = get_advanced_retriever()
                    search_results = retriever.search(query=user_input, top_k=3)
                    
                    # Filter results by confidence threshold (0.7 for RAG, fallback to general knowledge below that)
                    rag_threshold = 0.7
                    relevant_results = [
                        result for result in search_results
                        if result.get('score', 0) >= rag_threshold
                    ]
                    
                    if relevant_results:
                        # Build context from retrieved chunks
                        rag_context = "\n\n".join([
                            f"Source: {result.get('source', 'Unknown')}\n{result.get('content', '')}"
                            for result in relevant_results
                        ])
                        
                        # Build prompt with RAG context and conversation history
                        if conversation_history and has_previous_diagnosis:
                            # Include both retrieved context AND previous diagnosis
                            rag_prompt = f"""You are a helpful veterinary AI assistant.

Pet Type: {animal}

Previous Diagnosis Context:
{conversation_history}

Use the following retrieved context from the knowledge base to answer the current question:

Retrieved Knowledge Base Context:
{rag_context}

Current User Question: {user_input}

IMPORTANT INSTRUCTIONS:
1. Use the retrieved knowledge base context to provide accurate information.
2. Reference the previous diagnosis where relevant.
3. Answer the current question using both the retrieved context and the conversation history.
4. Be specific and provide detailed veterinary advice.
5. Do NOT ask for images. Just provide helpful guidance based on the information available."""
                        else:
                            # Just use retrieved context for new topic
                            rag_prompt = f"""You are a helpful veterinary AI assistant.

Pet Type: {animal}

Use the following retrieved context from the knowledge base to answer the question as accurately as possible:

Retrieved Knowledge Base Context:
{rag_context}

User Question: {user_input}

Answer based on the retrieved context. Provide detailed, accurate veterinary advice."""
                        
                        # Call LLM with RAG context
                        llm_response = llm.invoke(rag_prompt)
                        clean_response = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)
                    else:
                        # No relevant context found - fall back to agent
                        if conversation_history:
                            if has_previous_diagnosis:
                                prompt = f"""You are a veterinary expert assistant. 
                        
Pet Type: {animal}

Previous Conversation (including a specific medical diagnosis):
{conversation_history}

Current User Question: {user_input}

IMPORTANT: You MUST reference the previous conversation and any diagnosis that was made.
Provide helpful, accurate veterinary advice based on the question asked."""
                            else:
                                prompt = f"""You are a veterinary expert assistant. 
                        
Pet Type: {animal}

Previous Conversation:
{conversation_history}

Current User Question: {user_input}

IMPORTANT: You MUST reference the previous conversation when answering."""
                            
                            llm_response = llm.invoke(prompt)
                            clean_response = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)
                        else:
                            # Use agent for first general question
                            enriched_input = f"""
                Pet Type: {animal}
                Issue Type: General health question
                
                User Query: {user_input}
                
                This is a general health question. Answer it directly with veterinary advice.
                Do NOT ask for images. Just provide helpful guidance.
                """
                            
                            llm_response = agent.run(enriched_input)
                            clean_response = clean_agent_response(llm_response)
                    
                    print(f"Bot: {clean_response}\n")
                    
                    # Save all responses to memory for context in future turns
                    memory.save_context(
                        {"input": user_input},
                        {"output": clean_response}
                    )
                
                except Exception as e:
                    # Fallback to agent on any error
                    print(f"⚠️  Knowledge base search encountered an issue, using general knowledge..\n")
                    if conversation_history:
                        if has_previous_diagnosis:
                            prompt = f"""You are a veterinary expert assistant. 
                        
Pet Type: {animal}

Previous Conversation (including a specific medical diagnosis):
{conversation_history}

Current User Question: {user_input}

IMPORTANT: You MUST reference the previous conversation and any diagnosis that was made.
Provide helpful, accurate veterinary advice based on the question asked."""
                        else:
                            prompt = f"""You are a veterinary expert assistant. 
                        
Pet Type: {animal}

Previous Conversation:
{conversation_history}

Current User Question: {user_input}

IMPORTANT: You MUST reference the previous conversation when answering."""
                        
                        llm_response = llm.invoke(prompt)
                        clean_response = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)
                    else:
                        enriched_input = f"""
                Pet Type: {animal}
                Issue Type: General health question
                
                User Query: {user_input}
                
                This is a general health question. Answer it directly with veterinary advice.
                """
                        
                        llm_response = agent.run(enriched_input)
                        clean_response = clean_agent_response(llm_response)
                    
                    print(f"Bot: {clean_response}\n")
                    memory.save_context(
                        {"input": user_input},
                        {"output": clean_response}
                    )
        
        except KeyboardInterrupt:
            print("\n\nBot: Goodbye! 🐾")
            conversation_active = False
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            print("Please try again.\n")


if __name__ == "__main__":
    # Initialize LangSmith tracing (optional)
    setup_langsmith()
    
    # Start the chatbot
    run_chat()