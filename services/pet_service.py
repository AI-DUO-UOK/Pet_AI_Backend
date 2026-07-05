from typing import Dict, Optional
import time
import logging
from repositories.pet_repository import PetRepository
from core.cache import CacheService
from core.supabase_config import SupabaseStorage

logger = logging.getLogger(__name__)

class PetService:
    """Service for managing pets and their vaccine records"""

    def __init__(self, pet_repo: PetRepository, cache_service: CacheService):
        self.pet_repo = pet_repo
        self.cache_service = cache_service

    def add_pet(
        self,
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

            pet = self.pet_repo.insert_pet(pet_data)
            if not pet:
                return {"success": False, "error": "Failed to create pet"}

            # Cache Invalidation: Clear owner pets list cache
            self.cache_service.delete(f"pets:owner:{user_id}")

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

    def get_user_pets(self, user_id: str) -> Dict:
        """Get all pets for a user (with Redis/In-memory caching)"""
        try:
            cache_key = f"pets:owner:{user_id}"
            cached_pets = self.cache_service.get(cache_key)
            if cached_pets is not None:
                logger.info(f"Cache hit: user pets for {user_id}")
                return {
                    "success": True,
                    "pets": cached_pets,
                    "count": len(cached_pets)
                }

            pets = self.pet_repo.get_user_pets(user_id)
            
            # Cache the list for 30 minutes
            self.cache_service.set(cache_key, pets, expire_seconds=1800)
            
            return {
                "success": True,
                "pets": pets,
                "count": len(pets)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error fetching pets: {str(e)}"
            }

    def update_pet(self, pet_id: str, updates: Dict) -> Dict:
        """Update pet details (and invalidate related caches)"""
        try:
            # Query existing user_id for cache invalidation
            pet_before = self.pet_repo.get_by_id(pet_id)
            
            pet = self.pet_repo.update_pet(pet_id, updates)
            if not pet:
                return {
                    "success": False,
                    "error": "Pet not found or not updated"
                }

            # Cache Invalidation
            if pet_before:
                user_id = pet_before.get("user_id")
                self.cache_service.delete(f"pets:owner:{user_id}")
            self.cache_service.delete(f"pets:detail:{pet_id}")

            return {
                "success": True,
                "pet": pet,
                "message": "Pet updated successfully!"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error updating pet: {str(e)}"
            }

    def upload_vaccine_record(
        self,
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
            
            from core.supabase_config import supabase
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

            record = self.pet_repo.insert_vaccine_record(record_data)
            if not record:
                return {"success": False, "error": "Failed to save vaccine record"}

            return {
                "success": True,
                "record_id": record["id"],
                "file_url": file_path,
                "message": "Vaccine record uploaded successfully!"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error uploading vaccine record: {str(e)}"
            }

    def get_pet_vaccine_records(self, pet_id: str) -> Dict:
        """Get all vaccine records for a pet"""
        try:
            records = self.pet_repo.get_vaccine_records(pet_id)
            return {
                "success": True,
                "records": records,
                "count": len(records)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error fetching vaccine records: {str(e)}"
            }
