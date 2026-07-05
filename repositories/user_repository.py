from typing import Dict, Optional
from core.supabase_config import supabase
from interfaces.user_repository import IUserRepository

class UserRepository(IUserRepository):
    """Repository for managing users and pet owners tables"""

    def get_by_id(self, user_id: str) -> Optional[Dict]:
        """Fetch user by ID"""
        response = supabase.table("users").select("*").eq("id", user_id).execute()
        return response.data[0] if response.data else None

    def update_user(self, user_id: str, updates: Dict) -> Optional[Dict]:
        """Update user record"""
        response = supabase.table("users").update(updates).eq("id", user_id).execute()
        return response.data[0] if response.data else None

    def get_owner_profile(self, user_id: str) -> Optional[Dict]:
        """Fetch pet owner profile by user_id"""
        response = supabase.table("pet_owners").select("*").eq("user_id", user_id).execute()
        return response.data[0] if response.data else None

    def insert_owner_profile(self, owner_data: Dict) -> Optional[Dict]:
        """Create new pet owner profile"""
        response = supabase.table("pet_owners").insert(owner_data).execute()
        return response.data[0] if response.data else None

    def update_owner_profile(self, user_id: str, updates: Dict) -> Optional[Dict]:
        """Update pet owner profile details"""
        response = supabase.table("pet_owners").update(updates).eq("user_id", user_id).execute()
        return response.data[0] if response.data else None

    def insert_notification(self, payload: Dict) -> Optional[Dict]:
        """Create a notification"""
        response = supabase.table("notifications").insert(payload).execute()
        return response.data[0] if response.data else None
