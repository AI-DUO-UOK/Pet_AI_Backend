"""
Vaccine Document VLM Extraction Service.
Uses Qwen2.5-VL-72B via OpenRouter to extract vaccine data from uploaded
vaccine booklet/card images.
"""

import json
import logging
from chatbot.vlm import _query_vlm_qwen

logger = logging.getLogger(__name__)

VACCINE_EXTRACTION_PROMPT = """
Extract all vaccine information from this vaccine card/booklet image.

Return ONLY valid JSON in this exact format, no other text:
{
  "vaccines": [
    {
      "vaccine_name": "Rabies",
      "vaccination_date": "2025-05-12",
      "next_due_date": "2026-05-12",
      "veterinarian": "Dr. Silva"
    }
  ]
}

If you cannot identify a field, use null for that field.
If the image is not a vaccine card or booklet, return {"error": "This does not appear to be a vaccine document."}
"""


def extract_vaccine_data_vlm(image_path: str) -> dict:
    """
    Analyze a vaccine card/booklet image using Qwen2.5-VL-72B via OpenRouter.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Dictionary with 'vaccines' key containing list of vaccine records.
        Returns {"error": "..."} on failure.
    """
    try:
        result_text = _query_vlm_qwen(
            image_path=image_path,
            system_prompt="You are a medical document analysis AI specialized in extracting vaccine data. You ALWAYS return valid JSON only.",
            user_prompt=VACCINE_EXTRACTION_PROMPT
        )
        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            logger.warning("Vaccine VLM: Response was not valid JSON")
            return {"error": "Failed to parse vaccine data", "raw_text": result_text}
            
    except FileNotFoundError:
        logger.error(f"Vaccine VLM: Image file not found: {image_path}")
        return {"error": f"Image file not found: {image_path}"}
    except Exception as e:
        logger.error(f"Vaccine VLM: Error: {e}")
        return {"error": f"Failed to analyze vaccine document: {str(e)}"}