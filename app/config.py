import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DOG_SKIN_MODEL = os.path.join(BASE_DIR, "weights/dog_skin_model.pth")
DOG_EYE_MODEL = os.path.join(BASE_DIR, "weights/dog_eye_model_ResNet_NEW.pth")
CAT_SKIN_MODEL = os.path.join(BASE_DIR, "weights/cat_skin_model.pth")

DEVICE = "cuda" if __import__("torch").cuda.is_available() else "cpu"

# LangSmith Configuration (for tracing and debugging)
# These can be set in .env file or will prompt at runtime
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", None)
LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "Pet_AI")