from typing import Dict, List, Optional
from core.supabase_config import supabase
from interfaces.clinic_repository import IClinicRepository

class ClinicRepository(IClinicRepository):
    """Repository for managing clinics table and listings"""

    def insert_clinic(self, clinic_data: Dict) -> Optional[Dict]:
        """Create new clinic registration"""
        response = supabase.table("clinics").insert(clinic_data).execute()
        return response.data[0] if response.data else None

    def get_by_id(self, clinic_id: str) -> Optional[Dict]:
        """Fetch clinic profile by ID"""
        response = supabase.table("clinics").select("*").eq("id", clinic_id).execute()
        return response.data[0] if response.data else None

    def get_by_user_id(self, user_id: str) -> Optional[Dict]:
        """Fetch clinic profile by clinic owner user_id"""
        response = supabase.table("clinics").select("*").eq("user_id", user_id).execute()
        return response.data[0] if response.data else None

    def get_all_clinics(self) -> List[Dict]:
        """Get all clinics ordered by creation date (for admin)"""
        response = supabase.table("clinics").select("*").order("created_at", desc=True).execute()
        return response.data or []

    def get_public_clinics(self) -> List[Dict]:
        """Get verified, active clinics (for public search)"""
        response = supabase.table("clinics").select("*").eq("is_verified", True).eq("is_active", True).execute()
        return response.data or []

    def update_clinic(self, clinic_id: str, updates: Dict) -> Optional[Dict]:
        """Update clinic profile details"""
        response = supabase.table("clinics").update(updates).eq("id", clinic_id).execute()
        return response.data[0] if response.data else None

    def reject_clinic(self, clinic_id: str, updates: Dict) -> Optional[Dict]:
        """
        Reject a clinic registration.
        Supports structured rejection columns (rejection_reason, rejected_at)
        and falls back gracefully to description-only updates if the migration hasn't run.
        """
        try:
            # Try to write to new columns
            response = supabase.table("clinics").update(updates).eq("id", clinic_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            # Fallback if columns do not exist
            if "rejection_reason" in str(e) or "rejected_at" in str(e) or "column" in str(e).lower():
                fallback_updates = {
                    "is_verified": updates.get("is_verified", False),
                    "description": updates.get("description")
                }
                response = supabase.table("clinics").update(fallback_updates).eq("id", clinic_id).execute()
                return response.data[0] if response.data else None
            raise
