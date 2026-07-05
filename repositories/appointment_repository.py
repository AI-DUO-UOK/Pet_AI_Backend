from typing import Dict, List, Optional
from core.supabase_config import supabase

class AppointmentRepository:
    """Repository for managing appointments and clinic reviews tables"""

    @staticmethod
    def insert_appointment(appointment_data: Dict) -> Optional[Dict]:
        """Create new appointment"""
        response = supabase.table("appointments").insert(appointment_data).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def get_by_id(appointment_id: str) -> Optional[Dict]:
        """Fetch appointment by ID"""
        response = supabase.table("appointments").select("*").eq("id", appointment_id).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def get_user_appointments(user_id: str) -> List[Dict]:
        """Get all appointments for a pet owner user"""
        response = supabase.table("appointments")\
            .select("*, clinics(clinic_name, address, phone), pets(name, type, breed)")\
            .eq("owner_id", user_id)\
            .order("appointment_date", desc=True)\
            .order("appointment_time", desc=True)\
            .execute()
        return response.data or []

    @staticmethod
    def get_clinic_appointments(clinic_id: str) -> List[Dict]:
        """Get all appointments for a clinic"""
        response = supabase.table("appointments")\
            .select("*, pets(name, type, breed, gender, date_of_birth), pet_owners(full_name, phone, email)")\
            .eq("clinic_id", clinic_id)\
            .order("appointment_date", desc=True)\
            .order("appointment_time", desc=True)\
            .execute()
        return response.data or []

    @staticmethod
    def update_appointment(appointment_id: str, updates: Dict) -> Optional[Dict]:
        """Update appointment details (status, notes, etc.)"""
        response = supabase.table("appointments").update(updates).eq("id", appointment_id).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def insert_review(review_data: Dict) -> Optional[Dict]:
        """Insert clinic review"""
        response = supabase.table("clinic_reviews").insert(review_data).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def get_reviews_by_clinic(clinic_id: str) -> List[Dict]:
        """Get reviews for a clinic"""
        response = supabase.table("clinic_reviews")\
            .select("*, pets(name), pet_owners(full_name)")\
            .eq("clinic_id", clinic_id)\
            .execute()
        return response.data or []

    @staticmethod
    def get_appointments_by_pet(pet_id: str) -> List[Dict]:
        """Get all appointments for a pet"""
        response = supabase.table("appointments").select("*").eq("pet_id", pet_id).execute()
        return response.data or []

