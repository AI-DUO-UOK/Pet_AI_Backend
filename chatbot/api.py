"""
FastAPI endpoints for Pet AI Healthcare Chatbot

Connects frontend to backend without changing any chatbot logic.
Imports and reuses exact same functions as CLI chatbot.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, AsyncGenerator
import uuid
import os
import tempfile
import logging
import json
import asyncio

from chatbot.main import detect_disease_type, extract_image_path, clean_agent_response
from chatbot.tools import _analyze_pet_image_impl
from chatbot.rag.agentic_rag import query_agentic_rag
from chatbot.memory import SimpleConversationMemory
from chatbot.agent import agent
from chatbot.llm import llm
from chatbot.langsmith_config import setup_langsmith

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Pet AI Healthcare Chatbot API",
    description="Backend API for Pet AI Healthcare Chatbot",
    version="1.0.0"
)

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────────────────────

class StartConversationRequest(BaseModel):
    """Request to start a new conversation"""
    animal: str  # 'dog' or 'cat'
    user_id: Optional[str] = None  # Optional user identifier
    pet_id: Optional[str] = None  # Optional pet identifier for real user data

class StartConversationResponse(BaseModel):
    """Response when starting conversation"""
    session_id: str
    animal: str
    message: str

class SendMessageRequest(BaseModel):
    """Request to send a message in conversation"""
    session_id: str
    message: str

class SendMessageResponse(BaseModel):
    """Response to sent message"""
    session_id: str
    bot_response: str
    used_rag: bool
    disease_detected: Optional[str] = None

class UploadImageRequest(BaseModel):
    """Request to upload image for analysis"""
    session_id: str
    disease_type: str  # 'skin' or 'eye'

# ─────────────────────────────────────────────────────────────
# Session Management
# ─────────────────────────────────────────────────────────────

class ConversationSession:
    """Manages a single conversation session"""
    
    def __init__(self, session_id: str, animal: str, pet_profile: Optional[dict] = None):
        self.session_id = session_id
        self.animal = animal
        self.pet_profile = pet_profile or {}
        self.memory = SimpleConversationMemory()
        self.current_disease_type = None
        self.analysis_done = False
        self.pet_initialized = False
    
    def get_chat_history(self) -> str:
        """Get formatted chat history"""
        memory_vars = self.memory.load_memory_variables({})
        return memory_vars.get('chat_history', '')

# Store active sessions
_sessions: Dict[str, ConversationSession] = {}

def get_session(session_id: str) -> ConversationSession:
    """Get conversation session by ID"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return _sessions[session_id]

# ─────────────────────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────────────────────

async def fetch_pet_profile(pet_id: str) -> Optional[dict]:
    """Fetch pet profile from the database by pet_id."""
    try:
        from chatbot.supabase_config import supabase
        response = supabase.table("pets").select("*").eq("id", pet_id).execute()
        if response.data:
            return response.data[0]
    except Exception as e:
        logger.warning(f"Could not fetch pet profile for {pet_id}: {e}")
    return None


