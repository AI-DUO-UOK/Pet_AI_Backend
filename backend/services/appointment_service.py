from typing import Dict, List, Optional
from datetime import datetime
import time
import logging
from backend.core.supabase_config import supabase

logger = logging.getLogger(__name__)

class AppointmentService:
    """Service for managing appointments and reviews"""

    @staticmethod
    def create_appointment(
        pet_id: str,
        clinic_id: str,
        owner_id: str,
        appointment_date: str,
        appointment_time: str,
        reason: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict:
        """Create appointment"""
        try:
            appointment_data = {
                "pet_id": pet_id,
                "clinic_id": clinic_id,
                "owner_id": owner_id,
                "appointment_date": appointment_date,
                "appointment_time": appointment_time,
                "reason": reason,
                "notes": notes,
                "status": "scheduled"
            }
            
            response = supabase.table("appointments").insert(appointment_data).execute()
            if not response.data:
                return {"success": False, "error": "Failed to create appointment"}

            created = response.data[0]
            
            # Send notifications
            try:
                AppointmentService._send_appointment_notifications(created)
            except Exception as notif_err:
                logger.warning(f"Failed to send appointment notifications: {notif_err}")

            return {
                "success": True,
                "appointment_id": created["id"],
                "appointment": created,
                "message": "Appointment created successfully!"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error creating appointment: {str(e)}"
            }

    @staticmethod
    def get_owner_appointments(owner_id: str) -> Dict:
        """Get all appointments for pet owner"""
        try:
            response = supabase.table("appointments").select("*").eq("owner_id", owner_id).execute()
            appointments = response.data or []
            # We can enrich reviews here if needed
            return {
                "success": True,
                "appointments": appointments,
                "count": len(appointments)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error fetching owner appointments: {str(e)}"
            }

    @staticmethod
    def get_clinic_appointments(clinic_id: str) -> Dict:
        """Get all appointments for clinic"""
        try:
            response = supabase.table("appointments").select("*").eq("clinic_id", clinic_id).execute()
            appointments = response.data or []
            return {
                "success": True,
                "appointments": appointments,
                "count": len(appointments)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error fetching clinic appointments: {str(e)}"
            }

    @staticmethod
    def get_pet_appointments(pet_id: str) -> Dict:
        """Get all appointments for a pet"""
        try:
            response = supabase.table("appointments").select("*").eq("pet_id", pet_id).execute()
            appointments = response.data or []
            return {
                "success": True,
                "appointments": appointments,
                "count": len(appointments)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error fetching pet appointments: {str(e)}"
            }

    @staticmethod
    def update_appointment_status(appointment_id: str, status: str) -> Dict:
        """Update appointment status (scheduled, completed, cancelled, etc.)"""
        try:
            # Fetch appointment
            appt_resp = supabase.table("appointments").select("*").eq("id", appointment_id).execute()
            if not appt_resp.data:
                return {"success": False, "error": "Appointment not found"}
            
            appt = appt_resp.data[0]
            
            # Update status
            timestamp = datetime.utcnow().isoformat()
            supabase.table("appointments").update({"status": status, "updated_at": timestamp}).eq("id", appointment_id).execute()
            
            # Send status update notifications
            try:
                AppointmentService._send_status_notifications(appt, status)
            except Exception as notif_err:
                logger.warning(f"Failed to send status notifications: {notif_err}")

            return {
                "success": True,
                "appointment_id": appointment_id,
                "status": status
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error updating appointment status: {str(e)}"
            }

    @staticmethod
    def create_review(
        appointment_id: str,
        rating: int,
        treatment: str,
        comment: Optional[str] = None,
    ) -> Dict:
        """Create review for a completed appointment"""
        try:
            # Fetch appointment
            appt_resp = supabase.table("appointments").select("*").eq("id", appointment_id).execute()
            if not appt_resp.data:
                return {"success": False, "error": "Appointment not found"}
            
            appt = appt_resp.data[0]
            if appt.get("status") != "completed":
                return {"success": False, "error": "Only completed appointments can be reviewed"}

            review_data = {
                "appointment_id": appointment_id,
                "clinic_id": appt.get("clinic_id"),
                "pet_id": appt.get("pet_id"),
                "owner_id": appt.get("owner_id"),
                "rating": rating,
                "treatment": treatment[:100],
                "comment": comment,
            }

            response = supabase.table("clinic_reviews").insert(review_data).execute()
            if not response.data:
                return {"success": False, "error": "Failed to create review"}

            created_review = response.data[0]

            # Notify clinic
            try:
                AppointmentService._notify_clinic_about_review(created_review)
            except Exception as notif_err:
                logger.warning(f"Failed to notify clinic about review: {notif_err}")

            return {
                "success": True,
                "review": created_review,
                "message": "Review submitted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error creating review: {str(e)}"
            }

    @staticmethod
    def get_reviews_for_clinic(clinic_id: str) -> Dict:
        """Get reviews for a clinic"""
        try:
            response = supabase.table("clinic_reviews").select("*").eq("clinic_id", clinic_id).order("created_at", desc=True).execute()
            reviews = response.data or []
            avg_rating = round(sum(r.get("rating", 0) for r in reviews) / len(reviews), 1) if reviews else 0.0
            return {
                "success": True,
                "reviews": reviews,
                "count": len(reviews),
                "average_rating": avg_rating
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error fetching clinic reviews: {str(e)}"
            }

    # Private helper methods for notifications
    @staticmethod
    def _create_notification(user_id: str, type_: str, title: str, message: str, role: str, entity_type: str, entity_id: str):
        payload = {
            "user_id": user_id,
            "user_role": role,
            "type": type_,
            "title": title,
            "message": message,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "is_read": False,
            "created_at": datetime.utcnow().isoformat(),
        }
        supabase.table("notifications").insert(payload).execute()

    @staticmethod
    def _send_appointment_notifications(appt: Dict):
        pet_resp = supabase.table("pets").select("name").eq("id", appt["pet_id"]).execute()
        pet_name = pet_resp.data[0]["name"] if pet_resp.data else "your pet"
        
        clinic_resp = supabase.table("clinics").select("clinic_name", "user_id").eq("id", appt["clinic_id"]).execute()
        clinic_name = "Clinic"
        clinic_user_id = None
        if clinic_resp.data:
            clinic_name = clinic_resp.data[0]["clinic_name"]
            clinic_user_id = clinic_resp.data[0]["user_id"]

        title = "Appointment Scheduled"
        message = f"{pet_name} has a new appointment with {clinic_name} on {appt['appointment_date']} at {appt['appointment_time']}."
        
        # Notify owner
        AppointmentService._create_notification(appt["owner_id"], "appointment", title, message, "owner", "appointment", appt["id"])
        
        # Notify clinic
        if clinic_user_id:
            AppointmentService._create_notification(clinic_user_id, "appointment", title, message, "clinic", "appointment", appt["id"])

    @staticmethod
    def _send_status_notifications(appt: Dict, status: str):
        pet_resp = supabase.table("pets").select("name").eq("id", appt["pet_id"]).execute()
        pet_name = pet_resp.data[0]["name"] if pet_resp.data else "your pet"
        
        clinic_resp = supabase.table("clinics").select("clinic_name", "user_id").eq("id", appt["clinic_id"]).execute()
        clinic_name = "Clinic"
        clinic_user_id = None
        if clinic_resp.data:
            clinic_name = clinic_resp.data[0]["clinic_name"]
            clinic_user_id = clinic_resp.data[0]["user_id"]

        status_label = status.replace("_", " ").title()
        title = f"Appointment {status_label}"
        message = f"{pet_name}'s appointment with {clinic_name} on {appt['appointment_date']} at {appt['appointment_time']} was updated to {status_label}."
        
        # Notify owner
        AppointmentService._create_notification(appt["owner_id"], "appointment_status", title, message, "owner", "appointment", appt["id"])
        
        # Notify clinic
        if clinic_user_id:
            AppointmentService._create_notification(clinic_user_id, "appointment_status", title, message, "clinic", "appointment", appt["id"])

    @staticmethod
    def _notify_clinic_about_review(review: Dict):
        clinic_resp = supabase.table("clinics").select("user_id", "clinic_name").eq("id", review["clinic_id"]).execute()
        if clinic_resp.data and clinic_resp.data[0].get("user_id"):
            clinic_user_id = clinic_resp.data[0]["user_id"]
            clinic_name = clinic_resp.data[0]["clinic_name"]
            AppointmentService._create_notification(
                clinic_user_id,
                "clinic_review",
                "New Client Review",
                f"A pet owner left a {review['rating']}-star review for {clinic_name}.",
                "clinic",
                "review",
                review["id"]
            )
        
