from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, AsyncGenerator, Any
import uuid
import os
import tempfile
import logging
import json
import asyncio

from chatbot.main import detect_disease_type, extract_image_path, clean_agent_response
from chatbot.tools import _analyze_pet_image_impl, _analyze_medical_document_vlm_impl
from chatbot.rag.agentic_rag import query_agentic_rag
from chatbot.memory import SimpleConversationMemory
from chatbot.agent import agent
from chatbot.llm import llm

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chatbot"])

# ─────────────────────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────────────────────

class StartConversationRequest(BaseModel):
    """Request to start a new conversation"""
    animal: str  # 'dog' or 'cat'
    user_id: Optional[str] = None  # Optional user identifier
    pet_id: Optional[str] = None  # Optional pet identifier for real user data
    pet_profile: Optional[Dict[str, Any]] = None

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
    
    def __init__(self, session_id: str, animal: str, pet_profile: Optional[Dict[str, Any]] = None):
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

    def get_pet_context(self) -> str:
        """Get selected pet profile context for LLM prompts."""
        return format_pet_profile_context(self.animal, self.pet_profile)

# Store active sessions
_sessions: Dict[str, ConversationSession] = {}

def get_session(session_id: str) -> ConversationSession:
    """Get conversation session by ID"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return _sessions[session_id]


def format_pet_profile_context(animal: str, pet_profile: Dict[str, Any]) -> str:
    """Build a compact pet profile context block for prompts."""
    if not pet_profile:
        return f"Selected Pet Profile:\n- Type: {animal}"

    field_labels = {
        "name": "Name",
        "type": "Type",
        "breed": "Breed",
        "age": "Age",
        "date_of_birth": "Date of birth",
        "gender": "Gender",
        "blood_type": "Blood type",
        "allergies": "Allergies",
        "medical_conditions": "Medical conditions",
        "notes": "Notes",
        "microchip_id": "Microchip ID",
    }
    lines = ["Selected Pet Profile:"]
    for key, label in field_labels.items():
        value = pet_profile.get(key)
        if value is not None and str(value).strip():
            lines.append(f"- {label}: {value}")

    weight = pet_profile.get("weight")
    if weight is not None and str(weight).strip():
        weight_unit = pet_profile.get("weight_unit") or ""
        lines.append(f"- Weight: {weight} {weight_unit}".strip())

    if not any(line.startswith("- Type:") for line in lines):
        lines.append(f"- Type: {animal}")

    vaccinations = pet_profile.get("vaccinations")
    if vaccinations:
        lines.append("\nVaccination History & Timeline:")
        for vac in vaccinations:
            vac_name = vac.get("vaccine_name")
            vac_date = vac.get("vaccination_date")
            next_due = vac.get("next_due_date")
            clinic = vac.get("clinic_name")
            vet = vac.get("veterinarian_name")
            batch = vac.get("batch_number")
            notes = vac.get("notes")
            vac_type = vac.get("vaccine_type")
            
            vac_details = []
            if vac_name:
                name_str = f"  - Vaccine: {vac_name}"
                if vac_type:
                    name_str += f" ({vac_type})"
                vac_details.append(name_str)
            if vac_date:
                vac_details.append(f"    Date Administered: {vac_date}")
            if next_due:
                vac_details.append(f"    Next Due Date: {next_due}")
            if vet:
                vac_details.append(f"    Veterinarian: {vet}")
            if clinic:
                vac_details.append(f"    Clinic: {clinic}")
            if batch:
                vac_details.append(f"    Batch/Lot Number: {batch}")
            if notes:
                vac_details.append(f"    Notes: {notes}")
            
            if vac_details:
                lines.append("\n".join(vac_details))

    return "\n".join(lines)

async def fetch_pet_profile(pet_id: str) -> Optional[dict]:
    """Fetch pet profile from the database by pet_id."""
    try:
        from backend.core.supabase_config import supabase
        response = supabase.table("pets").select("*").eq("id", pet_id).execute()
        if response.data:
            return response.data[0]
    except Exception as e:
        logger.warning(f"Could not fetch pet profile for {pet_id}: {e}")
    return None


async def fetch_pet_vaccines(pet_id: str) -> list:
    """Fetch pet vaccination records from the database by pet_id."""
    try:
        from backend.core.supabase_config import supabase
        response = supabase.table("vaccination_records")\
            .select("*")\
            .eq("pet_id", pet_id)\
            .order("vaccination_date", desc=True)\
            .execute()
        if response.data:
            return response.data
    except Exception as e:
        logger.warning(f"Could not fetch vaccination records for {pet_id}: {e}")
    return []

# ─────────────────────────────────────────────────────────────
# Helper Functions for Image Analysis & Streaming
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
        confidence = tool_result.get('confidence', 0.0)
        
        # Use agentic RAG for explanation
        pet_context = session.get_pet_context()
        explanation_query = f"""{pet_context}
 
