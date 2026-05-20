"""
FastAPI wrapper for Pet AI Chatbot
Exposes the chatbot as a REST API by importing and using existing chatbot logic
NO changes to chatbot behavior - just wraps existing functions with REST endpoints
"""

import os
import sys
import uuid
import json
import logging
import re
import tempfile
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import existing chatbot modules - EXACT same as main.py uses
from chatbot.memory import SimpleConversationMemory
from chatbot.rag.agentic_rag import query_agentic_rag
from chatbot.tools import _analyze_pet_image_impl

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Pet AI Chatbot API",
    description="REST API wrapper for Pet AI Chatbot",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= Models =============

class ChatMessage(BaseModel):
    """User message in the chat"""
    content: str
    include_image: Optional[bool] = False


class ChatResponse(BaseModel):
    """AI response to user message"""
    message: str
    is_analysis: bool = False
    analysis_data: Optional[dict] = None


class SessionInit(BaseModel):
    """Initialize a new chat session"""
    pet_type: str  # "dog" or "cat"


class SessionInfo(BaseModel):
    """Information about a chat session"""
    session_id: str
    pet_type: str
    messages_count: int


# ============= Disease Detection (EXACT same as main.py) =============

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


def detect_disease_type(user_input: str) -> str:
    """
    Detect if the user is asking about skin or eye disease.
    Returns 'skin', 'eye', or None
    EXACT same logic as main.py
    """
    user_lower = user_input.lower()
    
    for keyword in SKIN_KEYWORDS:
        if keyword in user_lower:
            return "skin"
    
    for keyword in EYE_KEYWORDS:
        if keyword in user_lower:
            return "eye"
    
    return None


def extract_image_path(user_input: str) -> str:
    """
    Extract image file path from user input.
    EXACT same logic as main.py
    """
    pattern = r'(/[^\n]*\.(?:jpg|jpeg|png|gif|bmp)|~/[^\n]*\.(?:jpg|jpeg|png|gif|bmp))'
    
    match = re.search(pattern, user_input, re.IGNORECASE)
    if match:
        path = match.group(1).strip()
        if path.startswith("~"):
            path = os.path.expanduser(path)
        return path
    
    return None

# ============= Session Management =============

class SessionManager:
    """Manage chat sessions with conversation memory"""
    
    def __init__(self):
        self.sessions: dict[str, dict] = {}
    
    def create_session(self, pet_type: str) -> str:
        """Create a new chat session with memory"""
        session_id = str(uuid.uuid4())
        
        if pet_type.lower() not in ["dog", "cat"]:
            raise ValueError("Pet type must be 'dog' or 'cat'")
        
        # Initialize session with SimpleConversationMemory (EXACT same as existing code)
        self.sessions[session_id] = {
            "pet_type": pet_type.lower(),
            "memory": SimpleConversationMemory(),
            "current_disease_type": None,
            "analysis_done": False
        }
        
        logger.info(f"Created session {session_id} for {pet_type}")
        return session_id
    
    def get_session(self, session_id: str) -> dict:
        """Get session"""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        return self.sessions[session_id]
    
    def delete_session(self, session_id: str) -> None:
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted session {session_id}")


# Global session manager
session_manager = SessionManager()


