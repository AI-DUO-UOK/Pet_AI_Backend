"""
Vaccine Management Service for Pet AI Backend.
Handles vaccine record CRUD, VLM extraction storage, and reminder logic.
"""

import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any

from interfaces.vaccine_repository import IVaccineRepository
from interfaces.user_repository import IUserRepository
from chatbot.vaccine_vlm import extract_vaccine_data_vlm

logger = logging.getLogger(__name__)


class VaccineService:
    """Service for managing pet vaccination records."""

    def __init__(self, vaccine_repo: IVaccineRepository, user_repo: IUserRepository):
        self.vaccine_repo = vaccine_repo
        self.user_repo = user_repo

    async def upload_vaccine_document(
        self,
        pet_id: str,
        image_url: str,
        image_path: str
    ) -> Dict:
        """
        Upload a vaccine document image, extract data via VLM, 
        and store both the document and extracted records.
        
        Args:
            pet_id: Pet UUID
            image_url: Public URL of the uploaded image
            image_path: Local file path for VLM extraction
            
        Returns:
            Dictionary with success status and extracted records
        """
        try:
            # Step 1: Run VLM extraction
            extracted = await extract_vaccine_data_vlm(image_path)
            
            if isinstance(extracted, dict) and "error" in extracted:
                return {"success": False, "error": extracted["error"]}
            
            vaccines = extracted.get("vaccines", [])
            if not vaccines:
                return {"success": False, "error": "No vaccine data found in the image"}
            
            # Step 2: Store the document record
            doc_data = {
                "pet_id": pet_id,
                "image_url": image_url,
                "extracted_json": json.dumps(extracted),
            }
            doc_result = self.vaccine_repo.insert_vaccine_document(doc_data)
            document_id = doc_result["id"] if doc_result else None
            
            # Step 3: Store each extracted vaccine record
            stored_records = []
            for vaccine in vaccines:
                record_data = {
                    "pet_id": pet_id,
                    "vaccine_name": vaccine.get("vaccine_name"),
                    "vaccination_date": vaccine.get("vaccination_date"),
                    "next_due_date": vaccine.get("next_due_date"),
                    "veterinarian_name": vaccine.get("veterinarian"),
                    "batch_number": vaccine.get("batch_number"),
                    "clinic_name": vaccine.get("clinic_name"),
                    "source": "vlm_extracted",
                }
                
                # Only insert if vaccine_name and date are present
                if record_data["vaccine_name"] and record_data["vaccination_date"]:
                    result = self.vaccine_repo.insert_vaccination_record(record_data)
                    if result:
                        stored_records.append(result)
            
            return {
                "success": True,
                "document_id": document_id,
                "records_count": len(stored_records),
                "records": stored_records
            }
            
        except Exception as e:
            logger.error(f"Error uploading vaccine document: {e}")
            return {"success": False, "error": str(e)}

    def add_manual_vaccine_entry(
        self,
        pet_id: str,
        vaccine_name: str,
        vaccination_date: str,
        next_due_date: Optional[str] = None,
        batch_number: Optional[str] = None,
        veterinarian_name: Optional[str] = None,
        clinic_name: Optional[str] = None,
        clinic_id: Optional[str] = None,
        notes: Optional[str] = None,
        source: str = "vet_entry"
    ) -> Dict:
        """
        Add a vaccine record manually (by vet or owner).
        
        Args:
            pet_id: Pet UUID
            vaccine_name: Name of the vaccine
            vaccination_date: Date given (YYYY-MM-DD)
            next_due_date: Next due date (YYYY-MM-DD)
            batch_number: Optional batch/lot number
            veterinarian_name: Name of vet who administered
            clinic_name: Clinic name
            clinic_id: Clinic UUID
            notes: Additional notes
            source: 'manual' or 'vet_entry'
            
        Returns:
            Dictionary with success status and record data
        """
        try:
            if not vaccine_name or not vaccination_date:
                return {"success": False, "error": "Vaccine name and vaccination date are required"}
            
            record_data = {
                "pet_id": pet_id,
                "vaccine_name": vaccine_name,
                "vaccination_date": vaccination_date,
                "next_due_date": next_due_date,
                "batch_number": batch_number,
                "veterinarian_name": veterinarian_name,
                "clinic_name": clinic_name,
                "clinic_id": clinic_id,
                "notes": notes,
                "source": source,
            }
            
            result = self.vaccine_repo.insert_vaccination_record(record_data)
            
            if not result:
                return {"success": False, "error": "Failed to create vaccine record"}
            
            logger.info(f"Vaccine record created: {result['id']} for pet {pet_id}")
            
            return {
                "success": True,
                "record": result,
                "message": "Vaccine record added successfully!"
            }
            
        except Exception as e:
            logger.error(f"Error adding vaccine record: {e}")
            return {"success": False, "error": str(e)}

    def get_pet_vaccines(self, pet_id: str) -> Dict:
        """
        Get all vaccination records for a pet, ordered by date.
        
        Args:
            pet_id: Pet UUID
            
        Returns:
            Dictionary with success status and records list
        """
        try:
            records = self.vaccine_repo.get_vaccination_records(pet_id)
            return {
                "success": True,
                "records": records,
                "count": len(records)
            }
            
        except Exception as e:
            logger.error(f"Error fetching vaccines: {e}")
            return {"success": False, "error": str(e), "records": []}

    def get_pet_vaccine_documents(self, pet_id: str) -> Dict:
        """
        Get uploaded vaccine documents for a pet.
        
        Args:
            pet_id: Pet UUID
            
        Returns:
            Dictionary with success status and documents list
        """
        try:
            documents = self.vaccine_repo.get_vaccine_documents(pet_id)
            return {
                "success": True,
                "documents": documents
            }
            
        except Exception as e:
            logger.error(f"Error fetching vaccine documents: {e}")
            return {"success": False, "error": str(e), "documents": []}

    def check_and_send_reminders(self) -> Dict:
        """
        Check all vaccination records for upcoming/overdue dates
        and create notifications. Called daily by scheduler.
        
        Returns:
            Dictionary with summary of notifications created
        """
        try:
            today = date.today()
            today_str = today.isoformat()
            notifications_created = []
            
            # Get all vaccination records with next_due_date
            records = self.vaccine_repo.get_records_with_due_dates()
            
            for record in records:
                next_due_str = record.get("next_due_date")
                if not next_due_str:
                    continue
                    
                try:
                    next_due = datetime.strptime(next_due_str[:10], "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    continue
                
                days_remaining = (next_due - today).days
                pet_id = record.get("pet_id")
                vaccine_name = record.get("vaccine_name", "Unknown")
                record_id = record.get("id")
                
                # Determine notification type
                notification_type = None
                if days_remaining == 30:
                    notification_type = "UPCOMING_VACCINE"
                elif days_remaining == 7:
                    notification_type = "DUE_SOON"
                elif days_remaining == 0:
                    notification_type = "DUE_TODAY"
                elif days_remaining < 0 and days_remaining % 15 == 0:
                    notification_type = "OVERDUE"
                
                if not notification_type:
                    continue
                
                # Check if notification already sent today
                if self.vaccine_repo.check_notification_log_exists(record_id, notification_type, today_str):
                    continue  # Skip duplicate
                
                # Build notification message
                if notification_type == "UPCOMING_VACCINE":
                    title = f"Upcoming Vaccine: {vaccine_name}"
                    message = f"{vaccine_name} vaccine for {record.get('pets', {}).get('name', 'your pet')} is due in 30 days (due: {next_due_str[:10]})."
                elif notification_type == "DUE_SOON":
                    title = f"Vaccine Due Soon: {vaccine_name}"
                    message = f"{vaccine_name} vaccine is due next week (due: {next_due_str[:10]}). Schedule an appointment!"
                elif notification_type == "DUE_TODAY":
                    title = f"Vaccine Due Today: {vaccine_name}"
                    message = f"{vaccine_name} vaccination is due today! Please visit your vet."
                elif notification_type == "OVERDUE":
                    overdue_days = abs(days_remaining)
                    title = f"Overdue: {vaccine_name}"
                    message = f"{vaccine_name} vaccine is overdue by {overdue_days} days (was due: {next_due_str[:10]}). Please schedule ASAP!"
                else:
                    continue
                
                # Get user_id from pet owner
                user_id = record.get("pets", {}).get("user_id")
                if not user_id:
                    continue
                
                # Create notification
                notif_result = self.user_repo.insert_notification({
                    "user_id": user_id,
                    "user_role": "owner",
                    "type": notification_type,
                    "title": title,
                    "message": message,
                    "entity_type": "vaccination",
                    "entity_id": record_id,
                    "metadata": {
                        "pet_id": pet_id,
                        "vaccine_name": vaccine_name,
                        "next_due_date": next_due_str[:10],
                        "days_remaining": days_remaining
                    }
                })
                
                # Log the notification
                self.vaccine_repo.log_notification_sent({
                    "vaccination_id": record_id,
                    "notification_type": notification_type,
                    "sent_date": today_str
                })
                
                if notif_result:
                    notifications_created.append(notif_result)
            
            return {
                "success": True,
                "notifications_created": len(notifications_created),
                "date": today_str
            }
            
        except Exception as e:
            logger.error(f"Error checking reminders: {e}")
            return {"success": False, "error": str(e)}
