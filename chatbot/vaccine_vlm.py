"""
Vaccine Document VLM Extraction Service.
Uses Qwen2.5-VL-72B via OpenRouter to extract vaccine data from uploaded
vaccine booklet/card images. This is completely separate from the main
chatbot's VLM service to avoid any interference.
"""

import os
import base64
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Initialize OpenRouter client (same API key, separate instance)
VLM_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not VLM_API_KEY:
    raise ValueError("OPENROUTER_API_KEY not found in .env file")

_vlm_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=VLM_API_KEY,
)

VLM_MODEL = "qwen/qwen2.5-vl-72b-instruct"

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
        # Read and encode image
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")
        
        # Determine image MIME type
        ext = os.path.splitext(image_path)[1].lower()
        mime_type = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
        }.get(ext, 'image/jpeg')
        
        logger.info(f"Vaccine VLM: Analyzing document: {image_path} ({len(base64_image)} bytes base64)")
        
        response = _vlm_client.chat.completions.create(
            model=VLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a medical document analysis AI specialized in extracting vaccine data. You ALWAYS return valid JSON only."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": VACCINE_EXTRACTION_PROMPT
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            temperature=0,
            max_tokens=2000
        )
        
        result_text = response.choices[0].message.content.strip()
        logger.info(f"Vaccine VLM: Raw response length: {len(result_text)} chars")
        
        # Clean markdown code blocks if present
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()
        
        try:
            result_json = json.loads(result_text)
            return result_json
        except json.JSONDecodeError:
            logger.warning(f"Vaccine VLM: Response was not valid JSON")
            return {"error": "Failed to parse vaccine data", "raw_text": result_text}
    
    except FileNotFoundError:
        logger.error(f"Vaccine VLM: Image file not found: {image_path}")
        return {"error": f"Image file not found: {image_path}"}
    except Exception as e:
        logger.error(f"Vaccine VLM: Error: {e}")
        return {"error": f"Failed to analyze vaccine document: {str(e)}"}