@app.post("/api/sessions", response_model=SessionInfo)
async def create_session(session_init: SessionInit) -> SessionInfo:
    """Create a new chat session"""
    try:
        session_id = session_manager.create_session(session_init.pet_type)
        session = session_manager.get_session(session_id)
        
        return SessionInfo(
            session_id=session_id,
            pet_type=session["pet_type"],
            messages_count=0
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/sessions/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str) -> SessionInfo:
    """Get session information"""
    try:
        session = session_manager.get_session(session_id)
        memory = session["memory"]
        msg_count = len(memory.messages_list)
        
        return SessionInfo(
            session_id=session_id,
            pet_type=session["pet_type"],
            messages_count=msg_count
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/sessions/{session_id}/chat", response_model=ChatResponse)
async def chat(session_id: str, message: ChatMessage) -> ChatResponse:
    """
    Send a message in the chat session
    Uses EXACT same logic as main.py - no changes to chatbot behavior
    """
    try:
        session = session_manager.get_session(session_id)
        pet_type = session["pet_type"]
        memory = session["memory"]
        
        user_input = message.content
        
        # Detect disease type from current message (EXACT same as main.py)
        detected_disease_type = detect_disease_type(user_input)
        
        # Update current disease type if a new one is detected
        if detected_disease_type:
            if detected_disease_type != session["current_disease_type"]:
                session["analysis_done"] = False
            session["current_disease_type"] = detected_disease_type
        
        disease_type = session["current_disease_type"]
        
        # Build response using exact same logic as main.py
        if disease_type:
            # Extract image path if provided
            image_path = extract_image_path(user_input)
            
            if image_path and os.path.isfile(image_path):
                # EXACT same logic as main.py: analyze image
                try:
                    # Call the implementation function directly (EXACT same as main.py)
                    tool_result = _analyze_pet_image_impl(
                        image_path=image_path,
                        animal=pet_type,
                        disease_type=disease_type
                    )
                    
                    # Check if tool returned an error
                    if isinstance(tool_result, dict) and "error" in tool_result:
                        error_msg = tool_result['error']
                        response_text = f"I encountered an error while analyzing the image: {error_msg}"
                        memory.add_user_message(user_input)
                        memory.add_ai_message(response_text)
                        
                        return ChatResponse(
                            message=response_text,
                            is_analysis=False
                        )
                    else:
                        # Tool succeeded - use agentic RAG to explain diagnosis (EXACT same as main.py)
                        disease_class = tool_result.get('class', 'Unknown')
                        confidence = tool_result.get('confidence', 'N/A')
                        
                        # Use agentic RAG - EXACT same as main.py
                        explanation_query = f"""The computer vision model detected {disease_class} (confidence: {confidence:.1%}) from a {pet_type}'s {disease_type} image.

User's original description: {user_input}

Provide a detailed veterinary explanation covering:
1. What is {disease_class}?
2. Common causes and risk factors for this condition
3. Treatment options and recommendations
4. When to seek professional veterinary care
5. Prevention and management tips

Be thorough and informative. Use formatting with headers and bullet points for clarity."""
                        
                        # Get conversation history for context (EXACT same as main.py)
                        memory_vars = memory.load_memory_variables({})
                        chat_history = memory_vars.get('chat_history', '')
                        
                        # Agent decides whether to use RAG (EXACT same as main.py)
                        explanation_text = query_agentic_rag(
                            question=explanation_query,
                            chat_history=chat_history
                        )
                        
                        session["analysis_done"] = True
                        
                        # Save to memory (EXACT same as main.py)
                        memory.add_user_message(user_input)
                        diagnosis_record = f"Diagnosed with {disease_class} (confidence: {confidence:.1%}) from {disease_type} image analysis"
                        memory.add_ai_message(diagnosis_record)
                        
                        return ChatResponse(
                            message=explanation_text,
                            is_analysis=True,
                            analysis_data={
                                "class": disease_class,
                                "confidence": float(confidence) if isinstance(confidence, (int, float)) else 0.0
                            }
                        )
                except Exception as e:
                    error_msg = str(e)
                    response_text = f"I encountered an error while analyzing the image: {error_msg}"
                    memory.add_user_message(user_input)
                    memory.add_ai_message(response_text)
                    
                    return ChatResponse(message=response_text, is_analysis=False)
            else:
                # No image provided for disease type
                # Use agentic RAG (EXACT same as main.py)
                memory_vars = memory.load_memory_variables({})
                conversation_history = memory_vars.get('chat_history', '')
                
                # Agent decides whether to use RAG (EXACT same as main.py)
                clean_response = query_agentic_rag(
                    question=user_input,
                    chat_history=conversation_history
                )
                
                # Save to memory (EXACT same as main.py)
                memory.add_user_message(user_input)
                memory.add_ai_message(clean_response)
                
                return ChatResponse(message=clean_response, is_analysis=False)
        else:
            # General health question - no disease keywords detected
            # Use agentic RAG (EXACT same as main.py)
            session["analysis_done"] = False
            
            memory_vars = memory.load_memory_variables({})
            conversation_history = memory_vars.get('chat_history', '')
            
            # Agent decides whether to use RAG (EXACT same as main.py)
            pet_query = f"""Pet Type: {pet_type}

Previous Conversation:
{conversation_history}

Current User Question: {user_input}

If this is a veterinary/medical question, search the knowledge base for accurate information.
If this is casual conversation or personal information, answer directly without searching.
Be smart about deciding whether retrieval is necessary."""
            
            clean_response = query_agentic_rag(
                question=pet_query,
                chat_history=conversation_history
            )
            
            # Save to memory (EXACT same as main.py)
            memory.add_user_message(user_input)
            memory.add_ai_message(clean_response)
            
            return ChatResponse(message=clean_response, is_analysis=False)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Chat error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions/{session_id}/analyze-image")
async def analyze_image(session_id: str, file: UploadFile = File(...)):
    """
    Analyze an uploaded pet image
    Uses EXACT same logic as tools.py
    """
    try:
        session = session_manager.get_session(session_id)
        pet_type = session["pet_type"]
        memory = session["memory"]
        
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Detect disease type - try to infer from context
            # For API uploads without context, try both skin and eye
            for disease_type in ["skin", "eye"]:
                result = _analyze_pet_image_impl(
                    image_path=tmp_path,
                    animal=pet_type,
                    disease_type=disease_type
                )
                
                if not isinstance(result, dict) or "error" not in result:
                    return result
            
            # If both failed, return error
            return {"error": "Could not analyze image for skin or eye conditions"}
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Image analysis error")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session"""
    try:
        session_manager.delete_session(session_id)
        return {"message": f"Session {session_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Pet AI Chatbot API"}


# ============= Main =============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
