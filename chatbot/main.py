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

def prompt_pet_type() -> str:
    """Prompt the user for pet type (dog/cat)."""
    while True:
        animal = input("What type of pet do you have? (dog/cat): ").strip().lower()
        if animal in ["dog", "cat"]:
            return animal
        print("❌ Please enter 'dog' or 'cat'")


def process_image_analysis(image_path: str, animal: str, disease_type: str, user_input: str) -> str:
    """Perform image analysis using vision model and explain via RAG."""
    print("\n📸 Analyzing image with computer vision model...\n")
    from chatbot.tools import _analyze_pet_image_impl
    
    tool_result = _analyze_pet_image_impl(
        image_path=image_path,
        animal=animal,
        disease_type=disease_type
    )
    
    if isinstance(tool_result, dict) and "error" in tool_result:
        raise RuntimeError(tool_result['error'])
        
    disease_class = tool_result.get('class', 'Unknown')
    confidence = tool_result.get('confidence', 0.0)
    
    explanation_query = f"""The computer vision model detected {disease_class} (confidence: {confidence:.1%}) from a {animal}'s {disease_type} image.

User's original description: {user_input}

Provide a detailed veterinary explanation covering:
1. What is {disease_class}?
2. Common causes and risk factors for this condition
3. Treatment options and recommendations
4. When to seek professional veterinary care
5. Prevention and management tips

Be thorough and informative. Use formatting with headers and bullet points for clarity."""
    
    chat_history = memory.load_memory_variables({}).get('chat_history', '')
    explanation_text = query_agentic_rag(
        question=explanation_query,
        chat_history=chat_history
    )
    
    diagnosis_record = f"Diagnosed with {disease_class} (confidence: {confidence:.1%}) from {disease_type} image analysis"
    memory.save_context({"input": user_input}, {"output": diagnosis_record})
    return explanation_text


def process_followup(user_input: str, animal: str, disease_type: str) -> str:
    """Process follow-up questions for a previously diagnosed disease."""
    chat_history = memory.load_memory_variables({}).get('chat_history', '')
    
    followup_query = f"""You have already diagnosed and discussed a {disease_type} condition with this {animal}.

Previous Conversation:
{chat_history}

User's follow-up question: {user_input}

IMPORTANT: Reference the specific diagnosis and previous discussion from the conversation history.
Answer this question in the context of the condition previously diagnosed. 
Provide helpful, accurate veterinary advice based on the question asked."""
    
    answer = query_agentic_rag(
        question=followup_query,
        chat_history=chat_history
    )
    memory.save_context({"input": user_input}, {"output": answer})
    return answer


def process_disease_image_request(user_input: str, animal: str, disease_type: str) -> str:
    """Prompt user to provide an image path for the matched disease."""
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
    memory.save_context({"input": user_input}, {"output": clean_response})
    return clean_response


def process_general_query(user_input: str, animal: str) -> str:
    """Process general queries not matched to disease types using Agentic RAG."""
    chat_history = memory.load_memory_variables({}).get('chat_history', '')
    
    pet_query = f"""Pet Type: {animal}

Previous Conversation:
{chat_history}

Current User Question: {user_input}

If this is a veterinary/medical question, search the knowledge base for accurate information.
If this is casual conversation or personal information, answer directly without searching.
Be smart about deciding whether retrieval is necessary."""
    
    response = query_agentic_rag(
        question=pet_query,
        chat_history=chat_history
    )
    memory.save_context({"input": user_input}, {"output": response})
    return response


def run_chat():
    print("\n🐾 Pet AI Healthcare Chatbot Started")
    print("=" * 60)
    print("Welcome! I'm your veterinary assistant.")
    print("I can help with general pet health questions and diagnose")
    print("specific skin or eye issues with image analysis.\n")
    
    animal = prompt_pet_type()
    print(f"\n✅ Great! I'll help you with your {animal.upper()}'s health.\n")
    
    current_disease_type = None
    analysis_done = False
    
    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            
            if user_input.lower() in ["exit", "quit", "bye"]:
                print("Bot: Goodbye! Take care of your pet! 🐾")
                break
            
            detected_disease = detect_disease_type(user_input)
            if detected_disease:
                if detected_disease != current_disease_type:
                    analysis_done = False
                current_disease_type = detected_disease
            
            disease_type = current_disease_type
            
            if disease_type:
                image_path = extract_image_path(user_input)
                
                if image_path and os.path.isfile(image_path):
                    try:
                        bot_response = process_image_analysis(image_path, animal, disease_type, user_input)
                        analysis_done = True
                        print(f"Bot: {bot_response}\n")
                    except Exception as img_err:
                        print(f"Bot: I encountered an error while analyzing the image: {str(img_err)}")
                        print("     Please try again with a different image file.\n")
                elif analysis_done:
                    bot_response = process_followup(user_input, animal, disease_type)
                    print(f"Bot: {bot_response}\n")
                else:
                    bot_response = process_disease_image_request(user_input, animal, disease_type)
                    print(f"Bot: {bot_response}\n")
            else:
                analysis_done = False
                bot_response = process_general_query(user_input, animal)
                print(f"Bot: {bot_response}\n")
                
        except KeyboardInterrupt:
            print("\n\nBot: Goodbye! 🐾")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            print("Please try again.\n")


if __name__ == "__main__":
    setup_langsmith()
    run_chat()