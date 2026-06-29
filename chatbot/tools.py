import os
import requests
import json
import logging
from langchain.tools import tool
from chatbot.vlm import analyze_medical_document_vlm

logger = logging.getLogger(__name__)

FASTAPI_URL = os.getenv("DISEASE_DETECTION_API_URL") or os.getenv("FASTAPI_URL") or "http://127.0.0.1:8000/analyze-image"

def _analyze_pet_image_impl(image_path: str, animal: str, disease_type: str) -> dict:
    """
    Internal implementation of pet image analysis.
    This function contains the actual logic and can be called directly.
    
    Args:
        image_path: Path to the pet image file
        animal: Type of animal ('dog' or 'cat')
        disease_type: Type of disease to detect ('skin' or 'eye')
    
    Returns:
        Dictionary containing disease prediction and confidence score
    """
    try:
        with open(image_path, "rb") as f:
            response = requests.post(
                FASTAPI_URL,
                files={"file": f},
                data={
                    "animal": animal,
                    "disease_type": disease_type,
                    "user_id": "demo"
                }
            )
        
        response.raise_for_status()  # Raise exception for bad status codes
        result = response.json()
        
        # Ensure we return a dict, not a string
        if isinstance(result, str):
            result = json.loads(result)
        
        return result
    
    except FileNotFoundError:
        return {"error": f"Image file not found: {image_path}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"FastAPI request failed: {str(e)}"}
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse API response: {str(e)}"}


@tool
def analyze_pet_image(image_path: str, animal: str, disease_type: str) -> dict:
    """
    Analyze pet image and return disease prediction.
    
    Args:
        image_path: Path to the pet image file
        animal: Type of animal ('dog' or 'cat')
        disease_type: Type of disease to detect ('skin' or 'eye')
    
    Returns:
        Dictionary containing disease prediction and confidence score
    """
    return _analyze_pet_image_impl(image_path, animal, disease_type)


def _analyze_medical_document_vlm_impl(image_path: str) -> dict:
    """
    Internal implementation of medical document analysis using VLM.
    This function contains the actual logic and can be called directly.
    
    Args:
        image_path: Path to the medical document image file
    
    Returns:
        Dictionary containing extracted data from the document
    """
    try:
        logger.info(f"VLM Tool: Analyzing medical document: {image_path}")
        result = analyze_medical_document_vlm(image_path)
        logger.info(f"VLM Tool: Extraction result: {json.dumps(result, indent=2)[:500]}")
        return result
    except Exception as e:
        logger.error(f"VLM Tool: Error: {e}")
        return {"error": f"Failed to analyze medical document: {str(e)}"}


@tool
def analyze_medical_document(image_path: str) -> dict:
    """
    Analyze a medical document image (prescription, vaccine card, or medical report)
    and extract all data in structured JSON format.
    
    Args:
        image_path: Path to the medical document image file
    
    Returns:
        Dictionary containing extracted data from the document
    """
    return _analyze_medical_document_vlm_impl(image_path)
