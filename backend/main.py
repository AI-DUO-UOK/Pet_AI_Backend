from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import tempfile
import os

# Import models & services with updated backend package prefix
from backend.models import dog_skin, dog_eye, cat_skin
from backend.utils.image import preprocess
from backend.services.router import route_prediction

# Import refactored routers
from backend.routers.auth import router as auth_router
from backend.routers.pets import router as pets_router
from backend.routers.appointments import router as appointments_router
from backend.routers.clinics import router as clinics_router
from backend.routers.admin import router as admin_router

from chatbot.langsmith_config import setup_langsmith
from chatbot.tools import _analyze_pet_image_impl
from chatbot.rag.agentic_rag import query_agentic_rag

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Pet PULSE Disease Detection API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include refactored routers under the /api prefix
app.include_router(auth_router, prefix="/api")
app.include_router(pets_router, prefix="/api")
app.include_router(appointments_router, prefix="/api")
app.include_router(clinics_router, prefix="/api")
app.include_router(admin_router, prefix="/api")

# 🏠 Root endpoint
@app.get("/")
async def root(request: Request):
    """Root endpoint with API information"""
    base_url = str(request.base_url).rstrip('/')
    env = os.getenv("ENVIRONMENT", "production" if os.getenv("RAILWAY_STATIC_URL") or os.getenv("RAILWAY_ENVIRONMENT") else "development")
    return {
        "name": "Pet PULSE Disease Detection API",
        "version": "1.0.0",
        "status": "running",
        "environment": env,
        "docs": f"{base_url}/docs",
        "openapi": f"{base_url}/openapi.json",
        "health": f"{base_url}/health",
        "endpoints": {
            "prediction": "/predict",
            "image_analysis": "/analyze-image",
            "pets": "/api/pets",
            "clinics": "/api/clinics"
        }
    }

# 🏥 Health check endpoint
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Pet PULSE API",
        "models_loaded": {
            "dog_skin": hasattr(app.state, 'dog_skin') and app.state.dog_skin is not None,
            "dog_eye": hasattr(app.state, 'dog_eye') and app.state.dog_eye is not None,
            "cat_skin": hasattr(app.state, 'cat_skin') and app.state.cat_skin is not None
        }
    }

# 🔥 Load models ONCE on startup
@app.on_event("startup")
def load_models():
    try:
        # Initialize LangSmith tracing (optional)
        setup_langsmith()
        logger.info("LangSmith tracing initialized")
    except Exception as e:
        logger.warning(f"LangSmith initialization failed (optional): {e}")
    
    try:
        app.state.dog_skin = dog_skin.load_model()
        logger.info("Dog skin model loaded")
    except Exception as e:
        logger.warning(f"Dog skin model loading failed: {e}")
        app.state.dog_skin = None
    
    try:
        app.state.dog_eye = dog_eye.load_model()
        logger.info("Dog eye model loaded")
    except Exception as e:
        logger.warning(f"Dog eye model loading failed: {e}")
        app.state.dog_eye = None
    
    try:
        app.state.cat_skin = cat_skin.load_model()
        logger.info("Cat skin model loaded")
    except Exception as e:
        logger.warning(f"Cat skin model loading failed: {e}")
        app.state.cat_skin = None
    
    logger.info("✅ Backend startup complete")

# 📸 Prediction endpoint
@app.post("/predict")
async def predict(
    file: UploadFile = File(...),
    animal: str = Form(...),
    disease_type: str = Form(...)
):
    image = preprocess(file.file)
    result = route_prediction(app, animal, disease_type, image)
    return result

# 🔍 Analyze image endpoint (for chatbot integration)
@app.post("/analyze-image")
async def analyze_image(
    file: UploadFile = File(...),
    disease_type: str = Form(...),
    animal: str = Form("dog"),
    user_id: str = Form("demo")
):
    """
    Analyze pet image for disease detection.
    Used by chatbot for skin/eye disease diagnosis.
    """
    image = preprocess(file.file)
    result = route_prediction(app, animal, disease_type, image)
    return result

# 📸 Chatbot image upload endpoint
@app.post("/api/chat/upload-image")
async def upload_image(
    session_id: str = Form(...),
    disease_type: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Upload and analyze a pet image for chatbot.
    """
    try:
        animal = "dog"  # Default - in production, retrieve from session
        
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
            
            explanation_query = f"""The computer vision model detected {disease_class} (confidence: {confidence:.1%}) from a {animal}'s {disease_type} image.

Provide a detailed veterinary explanation covering:
1. What is {disease_class}?
2. Common causes and risk factors for this condition
3. Treatment options and recommendations
4. When to seek professional veterinary care
5. Prevention and management tips

Be thorough and informative. Use formatting with headers and bullet points for clarity."""
            
            explanation_text = query_agentic_rag(
                question=explanation_query,
                chat_history="",
                force_rag=True
            )
            
            logger.info(f"Image analyzed for {disease_type}: {disease_class}")
            
            return {
                "session_id": session_id,
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