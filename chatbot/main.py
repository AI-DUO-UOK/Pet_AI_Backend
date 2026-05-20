import re
import os
import json
from pathlib import Path
from chatbot.agent import agent
from chatbot.llm import llm
from chatbot.memory import memory
from chatbot.langsmith_config import setup_langsmith
from chatbot.rag.agentic_rag import query_agentic_rag  # Import intelligent agentic RAG

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
                            # Tool succeeded - use agentic RAG to explain the diagnosis
                            disease_class = tool_result.get('class', 'Unknown')
                            confidence = tool_result.get('confidence', 'N/A')
                            
                            # Use agentic RAG - agent will decide whether to search knowledge base
                            explanation_query = f"""The computer vision model detected {disease_class} (confidence: {confidence:.1%}) from a {animal}'s {disease_type} image.

User's original description: {user_input}

Provide a detailed veterinary explanation covering:
1. What is {disease_class}?
2. Common causes and risk factors for this condition
3. Treatment options and recommendations
4. When to seek professional veterinary care
5. Prevention and management tips

Be thorough and informative. Use formatting with headers and bullet points for clarity."""
                            
                            # Get conversation history for context
                            memory_vars = memory.load_memory_variables({})
                            chat_history = memory_vars.get('chat_history', '')
                            
                            # Agent decides whether to use RAG
                            explanation_text = query_agentic_rag(
                                question=explanation_query,
                                chat_history=chat_history
                            )
                            
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
                        
                        # Use agentic RAG for follow-up question - agent decides if RAG is needed
                        followup_query = f"""You have already diagnosed and discussed a {disease_type} condition with this {animal}.

Previous Conversation:
{conversation_history}

User's follow-up question: {user_input}

IMPORTANT: Reference the specific diagnosis and previous discussion from the conversation history.
Answer this question in the context of the condition previously diagnosed. 
Provide helpful, accurate veterinary advice based on the question asked."""
                        
                        # Agent decides whether to use RAG
                        followup_answer = query_agentic_rag(
                            question=followup_query,
                            chat_history=conversation_history
                        )
                        
                        print(f"Bot: {followup_answer}\n")
                        
                        # Save follow-up to memory for continued context
                        memory.save_context(
                            {"input": user_input},
                            {"output": followup_answer}
                        )
                    else:
                        # First time for this disease - ask for image WITHOUT searching knowledge base
                        # RAG search will only happen AFTER the CV model analyzes the image
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
                
                # Use agentic RAG - let the agent decide whether to search knowledge base or answer directly
                # This is intelligent routing that avoids unnecessary retrieval
                pet_query = f"""Pet Type: {animal}

Previous Conversation:
{conversation_history}

Current User Question: {user_input}

If this is a veterinary/medical question, search the knowledge base for accurate information.
If this is casual conversation or personal information, answer directly without searching.
Be smart about deciding whether retrieval is necessary."""
                
                # Agent decides: use RAG or answer directly
                clean_response = query_agentic_rag(
                    question=pet_query,
                    chat_history=conversation_history
                )
                
                print(f"Bot: {clean_response}\n")
                
                # Save all responses to memory for context in future turns
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