"""
Vision Language Model (VLM) Service for Pet AI Healthcare Chatbot.
Uses Qwen2.5-VL-72B via OpenRouter to extract data from medical documents,
vaccine cards, and prescriptions.
"""

import os
import base64
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Initialize OpenRouter client for VLM
VLM_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not VLM_API_KEY:
    raise ValueError("OPENROUTER_API_KEY not found in .env file")

_vlm_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=VLM_API_KEY,
)

VLM_MODEL = "qwen/qwen2.5-vl-72b-instruct"

# System prompt instructing VLM to always return JSON
VLM_SYSTEM_PROMPT = """You are a medical document analysis AI. Your ONLY job is to extract data from medical documents, vaccine cards, and prescriptions and return it as structured JSON.
You must ALWAYS return valid JSON only - no explanations, no markdown formatting around JSON, no extra text.
If the image is not a medical document, return {"error": "This does not appear to be a medical document."}"""

# Prompt sent to VLM for extraction
EXTRACTION_PROMPT = """
Extract all data from this medical document, vaccine card, or prescription and return it as JSON format.

For a prescription include fields like:
- medication_name
- dosage
- frequency
- duration
- prescribing_vet
- date
- notes

For a vaccine card include fields like:
- pet_name
- vaccine_name
- date_administered
- next_due_date
- veterinarian
- clinic_name

For a medical report include fields like:
- report_type
- diagnosis
- findings
- recommendations
- date
- veterinarian
- clinic_name

Return ONLY valid JSON, no other text.
"""


def _query_vlm_qwen(image_path: str, system_prompt: str, user_prompt: str) -> str:
    """
    Execute a VLM query against Qwen2.5-VL-72B on OpenRouter.
    Returns the cleaned raw text response from the model.
    """
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
    
    logger.info(f"VLM Query: Analyzing image: {image_path} ({len(base64_image)} bytes base64)")
    
    response = _vlm_client.chat.completions.create(
        model=VLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_prompt
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
    logger.info(f"VLM Query: Raw response length: {len(result_text)} chars")
    
    # Clean markdown code blocks if present
    if result_text.startswith("```json"):
        result_text = result_text[7:]
    if result_text.startswith("```"):
        result_text = result_text[3:]
    if result_text.endswith("```"):
        result_text = result_text[:-3]
    return result_text.strip()


def analyze_medical_document_vlm(image_path: str) -> dict:
    """
    Analyze a medical document image using Qwen2.5-VL-72B via OpenRouter.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Dictionary containing extracted data in JSON format.
        Returns {"error": "..."} on failure.
    """
    try:
        result_text = _query_vlm_qwen(
            image_path=image_path,
            system_prompt=VLM_SYSTEM_PROMPT,
            user_prompt=EXTRACTION_PROMPT
        )
        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            logger.warning("VLM: Response was not valid JSON, returning as text")
            return {"extracted_text": result_text}
            
    except FileNotFoundError:
        logger.error(f"VLM: Image file not found: {image_path}")
        return {"error": f"Image file not found: {image_path}"}
    except Exception as e:
        logger.error(f"VLM: Error analyzing document: {e}")
        return {"error": f"Failed to analyze document: {str(e)}"}