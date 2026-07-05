from typing import Dict, List, Optional
from core.supabase_config import supabase
from interfaces.appointment_repository import IAppointmentRepository

class AppointmentRepository(IAppointmentRepository):
    """Repository for managing appointments and clinic reviews tables"""

    def insert_appointment(self, appointment_data: Dict) -> Optional[Dict]:
        """Create new appointment"""
        response = supabase.table("appointments").insert(appointment_data).execute()
        return response.data[0] if response.data else None

    def get_by_id(self, appointment_id: str) -> Optional[Dict]:
        """Fetch appointment by ID"""
        response = supabase.table("appointments").select("*").eq("id", appointment_id).execute()
        return response.data[0] if response.data else None

    def get_user_appointments(self, user_id: str) -> List[Dict]:
        """Get all appointments for a pet owner user"""
        response = supabase.table("appointments")\
            .select("*, clinics(clinic_name, address, phone), pets(name, type, breed)")\
            .eq("owner_id", user_id)\
            .order("appointment_date", desc=True)\
            .order("appointment_time", desc=True)\
            .execute()
        return response.data or []

    def get_clinic_appointments(self, clinic_id: str) -> List[Dict]:
        """Get all appointments for a clinic"""
        response = supabase.table("appointments")\
            .select("*, pets(name, type, breed, gender, date_of_birth), pet_owners(full_name, phone, email)")\
            .eq("clinic_id", clinic_id)\
            .order("appointment_date", desc=True)\
            .order("appointment_time", desc=True)\
            .execute()
        return response.data or []

    def update_appointment(self, appointment_id: str, updates: Dict) -> Optional[Dict]:
        """Update appointment details (status, notes, etc.)"""
        response = supabase.table("appointments").update(updates).eq("id", appointment_id).execute()
        return response.data[0] if response.data else None

    def insert_review(self, review_data: Dict) -> Optional[Dict]:
        """Insert clinic review"""
        response = supabase.table("clinic_reviews").insert(review_data).execute()
        return response.data[0] if response.data else None

    def get_reviews_by_clinic(self, clinic_id: str) -> List[Dict]:
        """Get reviews for a clinic"""
        response = supabase.table("clinic_reviews")\
            .select("*, pets(name), pet_owners(full_name)")\
            .eq("clinic_id", clinic_id)\
            .execute()
        return response.data or []

    def get_appointments_by_pet(self, pet_id: str) -> List[Dict]:
        """Get all appointments for a pet"""
        response = supabase.table("appointments").select("*").eq("pet_id", pet_id).execute()
        return response.data or []
