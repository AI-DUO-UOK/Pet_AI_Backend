import re
import os
import json

# Keywords for intent detection
SKIN_KEYWORDS = [
    "skin", "rash", "itch", "fur", "hair loss", "scab", "wound",
    "dermatitis", "fungal", "ringworm", "mange", "scabies", "allergic",
    "infection", "lesion", "bump", "spot", "dry", "flaky", "irritation"
]

EYE_KEYWORDS = [
    "eye", "sight", "vision", "discharge", "redness", "cloudiness",
    "swelling", "inflammation", "keratitis", "blepharitis", "entropion",
    "eyelid", "tumor", "cornea", "conjunctive", "watery", "crusty"
]


def extract_image_path(user_input: str) -> str:
    """
    Extract image file path from user input.
    Handles filenames with spaces, dots, and special characters.
    Supports formats like:
    - /path/to/image file.jpg (with spaces)
    - image.jpg
    - ~/Documents/image.jpg
    """
    # More robust pattern that handles spaces in filenames
    pattern = r'(/[^\n]*\.(?:jpg|jpeg|png|gif|bmp)|~/[^\n]*\.(?:jpg|jpeg|png|gif|bmp))'
    
    match = re.search(pattern, user_input, re.IGNORECASE)
    if match:
        path = match.group(1).strip()
        # Expand home directory
        if path.startswith("~"):
            path = os.path.expanduser(path)
        return path
    
    return None


def clean_agent_response(response: str) -> str:
    """
    Clean up the agent response by extracting actual content from JSON.
    """
    response_str = str(response).strip()
    
    # Remove "Action:" prefix if present
    if response_str.startswith("Action:"):
        response_str = response_str[7:].strip()
    
    # Try to parse as JSON
    try:
        # Remove markdown code block markers if present
        if response_str.startswith("```json"):
            response_str = response_str[7:]
        if response_str.startswith("```"):
            response_str = response_str[3:]
        if response_str.endswith("```"):
            response_str = response_str[:-3]
        response_str = response_str.strip()
        
        # Parse JSON
        if response_str.startswith("{"):
            data = json.loads(response_str)
            # Extract action_input from agent action
            if 'action_input' in data:
                return str(data['action_input'])
    except json.JSONDecodeError:
        pass
    
    # If not JSON, return as-is
    return response_str


def detect_disease_type(user_input: str) -> str:
    """
    Detect if the user is asking about skin or eye disease.
    Returns 'skin', 'eye', or None
    """
    user_lower = user_input.lower()
    
    for keyword in SKIN_KEYWORDS:
        if keyword in user_lower:
            return "skin"
    
    for keyword in EYE_KEYWORDS:
        if keyword in user_lower:
            return "eye"
    
    return None