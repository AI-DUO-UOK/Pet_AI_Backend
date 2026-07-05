from typing import Dict, List, Optional
from core.supabase_config import supabase
from interfaces.pet_repository import IPetRepository

class PetRepository(IPetRepository):
    """Repository for managing pets and their vaccine record uploads"""

    def insert_pet(self, pet_data: Dict) -> Optional[Dict]:
        """Create new pet profile"""
        response = supabase.table("pets").insert(pet_data).execute()
        return response.data[0] if response.data else None

    def get_by_id(self, pet_id: str) -> Optional[Dict]:
        """Fetch pet profile by ID"""
        response = supabase.table("pets").select("*").eq("id", pet_id).execute()
        return response.data[0] if response.data else None

    def get_user_pets(self, user_id: str) -> List[Dict]:
        """Fetch all pets for a user"""
        response = supabase.table("pets").select("*").eq("user_id", user_id).execute()
        return response.data or []

    def update_pet(self, pet_id: str, updates: Dict) -> Optional[Dict]:
        """Update pet profile details"""
        response = supabase.table("pets").update(updates).eq("id", pet_id).execute()
        return response.data[0] if response.data else None

    def insert_vaccine_record(self, record_data: Dict) -> Optional[Dict]:
        """Insert vaccine document record into database"""
        response = supabase.table("vaccine_records").insert(record_data).execute()
        return response.data[0] if response.data else None

    def get_vaccine_records(self, pet_id: str) -> List[Dict]:
        """Get uploaded vaccine documents list for a pet"""
        response = supabase.table("vaccine_records").select("*").eq("pet_id", pet_id).execute()
        return response.data or []
