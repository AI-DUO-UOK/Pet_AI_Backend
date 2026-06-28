from typing import Dict, Optional
import time
from chatbot.supabase_config import supabase, SupabaseStorage

class PetService:
    """Service for managing pets and their vaccine records"""

    @staticmethod
    def add_pet(
        user_id: str,
        name: str,
        pet_type: str,
        breed: str,
        date_of_birth: str,
        weight: float,
        weight_unit: str = "kg",
        gender: Optional[str] = None,
        blood_type: Optional[str] = None,
        allergies: Optional[str] = None,
        medical_conditions: Optional[str] = None,
        notes: Optional[str] = None,
        profile_image_url: Optional[str] = None,
    ) -> Dict:
        """Add new pet"""
        try:
            pet_data = {
                "user_id": user_id,
                "name": name,
                "type": pet_type,
                "breed": breed,
                "date_of_birth": date_of_birth,
                "weight": weight,
                "weight_unit": weight_unit,
                "gender": gender,
                "blood_type": blood_type,
                "allergies": allergies,
                "medical_conditions": medical_conditions,
                "notes": notes,
                "profile_image_url": profile_image_url,
            }

            response = supabase.table("pets").insert(pet_data).execute()
            if not response.data:
                return {"success": False, "error": "Failed to create pet"}

            pet = response.data[0]
            return {
                "success": True,
                "pet_id": pet["id"],
                "pet_name": pet["name"],
                "message": "Pet added successfully!"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error adding pet: {str(e)}"
            }

    @staticmethod
    def get_user_pets(user_id: str) -> Dict:
        """Get all pets for a user"""
        try:
            response = supabase.table("pets").select("*").eq("user_id", user_id).execute()
            return {
                "success": True,
                "pets": response.data or [],
                "count": len(response.data or [])
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error fetching pets: {str(e)}"
            }

    @staticmethod
    def update_pet(pet_id: str, updates: Dict) -> Dict:
        """Update pet details"""
        try:
            response = supabase.table("pets").update(updates).eq("id", pet_id).execute()
            if not response.data:
                return {
                    "success": False,
                    "error": "Pet not found or not updated"
                }
            return {
                "success": True,
                "pet": response.data[0],
                "message": "Pet updated successfully!"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error updating pet: {str(e)}"
            }

    @staticmethod
    def upload_vaccine_record(
        pet_id: str,
        file_data: bytes,
        file_name: str,
        file_type: str,
        uploaded_by: str,
        upload_date: Optional[str] = None,
    ) -> Dict:
        """Upload vaccine record file"""
        try:
            from datetime import datetime
            if not upload_date:
                upload_date = datetime.now().strftime("%Y-%m-%d")

            file_path = f"vaccine-records/{pet_id}/{int(time.time())}-{file_name}"

            # Upload to storage
            SupabaseStorage.ensure_bucket("vaccine-documents", public=False)
            supabase.storage.from_("vaccine-documents").upload(
                file=file_data,
                path=file_path,
                file_options={
                    "content-type": "application/pdf" if file_type == "pdf" else "image/jpeg",
                    "upsert": "false",
                },
            )

            # Save record to database
            record_data = {
                "pet_id": pet_id,
                "file_name": file_name,
                "file_url": file_path,
                "file_type": file_type,
                "file_size": len(file_data),
                "upload_date": upload_date,
                "uploaded_by": uploaded_by,
            }

            response = supabase.table("vaccine_records").insert(record_data).execute()
            if not response.data:
                return {"success": False, "error": "Failed to save vaccine record"}

            return {
                "success": True,
                "record_id": response.data[0]["id"],
                "file_url": file_path,
                "message": "Vaccine record uploaded successfully!"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error uploading vaccine record: {str(e)}"
            }

    @staticmethod
    def get_pet_vaccine_records(pet_id: str) -> Dict:
        """Get all vaccine records for a pet"""
        try:
            response = supabase.table("vaccine_records").select("*").eq("pet_id", pet_id).execute()
            return {
                "success": True,
                "records": response.data or [],
                "count": len(response.data or [])
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error fetching vaccine records: {str(e)}"
            }
