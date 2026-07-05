from typing import Dict, List, Optional
from datetime import datetime
import logging
from interfaces.clinic_repository import IClinicRepository
from interfaces.user_repository import IUserRepository
from interfaces.cache_service import ICacheService
from core.supabase_config import SupabaseStorage

logger = logging.getLogger(__name__)

REJECTION_MARKER = "__ADMIN_REJECTION__::"

class ClinicService:
    """Service for managing clinic profiles, approvals, and public listings"""

    def __init__(self, clinic_repo: IClinicRepository, user_repo: IUserRepository, cache_service: ICacheService):
        self.clinic_repo = clinic_repo
        self.user_repo = user_repo
        self.cache_service = cache_service

    def get_clinic_profile(self, user_id: str) -> Dict:
        """Get clinic profile by owner's user_id"""
        try:
            clinic_data = self.clinic_repo.get_by_user_id(user_id)
            if not clinic_data:
                return {"success": False, "error": "Clinic not found"}

            clinic = self._parse_clinic_status(clinic_data)
            clinic["gallery_urls"] = SupabaseStorage.list_clinic_images(user_id)
            
            if not clinic.get("clinic_logo_url") and clinic["gallery_urls"]:
                clinic["clinic_logo_url"] = clinic["gallery_urls"][0]
                
            return {"success": True, "clinic": clinic}
        except Exception as e:
            return {"success": False, "error": f"Error fetching clinic profile: {str(e)}"}

    def get_clinic_by_id(self, clinic_id: str) -> Dict:
        """Get clinic details by clinic ID"""
        try:
            clinic_data = self.clinic_repo.get_by_id(clinic_id)
            if not clinic_data:
                return {"success": False, "error": "Clinic not found"}

            clinic = self._parse_clinic_status(clinic_data)
            user_id = clinic.get("user_id")
            if user_id:
                clinic["gallery_urls"] = SupabaseStorage.list_clinic_images(user_id)
                if not clinic.get("clinic_logo_url") and clinic["gallery_urls"]:
                    clinic["clinic_logo_url"] = clinic["gallery_urls"][0]
            return {"success": True, "clinic": clinic}
        except Exception as e:
            return {"success": False, "error": f"Error fetching clinic: {str(e)}"}

    def get_pending_clinics(self) -> Dict:
        """List all pending clinics (unverified and not rejected)"""
        try:
            clinics_data = self.clinic_repo.get_all_clinics()
            parsed = [self._parse_clinic_status(c) for c in clinics_data]
            pending = [c for c in parsed if c.get("verification_status") == "pending"]
            return {"success": True, "clinics": pending}
        except Exception as e:
            return {"success": False, "error": f"Error fetching pending clinics: {str(e)}"}

    def get_public_clinics(self) -> Dict:
        """Get all verified and active clinics for public search (with Redis/In-memory caching)"""
        try:
            cache_key = "clinics:public"
            cached_clinics = self.cache_service.get(cache_key)
            if cached_clinics is not None:
                logger.info("Cache hit: public clinics list")
                return {"success": True, "clinics": cached_clinics, "count": len(cached_clinics)}

            clinics_data = self.clinic_repo.get_public_clinics()
            clinics = [self._parse_clinic_status(c) for c in clinics_data]
            
            # Cache the list for 1 hour
            self.cache_service.set(cache_key, clinics, expire_seconds=3600)
            
            return {"success": True, "clinics": clinics, "count": len(clinics)}
        except Exception as e:
            return {"success": False, "error": f"Error fetching clinics: {str(e)}"}

    def update_clinic_profile(self, user_id: str, updates: Dict) -> Dict:
        """Update clinic profile details (and invalidate public clinic cache)"""
        try:
            clinic = self.clinic_repo.get_by_user_id(user_id)
            if not clinic:
                return {"success": False, "error": "Clinic profile not found"}

            clinic_id = clinic["id"]
            
            # Clean description of any rejection marker if updates contains description
            if "description" in updates:
                updates["description"] = self._strip_rejection_marker(updates["description"])

            # If clinic is updating, clear rejection details
            updates["rejection_reason"] = None
            updates["rejected_at"] = None
            if REJECTION_MARKER in (clinic.get("description") or ""):
                updates["description"] = self._strip_rejection_marker(clinic.get("description"))

            updated_profile = self.clinic_repo.update_clinic(clinic_id, updates)
            if not updated_profile:
                return {"success": False, "error": "Failed to update clinic profile"}

            # Cache Invalidation: Clear public clinics cache
            self.cache_service.delete("clinics:public")

            return {
                "success": True,
                "clinic": self._parse_clinic_status(updated_profile),
                "message": "Clinic profile updated successfully!"
            }
        except Exception as e:
            return {"success": False, "error": f"Error updating clinic: {str(e)}"}

    def approve_clinic(self, clinic_id: str) -> Dict:
        """Approve/Verify a clinic registration (only admin)"""
        try:
            clinic = self.clinic_repo.get_by_id(clinic_id)
            if not clinic:
                return {"success": False, "error": "Clinic not found"}

            user_id = clinic.get("user_id")
            clinic_name = clinic.get("clinic_name", "your clinic")

            # Strip rejection marker from description on approval
            clean_desc = self._strip_rejection_marker(clinic.get("description"))
            
            updates = {
                "is_verified": True, 
                "description": clean_desc,
                "rejection_reason": None,
                "rejected_at": None
            }
            
            updated_profile = self.clinic_repo.update_clinic(clinic_id, updates)
            if not updated_profile:
                return {"success": False, "error": "Failed to verify clinic"}

            # Cache Invalidation: Clear public clinics cache
            self.cache_service.delete("clinics:public")

            # Create notification
            if user_id:
                self._create_notification(
                    user_id,
                    "clinic_approval",
                    "Clinic Verification Approved 🎉",
                    f"Congratulations! Your registration for {clinic_name} has been verified and approved.",
                    "clinic",
                    "clinic",
                    clinic_id
                )

            return {
                "success": True,
                "clinic_id": clinic_id,
                "message": "Clinic verified and approved successfully!"
            }
        except Exception as e:
            return {"success": False, "error": f"Error approving clinic: {str(e)}"}

    def reject_clinic(self, clinic_id: str, reason: Optional[str] = None) -> Dict:
        """Reject a clinic registration (only admin)"""
        try:
            clinic = self.clinic_repo.get_by_id(clinic_id)
            if not clinic:
                return {"success": False, "error": "Clinic not found"}

            user_id = clinic.get("user_id")
            clinic_name = clinic.get("clinic_name", "your clinic")
            
            timestamp = datetime.utcnow().isoformat()
            
            # Form updates containing BOTH structured columns and legacy description marker
            current_desc = self._strip_rejection_marker(clinic.get("description") or "")
            
            if reason:
                safe_reason = str(reason).replace("::", "--")
                marker_payload = f"reason={safe_reason}::time={timestamp}"
                new_desc = current_desc + ("\n\n" if current_desc else "") + REJECTION_MARKER + marker_payload
            else:
                marker_payload = f"time={timestamp}"
                new_desc = current_desc + ("\n\n" if current_desc else "") + REJECTION_MARKER + marker_payload

            updates = {
                "is_verified": False,
                "rejection_reason": reason or "Please check your documents and resubmit.",
                "rejected_at": timestamp,
                "description": new_desc
            }

            self.clinic_repo.reject_clinic(clinic_id, updates)

            # Cache Invalidation: Clear public clinics cache
            self.cache_service.delete("clinics:public")

            # Keep associated auth profile active so they can log in, view status, and edit/resubmit profile
            if user_id:
                # Create notification
                rejection_message = f"Your registration for {clinic_name} was rejected by the admin."
                if reason:
                    rejection_message += f" Reason: {reason}"
                else:
                    rejection_message += " Please check your documents and resubmit."
                
                self._create_notification(
                    user_id,
                    "clinic_rejection",
                    "Clinic Verification Rejected ❌",
                    rejection_message,
                    "clinic",
                    "clinic",
                    clinic_id
                )

            return {
                "success": True,
                "clinic_id": clinic_id,
                "message": "Clinic rejected successfully",
                "reason": reason,
                "rejected_at": timestamp
            }
        except Exception as e:
            return {"success": False, "error": f"Error rejecting clinic: {str(e)}"}

    # Private helper methods
    def _parse_clinic_status(self, clinic: dict) -> dict:
        clinic_copy = dict(clinic)
        
        # 1. Try structured database columns first
        rejection_reason = clinic.get("rejection_reason")
        rejected_at = clinic.get("rejected_at")
        is_rejected = bool(rejection_reason or rejected_at)
        
        # 2. Fallback to description string parsing if columns not set/populated
        desc = clinic.get("description") or ""
        if not is_rejected and REJECTION_MARKER in desc:
            try:
                marker_payload = desc.split(REJECTION_MARKER, 1)[1].split("::")
                kv = {}
                for part in marker_payload:
                    if "=" in part:
                        key, value = part.split("=", 1)
                        kv[key] = value
                rejection_reason = kv.get("reason")
                rejected_at = kv.get("time")
                is_rejected = True
            except Exception:
                is_rejected = False

        if clinic_copy.get("is_verified"):
            verification_status = "approved"
            is_rejected = False
            rejection_reason = None
            rejected_at = None
        elif is_rejected:
            verification_status = "rejected"
        else:
            verification_status = "pending"

        clinic_copy["is_rejected"] = is_rejected
        clinic_copy["rejection_reason"] = rejection_reason
        clinic_copy["rejected_at"] = rejected_at
        clinic_copy["verification_status"] = verification_status
        return clinic_copy

    def _strip_rejection_marker(self, description: Optional[str]) -> str:
        if not description:
            return ""
        if REJECTION_MARKER not in description:
            return description.strip()
        return description.split(REJECTION_MARKER, 1)[0].rstrip()

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

    def get_clinic_patients(self, user_id: str) -> Dict:
        """Get all appointments / patients for a clinic owner user"""
        try:
            clinic = self.clinic_repo.get_by_user_id(user_id)
            if not clinic:
                return {"success": False, "error": "Clinic profile not found"}
            
            clinic_id = clinic["id"]
            from repositories.appointment_repository import AppointmentRepository
            appts = AppointmentRepository.get_clinic_appointments(clinic_id)
            
            enriched = []
            for a in appts:
                item = dict(a)
                pet = a.get("pets") or {}
                owner = a.get("pet_owners") or {}
                item["pet_name"] = pet.get("name") or a.get("pet_id")
                item["pet_type"] = pet.get("type") or "Pet"
                item["breed"] = pet.get("breed") or ""
                item["owner_name"] = owner.get("full_name") or a.get("owner_id")
                enriched.append(item)
                
            return {"success": True, "appointments": enriched, "count": len(enriched)}
        except Exception as e:
            return {"success": False, "error": str(e)}
