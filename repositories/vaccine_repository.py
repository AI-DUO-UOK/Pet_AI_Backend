from typing import Dict, List, Optional
from core.supabase_config import supabase
from interfaces.vaccine_repository import IVaccineRepository

class VaccineRepository(IVaccineRepository):
    """Repository for managing vaccination_records and vaccine_documents tables"""

    def insert_vaccine_document(self, doc_data: Dict) -> Optional[Dict]:
        """Insert uploaded vaccine document details"""
        response = supabase.table("vaccine_documents").insert(doc_data).execute()
        return response.data[0] if response.data else None

    def insert_vaccination_record(self, record_data: Dict) -> Optional[Dict]:
        """Insert vaccination event record"""
        response = supabase.table("vaccination_records").insert(record_data).execute()
        return response.data[0] if response.data else None

    def get_vaccination_records(self, pet_id: str) -> List[Dict]:
        """Fetch vaccination events list for a pet, ordered by date"""
        response = supabase.table("vaccination_records")\
            .select("*")\
            .eq("pet_id", pet_id)\
            .order("vaccination_date", desc=True)\
            .execute()
        return response.data or []

    def get_vaccine_documents(self, pet_id: str) -> List[Dict]:
        """Fetch uploaded vaccine booklet document images for a pet"""
        response = supabase.table("vaccine_documents")\
            .select("*")\
            .eq("pet_id", pet_id)\
            .order("uploaded_at", desc=True)\
            .execute()
        return response.data or []

    def get_records_with_due_dates(self) -> List[Dict]:
        """Get all vaccination records with next due dates for reminders"""
        response = supabase.table("vaccination_records")\
            .select("*, pets!inner(user_id, name)")\
            .not_.is_("next_due_date", "null")\
            .execute()
        return response.data or []

    def check_notification_log_exists(self, record_id: str, notification_type: str, sent_date: str) -> bool:
        """Check if reminder notification was already sent today"""
        response = supabase.table("notification_logs")\
            .select("id")\
            .eq("vaccination_id", record_id)\
            .eq("notification_type", notification_type)\
            .eq("sent_date", sent_date)\
            .execute()
        return bool(response.data)

    def log_notification_sent(self, log_data: Dict) -> Optional[Dict]:
        """Log a sent reminder notification"""
        response = supabase.table("notification_logs").insert(log_data).execute()
        return response.data[0] if response.data else None
