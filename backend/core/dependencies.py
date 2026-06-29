from fastapi import Request, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from backend.core.security import verify_supabase_jwt, security_scheme
try:
    from chatbot.supabase_config import supabase
except ImportError:
    supabase = None
from typing import Dict, List, Optional

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> Dict:
    """
    Dependency to get the currently authenticated user.
    Verifies the JWT and fetches their profile from public.users.
    """
    if supabase is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Supabase integration not available on this instance"
        )
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials missing"
        )
    
    token = credentials.credentials
    # Verify JWT via Supabase Auth
    user_data = verify_supabase_jwt(token)
    user_id = user_data["id"]
    
    # Query the public.users table to get the latest role and status
    try:
        user_response = supabase.table("users").select("*").eq("id", user_id).execute()
        if not user_response.data:
            # Fallback to metadata if user doesn't exist yet (e.g., during signup)
            return user_data
            
        db_user = user_response.data[0]
        
        # Return merged user data
        return {
            "id": user_id,
            "email": user_data["email"],
            "role": db_user.get("role", "owner"),
            "phone": db_user.get("phone_number", ""),
            "full_name": db_user.get("full_name", ""),
            "avatar_url": db_user.get("avatar_url", "")
        }
    except HTTPException:
        raise
    except Exception as e:
        # Fallback to verified JWT data if DB query fails
        return user_data

class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles
        
    def __call__(self, current_user: Dict = Depends(get_current_user)) -> Dict:
        if current_user["role"] not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(self.allowed_roles)}"
            )
        return current_user

# Helper dependency builders
def require_role(role: str):
    return Depends(RoleChecker([role]))

def require_any_role(roles: List[str]):
    return Depends(RoleChecker(roles))