The computer vision model detected {disease_class} (confidence: {confidence:.1%}) from a {animal}'s {disease_type} image.

User's original description: {user_input}

Respond conversationally as a friendly vet assistant by provide a detailed veterinary explanation. Start by saying something like "Your {animal} appears to have {disease_class}." Then explain:
1. What is {disease_class}?
2. Common causes and risk factors for this condition
3. Treatment options and recommendations
4. When to seek professional veterinary care
5. Prevention and management tips

Be warm, conversational, and informative. Use formatting with headers and bullet points for clarity.
IMPORTANT: Do NOT mention the knowledge base, retrieved contexts, or the analysis model in your response. Just give the advice naturally."""
        
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
    """
    try:
        # Get full response using existing agentic RAG
        full_response = query_agentic_rag(question=question, chat_history=chat_history)
        
        # Split by double newlines to preserve paragraph structure
        paragraphs = full_response.split('\n\n')
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            yield para
            await asyncio.sleep(0.02)
            
            yield '\n\n'
            await asyncio.sleep(0.01)
    
    except Exception as e:
        logger.error(f"Error streaming LLM response: {e}")
        yield f"Error: {str(e)}"

# ─────────────────────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────────────────────

@router.post("/chat/start", response_model=StartConversationResponse)
async def start_conversation(request: StartConversationRequest):
    """
    Start a new conversation session with pet type selection.
    """
    try:
        if request.animal.lower() not in ["dog", "cat"]:
            raise HTTPException(status_code=400, detail="Animal must be 'dog' or 'cat'")
        
        session_id = str(uuid.uuid4())
        animal = request.animal.lower()
        
        pet_profile = None
        if request.pet_id:
            pet_profile = await fetch_pet_profile(request.pet_id)
            if pet_profile:
                logger.info(f"Fetched pet profile: {pet_profile.get('name')} for session {session_id}")
            else:
                logger.warning(f"Pet profile not found for pet_id: {request.pet_id}")
        elif request.pet_profile:
            pet_profile = dict(request.pet_profile)
        
        if pet_profile:
            pet_id = pet_profile.get("id") or request.pet_id
            if pet_id:
                vaccines = await fetch_pet_vaccines(pet_id)
                pet_profile["vaccinations"] = vaccines
        
        session = ConversationSession(session_id, animal, pet_profile)
        _sessions[session_id] = session
        
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


@router.post("/chat/message", response_model=SendMessageResponse)
async def send_message(request: SendMessageRequest):
    """
    Send a message in an existing conversation.
    """
    try:
        session = get_session(request.session_id)
        user_input = request.message.strip()
        
        if not user_input:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        animal = session.animal
        detected_disease_type = detect_disease_type(user_input)
        
        if detected_disease_type:
            if detected_disease_type != session.current_disease_type:
                session.analysis_done = False
            session.current_disease_type = detected_disease_type
            disease_type = session.current_disease_type
        else:
            disease_type = None
            session.current_disease_type = None
            
        bot_response = ""
        used_rag = False
        
        if disease_type:
            image_path = extract_image_path(user_input)
            
            if image_path and os.path.isfile(image_path):
                bot_response = await handle_image_analysis(
                    session, image_path, animal, disease_type, user_input
                )
            else:
                if session.analysis_done:
                    chat_history = session.get_chat_history()
                    followup_query = f"""User's follow-up question about the previously diagnosed {disease_type} condition for their {animal}: {user_input}

IMPORTANT: Reference the specific diagnosis and previous discussion from the conversation history.
Answer this question in the context of the condition previously diagnosed. 
Provide helpful, accurate veterinary advice based on the question asked."""
                    
                    bot_response = query_agentic_rag(
                        question=followup_query,
                        chat_history=chat_history
                    )
                    used_rag = True
                else:
                    pet_context = session.get_pet_context()
                    enriched_input = f"""
{pet_context}

Pet Type: {animal}
Issue Type: {disease_type} disease

User Query: {user_input}

The user is asking about a {disease_type} issue. Ask them to upload a clear image
so you can provide a proper diagnosis. Guide them to provide the image file path.
Do NOT use the tool yet. Just ask for the image."""
                    
                    response = agent.run(enriched_input)
                    bot_response = clean_agent_response(response)
        else:
            chat_history = session.get_chat_history()
            
            if session.pet_profile and not session.pet_initialized:
                from datetime import datetime
                current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
                pet_context = f"CURRENT DATE AND TIME: {current_time}\n\n{session.get_pet_context()}"
                session.memory.save_context(
                    {"input": "System: Pet profile initialized"},
                    {"output": pet_context}
                )
                chat_history = pet_context + "\n\n" + chat_history if chat_history else pet_context
                session.pet_initialized = True
            
            pet_context = session.get_pet_context()
            pet_query = f"""{pet_context}

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


@router.post("/chat/upload-image")
async def upload_image(
    session_id: str = Form(...),
    disease_type: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Upload and analyze a pet image.
    """
    try:
        session = get_session(session_id)
        animal = session.animal
        
        if disease_type not in ["skin", "eye"]:
            raise HTTPException(status_code=400, detail="disease_type must be 'skin' or 'eye'")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            tool_result = _analyze_pet_image_impl(
                image_path=tmp_path,
                animal=animal,
                disease_type=disease_type
            )
            
            if isinstance(tool_result, dict) and "error" in tool_result:
                raise HTTPException(status_code=400, detail=tool_result['error'])
            
            disease_class = tool_result.get('class', 'Unknown')
            confidence = tool_result.get('confidence', 0.0)
            
            pet_context = session.get_pet_context()
            explanation_query = f"""{pet_context}

The computer vision model detected {disease_class} (confidence: {confidence:.1%}) from a {animal}'s {disease_type} image.

Respond conversationally as a friendly vet assistant. Start by saying something like "Your {animal} appears to have {disease_class}." Then explain:
1. What is {disease_class}?
2. Common causes and risk factors for this condition
3. Treatment options and recommendations
4. When to seek professional veterinary care
5. Prevention and management tips

Be warm, conversational, and informative. Use formatting with headers and bullet points for clarity.
IMPORTANT: Do NOT mention the knowledge base, retrieved contexts, or the analysis model in your response. Just give the advice naturally."""
            
            chat_history = session.get_chat_history()
            explanation_text = query_agentic_rag(
                question=explanation_query,
                chat_history=chat_history
            )
            
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
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/upload-document")
async def upload_document(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    prompt: Optional[str] = Form(None)
):
    """
    Upload and analyze a medical document.
    """
    try:
        session = get_session(session_id)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename or ".jpg")[1]) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            extracted_data = _analyze_medical_document_vlm_impl(tmp_path)
            
            if isinstance(extracted_data, dict) and "error" in extracted_data:
                raise HTTPException(status_code=400, detail=extracted_data['error'])
            
            extracted_json_str = json.dumps(extracted_data, indent=2)
            user_prompt_str = f"\n\nUSER'S QUESTION/PROMPT ABOUT THE DOCUMENT:\n{prompt}" if prompt else ""
            
            explanation_query = f"""The following data was extracted from a medical document (prescription, vaccine card, or medical report) using AI analysis:
            
EXTRACTED DATA:
{extracted_json_str}
{user_prompt_str}

Respond conversationally as a friendly vet assistant. Explain what this document says in simple terms, focusing specifically on answering the user's question/prompt if one was provided.
If it's a prescription, explain the medication, dosage, and instructions clearly.
If it's a vaccine card, explain what vaccines were given and when the next ones are due.
If it's a medical report, summarize the findings and recommendations.
Be clear, helpful, and reassuring. Use formatting with headers and bullet points for clarity.
IMPORTANT: Do NOT mention the AI analysis or extraction process in your response. Just explain the document naturally."""
            
            chat_history = session.get_chat_history()
            explanation_text = query_agentic_rag(
                question=explanation_query,
                chat_history=chat_history
            )
            
            session.memory.save_context(
                {"input": f"Uploaded medical document: {file.filename}"},
                {"output": f"Document analyzed. Extracted data: {extracted_json_str}\n\nExplanation: {explanation_text}"}
            )
            
            logger.info(f"Session {session.session_id}: Medical document analyzed")
            
            return {
                "session_id": session.session_id,
                "extracted_data": extracted_data,
                "explanation": explanation_text
            }
        
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """
    Get conversation history for a session.
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


@router.post("/chat/message/stream")
async def send_message_stream(request: SendMessageRequest):
    """
    Send a message and stream the response using Server-Sent Events.
    """
    async def response_generator():
        try:
            session = get_session(request.session_id)
            user_input = request.message.strip()
            
            if not user_input:
                yield f"data: {json.dumps({'error': 'Message cannot be empty'})}\n\n"
                return
            
            animal = session.animal
            detected_disease_type = detect_disease_type(user_input)
            
            if detected_disease_type:
                if detected_disease_type != session.current_disease_type:
                    session.analysis_done = False
                session.current_disease_type = detected_disease_type
                disease_type = session.current_disease_type
            else:
                disease_type = None
                session.current_disease_type = None
            used_rag = False
            
            if disease_type:
                image_path = extract_image_path(user_input)
                
                if image_path and os.path.isfile(image_path):
                    bot_response = await handle_image_analysis(
                        session, image_path, animal, disease_type, user_input
                    )
                    session.analysis_done = True
                    yield f"data: {json.dumps({'chunk': bot_response, 'used_rag': False, 'disease_detected': disease_type, 'done': True})}\n\n"
                else:
                    if session.analysis_done:
                        follow_up_prompt = f"""User's follow-up question about the previously diagnosed {disease_type} condition for their {animal}: {user_input}

