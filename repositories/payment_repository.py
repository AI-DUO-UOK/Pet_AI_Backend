from typing import Dict, List, Optional
from core.supabase_config import supabase

class PaymentRepository:
    """Repository for managing payments table"""

    @staticmethod
    def insert_payment(payment_data: Dict) -> Optional[Dict]:
        """Insert new payment transaction record"""
        response = supabase.table("payments").insert(payment_data).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def get_by_id(payment_id: str) -> Optional[Dict]:
        """Fetch payment record by ID"""
        response = supabase.table("payments").select("*, appointments(*)").eq("id", payment_id).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def get_payments_by_owner(owner_id: str) -> List[Dict]:
        """Fetch all payments for appointments owned by owner_id"""
        # Fetch appointments for owner
        appt_resp = supabase.table("appointments").select("id").eq("owner_id", owner_id).execute()
        if not appt_resp.data:
            return []
        
        appt_ids = [a["id"] for a in appt_resp.data]
        
        # Fetch payments matching appointment IDs
        payment_resp = supabase.table("payments")\
            .select("*, appointments(*, clinics(clinic_name))")\
            .in_("appointment_id", appt_ids)\
            .order("created_at", desc=True)\
            .execute()
            
        return payment_resp.data or []
