import requests
import json
from langchain.tools import tool

FASTAPI_URL = "http://127.0.0.1:8000/analyze-image"

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