IMPORTANT: Reference the specific diagnosis and previous discussion from the conversation history.
Answer this question in the context of the condition previously diagnosed. 
Provide helpful, accurate veterinary advice based on the question asked."""
                        
                        chat_history = session.memory.load_memory_variables({}).get('chat_history', '')
                        
                        response_text = ""
                        async for chunk in stream_llm_response(follow_up_prompt, chat_history):
                            response_text += chunk
                            yield f"data: {json.dumps({'chunk': chunk, 'used_rag': True, 'disease_detected': None, 'done': False})}\n\n"
                            await asyncio.sleep(0.01)
                        
                        used_rag = True
                        session.memory.save_context({"input": user_input}, {"output": response_text})
                        yield f"data: {json.dumps({'chunk': '', 'used_rag': True, 'disease_detected': None, 'done': True})}\n\n"
                    else:
                        pet_context = session.get_pet_context()
                        enriched_input = f"""{pet_context}

The user mentioned their {animal} has {disease_type} symptoms: '{user_input}'. Ask them if they can provide an image for analysis."""
                        
                        response_text = ""
                        async for chunk in stream_llm_response(enriched_input, ""):
                            response_text += chunk
                            yield f"data: {json.dumps({'chunk': chunk, 'used_rag': False, 'disease_detected': disease_type, 'done': False})}\n\n"
                            await asyncio.sleep(0.01)
                        
                        session.memory.save_context({"input": user_input}, {"output": response_text})
                        yield f"data: {json.dumps({'chunk': '', 'used_rag': False, 'disease_detected': disease_type, 'done': True})}\n\n"
            else:
                chat_history = session.memory.load_memory_variables({}).get('chat_history', '')
                
                if session.pet_profile and not session.pet_initialized:
                    from datetime import datetime
                    current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
                    pet_context = f"CURRENT DATE AND TIME: {current_time}\n\n{session.get_pet_context()}"
                    session.memory.save_context(
                        {"input": "System: Pet profile initialized"},
                        {"output": pet_context}
                    )
                    chat_history = pet_context + "\n\n" + chat_history if chat_history else pet_context
                    session.pet_initialized = True
                
                if session.pet_profile:
                    contextual_input = user_input
                else:
                    contextual_input = f"Selected Pet Profile:\n- Type: {animal}\n\nCurrent User Question: {user_input}"

                response_text = ""
                async for chunk in stream_llm_response(contextual_input, chat_history):
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


@router.delete("/chat/session/{session_id}")
async def delete_session(session_id: str):
    """
    End a conversation session.
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
