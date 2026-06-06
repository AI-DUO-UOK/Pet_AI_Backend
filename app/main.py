from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.models import dog_skin, dog_eye, cat_skin
from app.utils.image import preprocess
from app.services.router import route_prediction
from app.api_routes import router as api_router
from chatbot.langsmith_config import setup_langsmith

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Pet AI Disease Detection API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Supabase API routes
app.include_router(api_router)

# 🏠 Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Pet AI Disease Detection API",
        "version": "1.0.0",
        "docs": "http://localhost:8000/docs",
        "status": "running",
        "endpoints": {
            "prediction": "/predict",
            "image_analysis": "/analyze-image",
            "supabase_auth": "/api/auth/login",
            "pets": "/api/pets"
        }
    }

# 🏥 Health check endpoint
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Pet AI API",
        "models_loaded": {
            "dog_skin": hasattr(app.state, 'dog_skin') and app.state.dog_skin is not None,
            "dog_eye": hasattr(app.state, 'dog_eye') and app.state.dog_eye is not None,
            "cat_skin": hasattr(app.state, 'cat_skin') and app.state.cat_skin is not None
        }
    }

# 🔥 Load models ONCE
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