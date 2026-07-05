from typing import Dict, Optional, List
from core.supabase_config import supabase

class UserRepository:
    """Repository for managing users and pet owners tables"""

    @staticmethod
    def get_by_id(user_id: str) -> Optional[Dict]:
        """Fetch user by ID"""
        response = supabase.table("users").select("*").eq("id", user_id).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def update_user(user_id: str, updates: Dict) -> Optional[Dict]:
        """Update user record"""
        response = supabase.table("users").update(updates).eq("id", user_id).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def get_owner_profile(user_id: str) -> Optional[Dict]:
        """Fetch pet owner profile by user_id"""
        response = supabase.table("pet_owners").select("*").eq("user_id", user_id).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def insert_owner_profile(owner_data: Dict) -> Optional[Dict]:
        """Create new pet owner profile"""
        response = supabase.table("pet_owners").insert(owner_data).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def update_owner_profile(user_id: str, updates: Dict) -> Optional[Dict]:
        """Update pet owner profile details"""
        response = supabase.table("pet_owners").update(updates).eq("user_id", user_id).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def insert_notification(notification_data: Dict) -> Optional[Dict]:
        """Create a notification"""
        response = supabase.table("notifications").insert(notification_data).execute()
        return response.data[0] if response.data else None

