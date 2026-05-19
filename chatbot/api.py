"""
FastAPI wrapper for Pet AI Chatbot
Exposes the chatbot as a REST API without modifying existing logic
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uuid
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from chatbot.rag.agentic_rag import query_agentic_rag
from chatbot.memory import ConversationMemory
from chatbot.tools import _analyze_pet_image_impl
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Pet AI Chatbot API",
    description="API for AI-powered pet health assistant",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (change in production)
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


class AnalysisResult(BaseModel):
    """Image analysis result"""
    class_name: str
    confidence: float
    error: Optional[str] = None


# ============= Session Management =============

class SessionManager:
    """Manage chat sessions and conversation memory"""
    
    def __init__(self):
        self.sessions: dict[str, dict] = {}
    
    def create_session(self, pet_type: str) -> str:
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        
        if pet_type.lower() not in ["dog", "cat"]:
            raise ValueError("Pet type must be 'dog' or 'cat'")
        
        # Initialize session with memory
        self.sessions[session_id] = {
            "pet_type": pet_type.lower(),
            "memory": ConversationMemory(),
            "current_disease_type": None,
            "analysis_done": False
        }
        
        logger.info(f"Created session {session_id} for {pet_type}")
        return session_id
    
    def get_session(self, session_id: str) -> dict:
        """Get session info"""
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


# ============= Helper Functions =============

def extract_image_path(user_input: str) -> str:
    """Extract image file path from user input"""
    # Look for common image patterns
    for word in user_input.split():
        if any(word.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']):
            if os.path.exists(word):
                return word
    return ""


def detect_disease_type(user_input: str) -> str:
    """Detect disease type from user input"""
    user_lower = user_input.lower()
    
    skin_keywords = ["skin", "rash", "itching", "scratching", "dermatitis", "bumps", "lesion", "wound"]
    eye_keywords = ["eye", "vision", "see", "blind", "discharge", "redness", "squinting"]
    
    has_skin = any(keyword in user_lower for keyword in skin_keywords)
    has_eye = any(keyword in user_lower for keyword in eye_keywords)
    
    if has_skin:
        return "skin"
    elif has_eye:
        return "eye"
    else:
        return None


def clean_agent_response(response: str) -> str:
    """Clean agent response from markdown/JSON formatting"""
    if response.startswith('```'):
        # Remove markdown code blocks
        response = response.split('```')[1]
        if response.startswith('json'):
            response = response[4:]
    
    response = response.strip()
    return response


def parse_rag_response(response: str) -> tuple[str, Optional[dict]]:
    """
    Parse RAG response to extract analysis data if present
    Returns: (message_text, analysis_data_dict or None)
    """
    # Try to parse if it looks like structured data
    import json
    
    # Check if response contains JSON-like structure
    if "{" in response and "}" in response:
        try:
            # Try to extract JSON from response
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            json_str = response[start_idx:end_idx]
            data = json.loads(json_str)
            
            # Check if it has analysis structure
            if all(key in data for key in ["condition", "confidence", "actions"]):
                return response, data
        except (json.JSONDecodeError, ValueError):
            pass
    
    return response, None


# ============= API Endpoints =============

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
        return SessionInfo(
            session_id=session_id,
            pet_type=session["pet_type"],
            messages_count=len(session["memory"].messages) if hasattr(session["memory"], 'messages') else 0
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/sessions/{session_id}/chat", response_model=ChatResponse)
async def chat(session_id: str, message: ChatMessage) -> ChatResponse:
    """
    Send a message in the chat session
    Returns AI response with optional analysis data
    """
    try:
        session = session_manager.get_session(session_id)
        pet_type = session["pet_type"]
        memory = session["memory"]
        
        user_input = message.content
        
        # Detect disease type from user input
        disease_type = detect_disease_type(user_input)
        if disease_type:
            session["current_disease_type"] = disease_type
        
        # Build chat history for context
        chat_history = ""
        if hasattr(memory, 'messages'):
            for msg in memory.messages[-6:]:  # Last 6 messages for context
                chat_history += f"\n{msg}"
        
        # Get response from agentic RAG
        logger.info(f"Processing message for session {session_id}: {user_input[:50]}")
        response_text = query_agentic_rag(user_input, chat_history)
        response_text = clean_agent_response(response_text)
        
        # Try to parse analysis data from response
        parsed_response, analysis_data = parse_rag_response(response_text)
        
        # Save to memory
        memory.save_response(response_text)
        memory.save_question(user_input)
        
        is_analysis = analysis_data is not None
        
        logger.info(f"Response generated (analysis: {is_analysis})")
        
        return ChatResponse(
            message=parsed_response,
            is_analysis=is_analysis,
            analysis_data=analysis_data
        )
        
    except ValueError as e:
        logger.error(f"Session error: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


@app.post("/api/sessions/{session_id}/analyze-image", response_model=AnalysisResult)
async def analyze_image(session_id: str, file: UploadFile = File(...)) -> AnalysisResult:
    """
    Analyze an uploaded pet image
    Returns disease classification and confidence
    """
    try:
        session = session_manager.get_session(session_id)
        pet_type = session["pet_type"]
        
        # Save uploaded file temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            contents = await file.read()
            tmp_file.write(contents)
            tmp_path = tmp_file.name
        
        try:
            # Analyze image using existing CV tools
            result = _analyze_pet_image_impl(tmp_path, pet_type)
            
            logger.info(f"Image analysis for {pet_type}: {result.get('class', 'unknown')}")
            
            return AnalysisResult(
                class_name=result.get('class', 'unknown'),
                confidence=result.get('confidence', 0.0),
                error=result.get('error')
            )
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    except ValueError as e:
        logger.error(f"Session error: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing image: {str(e)}")


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session"""
    try:
        session_manager.delete_session(session_id)
        return {"status": "deleted", "session_id": session_id}
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Pet AI Chatbot API"}


# ============= Main =============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
