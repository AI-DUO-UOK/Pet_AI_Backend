from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import tempfile
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import models & services with updated backend package prefix
from backend.models import dog_skin, dog_eye, cat_skin
from backend.utils.image import preprocess
from backend.services.router import route_prediction

# Import refactored routers (optional for lightweight deployments like Hugging Face)
try:
    from backend.routers.auth import router as auth_router
    from backend.routers.pets import router as pets_router
    from backend.routers.appointments import router as appointments_router
    from backend.routers.clinics import router as clinics_router
    from backend.routers.admin import router as admin_router
    from backend.routers.config import router as config_router  # GET /api/config/google-maps
    from backend.routers.payments import router as payments_router  # Payment & Stripe integration
    from backend.routers.chat import router as chat_router  # Unified chatbot router
    has_backend_routers = True
except ImportError as e:
    logger.warning(f"Backend routers not loaded (this is normal on Hugging Face Spaces): {e}")
    has_backend_routers = False

# Import chatbot integrations (optional for lightweight deployments like Hugging Face)
try:
    from chatbot.langsmith_config import setup_langsmith
    from chatbot.tools import _analyze_pet_image_impl
    from chatbot.rag.agentic_rag import query_agentic_rag
    has_chatbot = True
except ImportError as e:
    logger.warning(f"Chatbot integrations not loaded (this is normal on Hugging Face Spaces): {e}")
    has_chatbot = False

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
if has_backend_routers:
    app.include_router(auth_router, prefix="/api")
    app.include_router(pets_router, prefix="/api")
    app.include_router(appointments_router, prefix="/api")
    app.include_router(clinics_router, prefix="/api")
    app.include_router(admin_router, prefix="/api")
    app.include_router(config_router)  # prefix already set in router: /api/config
    app.include_router(payments_router, prefix="/api")  # POST /api/payments/create-checkout-session, etc.
    app.include_router(chat_router, prefix="/api")  # Unified chatbot router

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
    if has_chatbot:
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