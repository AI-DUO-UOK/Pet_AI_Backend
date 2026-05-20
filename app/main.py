from fastapi import FastAPI, UploadFile, File, Form
from app.models import dog_skin, dog_eye, cat_skin
from app.utils.image import preprocess
from app.services.router import route_prediction
from chatbot.langsmith_config import setup_langsmith

app = FastAPI(title="Pet AI Disease Detection API")

# 🔥 Load models ONCE
@app.on_event("startup")
def load_models():
    # Initialize LangSmith tracing (optional)
    setup_langsmith()
    
    app.state.dog_skin = dog_skin.load_model()
    app.state.dog_eye = dog_eye.load_model()
    app.state.cat_skin = cat_skin.load_model()

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