@app.post("/api/chat/start", response_model=StartConversationResponse)
async def start_conversation(request: StartConversationRequest):
    """
    Start a new conversation session with pet type selection.
    
    This endpoint initializes a conversation and returns a session ID.
    The session ID is used for all subsequent messages.
    
    Args:
        request: Contains animal type ('dog' or 'cat'), optional pet_id for real user data
    
    Returns:
        Session ID and initial greeting
    """
    try:
        # Validate animal type
        if request.animal.lower() not in ["dog", "cat"]:
            raise HTTPException(status_code=400, detail="Animal must be 'dog' or 'cat'")
        
        # Create new session
        session_id = str(uuid.uuid4())
        animal = request.animal.lower()
        
        # Fetch pet profile if pet_id is provided
        pet_profile = None
        if request.pet_id:
            pet_profile = await fetch_pet_profile(request.pet_id)
            if pet_profile:
                logger.info(f"Fetched pet profile: {pet_profile.get('name')} for session {session_id}")
            else:
                logger.warning(f"Pet profile not found for pet_id: {request.pet_id}")
        
        session = ConversationSession(session_id, animal, pet_profile)
        _sessions[session_id] = session
        
        # Build welcome message
        if pet_profile:
            pet_name = pet_profile.get("name", "your pet")
            message = f"🐾 Welcome back!\n\nHi! I'm your AI Pet Health Assistant, and I'm here to help with {pet_name}'s health and wellbeing."
        else:
            message = f"✅ Great! I'll help you with your {animal.upper()}'s health. How can I assist you today?"
        
        logger.info(f"Created new session {session_id} for {animal}")
        
        return StartConversationResponse(
            session_id=session_id,
            animal=animal,
            message=message
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/message", response_model=SendMessageResponse)
async def send_message(request: SendMessageRequest):
    """
    Send a message in an existing conversation.
    
    This endpoint processes user messages using the exact same logic as CLI:
    - Detects disease type (skin/eye keywords)
    - Routes to agentic RAG for intelligent retrieval
    - Maintains conversation history
    
    Args:
        request: Contains session_id and message text
    
    Returns:
        Bot response and metadata
    """
    try:
        # Get session
        session = get_session(request.session_id)
        user_input = request.message.strip()
        
        if not user_input:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        animal = session.animal
        
        # Detect disease type from message (same as CLI)
        detected_disease_type = detect_disease_type(user_input)
        
        if detected_disease_type:
            # Update current disease type if new one detected
            if detected_disease_type != session.current_disease_type:
                session.analysis_done = False
            session.current_disease_type = detected_disease_type
            disease_type = session.current_disease_type
        else:
            # No disease keywords in current message - reset disease type
            # to prevent non-disease questions from being routed to disease flow
            disease_type = None
            session.current_disease_type = None
        bot_response = ""
        used_rag = False
        
        # Handle disease-specific flow
        if disease_type:
            # Check if image path is provided
            image_path = extract_image_path(user_input)
            
            if image_path and os.path.isfile(image_path):
                # Analyze image using CV model
                bot_response = await handle_image_analysis(
                    session, image_path, animal, disease_type, user_input
                )
            else:
                # Ask for image or handle follow-up
                if session.analysis_done:
                    # Follow-up question after analysis
                    chat_history = session.get_chat_history()
                    followup_query = f"""You have already diagnosed and discussed a {disease_type} condition with this {animal}.

Previous Conversation:
{chat_history}

User's follow-up question: {user_input}

IMPORTANT: Reference the specific diagnosis and previous discussion from the conversation history.
Answer this question in the context of the condition previously diagnosed. 
Provide helpful, accurate veterinary advice based on the question asked."""
                    
                    bot_response = query_agentic_rag(
                        question=followup_query,
                        chat_history=chat_history
                    )
                    used_rag = True
                else:
                    # Ask for image (using agent)
                    enriched_input = f"""
Pet Type: {animal}
Issue Type: {disease_type} disease

User Query: {user_input}

The user is asking about a {disease_type} issue. Ask them to upload a clear image
so you can provide a proper diagnosis. Guide them to provide the image file path.
Do NOT use the tool yet. Just ask for the image."""
                    
                    response = agent.run(enriched_input)
                    bot_response = clean_agent_response(response)
        else:
            # General health question - use agentic RAG
            chat_history = session.get_chat_history()
            
            # Inject pet profile context on the very first message only
            # IMPORTANT: Add to chat_history, NOT to the question string,
            # because the question is checked by is_skin_or_eye_issue()
            # and pet profile fields (like "Allergies") could trigger false matches.
            if session.pet_profile and not session.pet_initialized:
                pp = session.pet_profile
                pet_info_parts = []
                if pp.get("name"):
                    pet_info_parts.append(f"Name: {pp['name']}")
                pet_info_parts.append(f"Type: {animal}")
                if pp.get("breed"):
                    pet_info_parts.append(f"Breed: {pp['breed']}")
                if pp.get("date_of_birth"):
                    pet_info_parts.append(f"Date of Birth: {pp['date_of_birth']}")
                if pp.get("weight"):
                    pet_info_parts.append(f"Weight: {pp['weight']} {pp.get('weight_unit', 'kg')}")
                if pp.get("gender"):
                    pet_info_parts.append(f"Gender: {pp['gender']}")
                if pp.get("blood_type"):
                    pet_info_parts.append(f"Blood Type: {pp['blood_type']}")
                if pp.get("allergies"):
                    pet_info_parts.append(f"Allergies: {pp['allergies']}")
                if pp.get("medical_conditions"):
                    pet_info_parts.append(f"Medical Conditions: {pp['medical_conditions']}")
                if pp.get("notes"):
                    pet_info_parts.append(f"Additional Notes: {pp['notes']}")
                
                # Create pet context and save to memory so it persists throughout conversation
                from datetime import datetime
                current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
                pet_context = f"CURRENT DATE AND TIME: {current_time}\n\nPET PROFILE:\n{chr(10).join(pet_info_parts)}"
                session.memory.save_context(
                    {"input": "System: Pet profile initialized"},
                    {"output": pet_context}
                )
                chat_history = pet_context + "\n\n" + chat_history if chat_history else pet_context
                session.pet_initialized = True
            
            pet_query = f"""Pet Type: {animal}

Previous Conversation:
{chat_history}

Current User Question: {user_input}

If this is a veterinary/medical question, search the knowledge base for accurate information.
If this is casual conversation or personal information, answer directly without searching.
Be smart about deciding whether retrieval is necessary."""
            
            bot_response = query_agentic_rag(
                question=user_input,
                chat_history=chat_history
            )
            used_rag = True
        
        # Save to memory
        session.memory.save_context(
            {"input": user_input},
            {"output": bot_response}
        )
        
        logger.info(f"Session {session.session_id}: Message processed")
        
        return SendMessageResponse(
            session_id=session.session_id,
            bot_response=bot_response,
            used_rag=used_rag,
            disease_detected=disease_type
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/upload-image")
async def upload_image(
    session_id: str = Form(...),
    disease_type: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Upload and analyze a pet image.
    
    This endpoint:
    1. Saves uploaded image temporarily
    2. Calls CV model via FastAPI
    3. Uses agentic RAG to explain diagnosis
    
    Args:
        session_id: Conversation session ID
        disease_type: 'skin' or 'eye'
        file: Image file upload
    
    Returns:
        Disease prediction and explanation
    """
    try:
        session = get_session(session_id)
        animal = session.animal
        
        if disease_type not in ["skin", "eye"]:
            raise HTTPException(status_code=400, detail="disease_type must be 'skin' or 'eye'")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Analyze image using CV model (exact same as CLI)
            tool_result = _analyze_pet_image_impl(
                image_path=tmp_path,
                animal=animal,
                disease_type=disease_type
            )
            
            if isinstance(tool_result, dict) and "error" in tool_result:
                raise HTTPException(status_code=400, detail=tool_result['error'])
            
            disease_class = tool_result.get('class', 'Unknown')
            confidence = tool_result.get('confidence', 'N/A')
            
            # Use agentic RAG to explain diagnosis (exact same as CLI)
            explanation_query = f"""The computer vision model detected {disease_class} (confidence: {confidence:.1%}) from a {animal}'s {disease_type} image.

Provide a detailed veterinary explanation covering:
1. What is {disease_class}?
2. Common causes and risk factors for this condition
3. Treatment options and recommendations
4. When to seek professional veterinary care
5. Prevention and management tips

Be thorough and informative. Use formatting with headers and bullet points for clarity."""
            
            chat_history = session.get_chat_history()
            explanation_text = query_agentic_rag(
                question=explanation_query,
                chat_history=chat_history
            )
            
            # Update session
            session.analysis_done = True
            session.current_disease_type = disease_type
            
            # Save diagnosis to memory
            diagnosis_record = f"Diagnosed with {disease_class} (confidence: {confidence:.1%}) from {disease_type} image analysis"
            session.memory.save_context(
                {"input": f"Image analysis for {disease_type}"},
                {"output": diagnosis_record}
            )
            
            logger.info(f"Session {session.session_id}: Image analyzed - {disease_class}")
            
            return {
                "session_id": session.session_id,
                "disease_class": disease_class,
                "confidence": confidence,
                "explanation": explanation_text
            }
        
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """
    Get conversation history for a session.
    
    Args:
        session_id: Conversation session ID
    
    Returns:
        Formatted chat history
    """
    try:
        session = get_session(session_id)
        chat_history = session.get_chat_history()
        
        return {
            "session_id": session_id,
            "animal": session.animal,
            "chat_history": chat_history
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/api/chat/message/stream")
async def send_message_stream(request: SendMessageRequest):
    """
    Send a message and stream the response using Server-Sent Events.
    
    This is the same logic as /api/chat/message but with streaming.
    Returns response token-by-token for real-time display.
    
    Args:
        request: Contains session_id and message text
    
    Yields:
        SSE formatted strings with streaming response chunks
    """
    from fastapi.responses import StreamingResponse
    
    async def response_generator():
        try:
            # Get session
            session = get_session(request.session_id)
            user_input = request.message.strip()
            
            if not user_input:
                yield f"data: {json.dumps({'error': 'Message cannot be empty'})}\n\n"
                return
            
            animal = session.animal
            
            # Detect disease type from message (same as CLI)
            detected_disease_type = detect_disease_type(user_input)
            
            if detected_disease_type:
                if detected_disease_type != session.current_disease_type:
                    session.analysis_done = False
                session.current_disease_type = detected_disease_type
                disease_type = session.current_disease_type
            else:
                # No disease keywords in current message - reset disease type
                disease_type = None
                session.current_disease_type = None
            used_rag = False
            
            # Handle disease-specific flow
            if disease_type:
                image_path = extract_image_path(user_input)
                
                if image_path and os.path.isfile(image_path):
                    # Analyze image
                    bot_response = await handle_image_analysis(
                        session, image_path, animal, disease_type, user_input
                    )
                    session.analysis_done = True
                    # Stream the full response
                    yield f"data: {json.dumps({'chunk': bot_response, 'used_rag': False, 'disease_detected': disease_type, 'done': True})}\n\n"
                else:
                    if session.analysis_done:
                        # Follow-up question
                        follow_up_prompt = f"The user is asking a follow-up question about the {disease_type} condition we discussed earlier: '{user_input}'"
                        
                        # Stream RAG response with history
                        chat_history = session.memory.load_memory_variables({}).get('chat_history', '')
                        
                        # Get the response with a streaming approach
                        response_text = ""
                        async for chunk in stream_llm_response(follow_up_prompt, chat_history):
                            response_text += chunk
                            yield f"data: {json.dumps({'chunk': chunk, 'used_rag': True, 'disease_detected': None, 'done': False})}\n\n"
                            await asyncio.sleep(0.01)  # Small delay for streaming effect
                        
                        used_rag = True
                        session.memory.save_context({"input": user_input}, {"output": response_text})
                        yield f"data: {json.dumps({'chunk': '', 'used_rag': True, 'disease_detected': None, 'done': True})}\n\n"
                    else:
                        # First mention of disease - ask for image
                        enriched_input = f"The user mentioned their {animal} has {disease_type} symptoms: '{user_input}'. Ask them if they can provide an image for analysis."
                        
                        response_text = ""
                        async for chunk in stream_llm_response(enriched_input, ""):
                            response_text += chunk
                            yield f"data: {json.dumps({'chunk': chunk, 'used_rag': False, 'disease_detected': disease_type, 'done': False})}\n\n"
                            await asyncio.sleep(0.01)
                        
                        session.memory.save_context({"input": user_input}, {"output": response_text})
                        yield f"data: {json.dumps({'chunk': '', 'used_rag': False, 'disease_detected': disease_type, 'done': True})}\n\n"
            else:
                # General health question - use agentic RAG
                chat_history = session.memory.load_memory_variables({}).get('chat_history', '')
                
                # Inject pet profile context on the very first message only
                # IMPORTANT: Add to chat_history, NOT to the question string,
                # because the question is checked by is_skin_or_eye_issue()
                # and pet profile fields (like "Allergies") could trigger false matches.
                if session.pet_profile and not session.pet_initialized:
                    pp = session.pet_profile
                    pet_info_parts = []
                    if pp.get("name"):
                        pet_info_parts.append(f"Name: {pp['name']}")
                    pet_info_parts.append(f"Type: {animal}")
                    if pp.get("breed"):
                        pet_info_parts.append(f"Breed: {pp['breed']}")
                    if pp.get("date_of_birth"):
                        pet_info_parts.append(f"Date of Birth: {pp['date_of_birth']}")
                    if pp.get("weight"):
                        pet_info_parts.append(f"Weight: {pp['weight']} {pp.get('weight_unit', 'kg')}")
                    if pp.get("gender"):
                        pet_info_parts.append(f"Gender: {pp['gender']}")
                    if pp.get("blood_type"):
                        pet_info_parts.append(f"Blood Type: {pp['blood_type']}")
                    if pp.get("allergies"):
                        pet_info_parts.append(f"Allergies: {pp['allergies']}")
                    if pp.get("medical_conditions"):
                        pet_info_parts.append(f"Medical Conditions: {pp['medical_conditions']}")
                    if pp.get("notes"):
                        pet_info_parts.append(f"Additional Notes: {pp['notes']}")
                    
                    # Save pet profile to memory so it persists throughout conversation
                    from datetime import datetime
                    current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
                    pet_context = f"CURRENT DATE AND TIME: {current_time}\n\nPET PROFILE:\n{chr(10).join(pet_info_parts)}"
                    session.memory.save_context(
                        {"input": "System: Pet profile initialized"},
                        {"output": pet_context}
                    )
                    chat_history = pet_context + "\n\n" + chat_history if chat_history else pet_context
                    session.pet_initialized = True
                
                response_text = ""
                async for chunk in stream_llm_response(user_input, chat_history):
                    response_text += chunk
                    yield f"data: {json.dumps({'chunk': chunk, 'used_rag': True, 'disease_detected': None, 'done': False})}\n\n"
                    await asyncio.sleep(0.01)
                
                used_rag = True
                session.memory.save_context({"input": user_input}, {"output": response_text})
                yield f"data: {json.dumps({'chunk': '', 'used_rag': True, 'disease_detected': None, 'done': True})}\n\n"
        
        except Exception as e:
            logger.exception(f"Error in streaming message: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        response_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@app.delete("/api/chat/session/{session_id}")
async def delete_session(session_id: str):
    """
    End a conversation session.
    
    Args:
        session_id: Conversation session ID
    
    Returns:
        Confirmation
    """
    try:
        if session_id in _sessions:
            del _sessions[session_id]
            logger.info(f"Session {session_id} deleted")
        
        return {
            "session_id": session_id,
            "message": "Session ended"
        }
    
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────

async def handle_image_analysis(
    session: ConversationSession,
    image_path: str,
    animal: str,
    disease_type: str,
    user_input: str
) -> str:
    """
    Handle image analysis using exact same logic as CLI.
    """
    try:
        tool_result = _analyze_pet_image_impl(
            image_path=image_path,
            animal=animal,
            disease_type=disease_type
        )
        
        if isinstance(tool_result, dict) and "error" in tool_result:
            return f"Error analyzing image: {tool_result['error']}"
        
        disease_class = tool_result.get('class', 'Unknown')
        confidence = tool_result.get('confidence', 'N/A')
        
        # Use agentic RAG for explanation
        explanation_query = f"""The computer vision model detected {disease_class} (confidence: {confidence:.1%}) from a {animal}'s {disease_type} image.

User's original description: {user_input}

Provide a detailed veterinary explanation covering:
1. What is {disease_class}?
2. Common causes and risk factors for this condition
3. Treatment options and recommendations
4. When to seek professional veterinary care
5. Prevention and management tips

Be thorough and informative. Use formatting with headers and bullet points for clarity."""
        
        chat_history = session.get_chat_history()
        explanation_text = query_agentic_rag(
            question=explanation_query,
            chat_history=chat_history
        )
        
        session.analysis_done = True
        session.current_disease_type = disease_type
        
        # Save diagnosis
        diagnosis_record = f"Diagnosed with {disease_class} (confidence: {confidence:.1%}) from {disease_type} image analysis"
        session.memory.save_context(
            {"input": user_input},
            {"output": diagnosis_record}
        )
        
        return explanation_text
    
    except Exception as e:
        logger.error(f"Error in image analysis: {e}")
        return f"Error analyzing image: {str(e)}"


async def stream_llm_response(
    question: str,
    chat_history: str = ""
) -> AsyncGenerator[str, None]:
    """
    Stream LLM response while preserving markdown structure.
    
    Streams complete markdown elements (paragraphs, lists, code blocks)
    to ensure proper rendering and avoid breaking markdown syntax.
    
    Args:
        question: User question
        chat_history: Previous conversation history
    
    Yields:
        Response chunks (preserving markdown structure)
    """
    try:
        # Get full response using existing agentic RAG
        full_response = query_agentic_rag(question=question, chat_history=chat_history)
        
        # Split by double newlines to preserve paragraph structure
        # This naturally preserves all markdown formatting (lists, headings, etc.)
        paragraphs = full_response.split('\n\n')
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Yield the entire paragraph at once to preserve markdown structure
            # This ensures lists, headings, and formatting stay intact
            yield para
            await asyncio.sleep(0.02)
            
            # Yield paragraph separator to maintain structure
            yield '\n\n'
            await asyncio.sleep(0.01)
    
    except Exception as e:
        logger.error(f"Error streaming LLM response: {e}")
        yield f"Error: {str(e)}"


# ─────────────────────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Pet AI Healthcare Chatbot API",
        "active_sessions": len(_sessions)
    }


# ─────────────────────────────────────────────────────────────
# Startup
# ─────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    setup_langsmith()
    logger.info("Pet AI Healthcare Chatbot API started")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
