from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict
import logging

try:
    from backend.core.supabase_config import supabase
except ImportError:
    supabase = None

logger = logging.getLogger(__name__)

security_scheme = HTTPBearer(auto_error=False)

def verify_supabase_jwt(token: str) -> Dict:
    """
    Verify Supabase JWT token using the Supabase auth client.
    Returns the user data dict if valid.
    Raises HTTPException 401 if invalid/expired.
    """
    if supabase is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Supabase integration not available on this instance"
        )
    try:
        # get_user verifies the token against the Supabase Auth server
        response = supabase.auth.get_user(token)
        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token"
            )
        
        user = response.user
        # Convert user object to dictionary
        user_data = {
            "id": user.id,
            "email": user.email,
            "role": user.user_metadata.get("role", "owner") if user.user_metadata else "owner",
            "phone": user.user_metadata.get("phone", "") if user.user_metadata else "",
            "is_active": user.user_metadata.get("is_active", True) if user.user_metadata else True
        }
        return user_data
    except Exception as e:
        logger.error(f"JWT verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )
