from typing import Dict, List, Optional
from datetime import datetime
import logging
from interfaces.appointment_repository import IAppointmentRepository
from interfaces.pet_repository import IPetRepository
from interfaces.clinic_repository import IClinicRepository
from interfaces.user_repository import IUserRepository

logger = logging.getLogger(__name__)

class AppointmentService:
    """Service for managing appointments and reviews"""

    def __init__(
        self,
        appt_repo: IAppointmentRepository,
        pet_repo: IPetRepository,
        clinic_repo: IClinicRepository,
        user_repo: IUserRepository
    ):
        self.appt_repo = appt_repo
        self.pet_repo = pet_repo
        self.clinic_repo = clinic_repo
        self.user_repo = user_repo

    def create_appointment(
        self,
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
            
            created = self.appt_repo.insert_appointment(appointment_data)
            if not created:
                return {"success": False, "error": "Failed to create appointment"}
            
            # Send notifications
            try:
                self._send_appointment_notifications(created)
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

    def get_owner_appointments(self, owner_id: str) -> Dict:
        """Get all appointments for pet owner"""
        try:
            appointments = self.appt_repo.get_user_appointments(owner_id)
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

    def get_clinic_appointments(self, clinic_id: str) -> Dict:
        """Get all appointments for clinic"""
        try:
            appointments = self.appt_repo.get_clinic_appointments(clinic_id)
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

    def get_pet_appointments(self, pet_id: str) -> Dict:
        """Get all appointments for a pet"""
        try:
            appointments = self.appt_repo.get_appointments_by_pet(pet_id)
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

    def update_appointment_status(self, appointment_id: str, status: str) -> Dict:
        """Update appointment status (scheduled, completed, cancelled, etc.)"""
        try:
            # Fetch appointment
            appt = self.appt_repo.get_by_id(appointment_id)
            if not appt:
                return {"success": False, "error": "Appointment not found"}
            
            # Update status
            timestamp = datetime.utcnow().isoformat()
            self.appt_repo.update_appointment(appointment_id, {"status": status, "updated_at": timestamp})
            
            # Send status update notifications
            try:
                self._send_status_notifications(appt, status)
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

    def create_review(
        self,
        appointment_id: str,
        rating: int,
        treatment: str,
        comment: Optional[str] = None,
    ) -> Dict:
        """Create review for a completed appointment"""
        try:
            # Fetch appointment
            appt = self.appt_repo.get_by_id(appointment_id)
            if not appt:
                return {"success": False, "error": "Appointment not found"}
            
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

            created_review = self.appt_repo.insert_review(review_data)
            if not created_review:
                return {"success": False, "error": "Failed to create review"}

            # Notify clinic
            try:
                self._notify_clinic_about_review(created_review)
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

    def get_reviews_for_clinic(self, clinic_id: str) -> Dict:
        """Get reviews for a clinic"""
        try:
            reviews = self.appt_repo.get_reviews_by_clinic(clinic_id)
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
    def _create_notification(self, user_id: str, type_: str, title: str, message: str, role: str, entity_type: str, entity_id: str):
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
        self.user_repo.insert_notification(payload)

    def _send_appointment_notifications(self, appt: Dict):
        pet = self.pet_repo.get_by_id(appt["pet_id"])
        pet_name = pet["name"] if pet else "your pet"
        
        clinic = self.clinic_repo.get_by_id(appt["clinic_id"])
        clinic_name = "Clinic"
        clinic_user_id = None
        if clinic:
            clinic_name = clinic["clinic_name"]
            clinic_user_id = clinic["user_id"]

        title = "Appointment Scheduled"
        message = f"{pet_name} has a new appointment with {clinic_name} on {appt['appointment_date']} at {appt['appointment_time']}."
        
        # Notify owner
        self._create_notification(appt["owner_id"], "appointment", title, message, "owner", "appointment", appt["id"])
        
        # Notify clinic
        if clinic_user_id:
            self._create_notification(clinic_user_id, "appointment", title, message, "clinic", "appointment", appt["id"])

    def _send_status_notifications(self, appt: Dict, status: str):
        pet = self.pet_repo.get_by_id(appt["pet_id"])
        pet_name = pet["name"] if pet else "your pet"
        
        clinic = self.clinic_repo.get_by_id(appt["clinic_id"])
        clinic_name = "Clinic"
        clinic_user_id = None
        if clinic:
            clinic_name = clinic["clinic_name"]
            clinic_user_id = clinic["user_id"]

        status_label = status.replace("_", " ").title()
        title = f"Appointment {status_label}"
        message = f"{pet_name}'s appointment with {clinic_name} on {appt['appointment_date']} at {appt['appointment_time']} was updated to {status_label}."
        
        # Notify owner
        self._create_notification(appt["owner_id"], "appointment_status", title, message, "owner", "appointment", appt["id"])
        
        # Notify clinic
        if clinic_user_id:
            self._create_notification(clinic_user_id, "appointment_status", title, message, "clinic", "appointment", appt["id"])

    def _notify_clinic_about_review(self, review: Dict):
        clinic = self.clinic_repo.get_by_id(review["clinic_id"])
        if clinic and clinic.get("user_id"):
            clinic_user_id = clinic["user_id"]
            clinic_name = clinic["clinic_name"]
            self._create_notification(
                clinic_user_id,
                "clinic_review",
                "New Client Review",
                f"A pet owner left a {review['rating']}-star review for {clinic_name}.",
                "clinic",
                "review",
                review["id"]
            )
