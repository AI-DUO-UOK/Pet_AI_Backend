from typing import Dict, List, Optional
from core.supabase_config import supabase

class PetRepository:
    """Repository for managing pets and their vaccine record uploads"""

    @staticmethod
    def insert_pet(pet_data: Dict) -> Optional[Dict]:
        """Create new pet profile"""
        response = supabase.table("pets").insert(pet_data).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def get_by_id(pet_id: str) -> Optional[Dict]:
        """Fetch pet profile by ID"""
        response = supabase.table("pets").select("*").eq("id", pet_id).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def get_user_pets(user_id: str) -> List[Dict]:
        """Fetch all pets for a user"""
        response = supabase.table("pets").select("*").eq("user_id", user_id).execute()
        return response.data or []

    @staticmethod
    def update_pet(pet_id: str, updates: Dict) -> Optional[Dict]:
        """Update pet profile details"""
        response = supabase.table("pets").update(updates).eq("id", pet_id).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def insert_vaccine_record(record_data: Dict) -> Optional[Dict]:
        """Insert vaccine document record into database"""
        response = supabase.table("vaccine_records").insert(record_data).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def get_vaccine_records(pet_id: str) -> List[Dict]:
        """Get uploaded vaccine documents list for a pet"""
        response = supabase.table("vaccine_records").select("*").eq("pet_id", pet_id).execute()
        return response.data or []
