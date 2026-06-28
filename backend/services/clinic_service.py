from typing import Dict, List, Optional
from datetime import datetime
import logging
from chatbot.supabase_config import supabase, SupabaseStorage

logger = logging.getLogger(__name__)

REJECTION_MARKER = "__ADMIN_REJECTION__::"

class ClinicService:
    """Service for managing clinic profiles, approvals, and public listings"""

    @staticmethod
    def get_clinic_profile(user_id: str) -> Dict:
        """Get clinic profile by owner's user_id"""
        try:
            response = supabase.table("clinics").select("*").eq("user_id", user_id).execute()
            if not response.data:
                return {"success": False, "error": "Clinic not found"}

            clinic = ClinicService._parse_clinic_status(response.data[0])
            clinic["gallery_urls"] = SupabaseStorage.list_clinic_images(user_id)
            
            if not clinic.get("clinic_logo_url") and clinic["gallery_urls"]:
                clinic["clinic_logo_url"] = clinic["gallery_urls"][0]

            return {"success": True, "clinic": clinic}
        except Exception as e:
            return {"success": False, "error": f"Error fetching clinic: {str(e)}"}

    @staticmethod
    def update_clinic_profile(user_id: str, updates: Dict) -> Dict:
        """Update clinic profile details"""
        try:
            if updates:
                supabase.table("clinics").update(updates).eq("user_id", user_id).execute()

            # Refresh and return
            return ClinicService.get_clinic_profile(user_id)
        except Exception as e:
            return {"success": False, "error": f"Error updating clinic: {str(e)}"}

    @staticmethod
    def get_public_clinics() -> Dict:
        """List verified clinics for the public frontend"""
        try:
            resp = supabase.table("clinics").select("*").eq("is_verified", True).order("created_at", desc=True).execute()
            clinics = []
            for clinic_data in (resp.data or []):
                parsed = ClinicService._parse_clinic_status(clinic_data)
                uid = parsed.get("user_id")
                parsed["gallery_urls"] = SupabaseStorage.list_clinic_images(uid) if uid else []
                if not parsed.get("clinic_logo_url") and parsed["gallery_urls"]:
                    parsed["clinic_logo_url"] = parsed["gallery_urls"][0]
                clinics.append(parsed)

            return {"success": True, "clinics": clinics, "count": len(clinics)}
        except Exception as e:
            return {"success": False, "error": f"Error fetching public clinics: {str(e)}"}

    @staticmethod
    def get_clinic_by_id(clinic_id: str) -> Dict:
        """Get public details of a clinic by its clinic ID"""
        try:
            resp = supabase.table("clinics").select("*").eq("id", clinic_id).execute()
            if not resp.data:
                return {"success": False, "error": "Clinic not found"}

            clinic = ClinicService._parse_clinic_status(resp.data[0])
            uid = clinic.get("user_id")
            clinic["gallery_urls"] = SupabaseStorage.list_clinic_images(uid) if uid else []
            if not clinic.get("clinic_logo_url") and clinic["gallery_urls"]:
                clinic["clinic_logo_url"] = clinic["gallery_urls"][0]

            return {"success": True, "clinic": clinic}
        except Exception as e:
            return {"success": False, "error": f"Error fetching clinic: {str(e)}"}

    @staticmethod
    def get_pending_clinics() -> Dict:
        """List all pending clinics (unverified and not rejected)"""
        try:
            resp = supabase.table("clinics").select("*").eq("is_verified", False).execute()
            pending = []
            for clinic in (resp.data or []):
                parsed = ClinicService._parse_clinic_status(clinic)
                if parsed["verification_status"] == "pending":
                    pending.append(parsed)
            return {"success": True, "clinics": pending, "count": len(pending)}
        except Exception as e:
            return {"success": False, "error": f"Error fetching pending clinics: {str(e)}"}

    @staticmethod
    def approve_clinic(clinic_id: str) -> Dict:
        """Approve clinic (admin action)"""
        try:
            clinic_resp = supabase.table("clinics").select("id", "user_id", "clinic_name").eq("id", clinic_id).execute()
            if not clinic_resp.data:
                return {"success": False, "error": "Clinic not found"}

            clinic = clinic_resp.data[0]
            user_id = clinic.get("user_id")
            clinic_name = clinic.get("clinic_name") or "Your clinic"
            
            # Fetch current description and strip rejection marker if any
            current = supabase.table("clinics").select("description").eq("id", clinic_id).execute()
            current_desc = current.data[0].get("description") if current.data else ""
            clean_desc = ClinicService._strip_rejection_marker(current_desc)

            # Update clinic to verified
            supabase.table("clinics").update({"is_verified": True, "description": clean_desc}).eq("id", clinic_id).execute()

            # Enable corresponding profile (profile is already active via auth, no-op)
            if user_id:
                # Create notification
                ClinicService._create_notification(
                    user_id,
                    "clinic_approval",
                    "Clinic Approved ✅",
                    f"Congratulations! {clinic_name} has been approved by the admin. You can now access all features.",
                    "clinic",
                    "clinic",
                    clinic_id
                )

            return {"success": True, "clinic_id": clinic_id, "message": "Clinic approved successfully!"}
        except Exception as e:
            return {"success": False, "error": f"Error approving clinic: {str(e)}"}

    @staticmethod
    def reject_clinic(clinic_id: str, reason: Optional[str] = None) -> Dict:
        """Reject clinic (admin action)"""
        try:
            clinic_resp = supabase.table("clinics").select("id", "user_id", "clinic_name").eq("id", clinic_id).execute()
            if not clinic_resp.data:
                return {"success": False, "error": "Clinic not found"}

            clinic = clinic_resp.data[0]
            user_id = clinic.get("user_id")
            clinic_name = clinic.get("clinic_name") or "Your clinic"

            # Fetch current description to append rejection marker
            current = supabase.table("clinics").select("description").eq("id", clinic_id).execute()
            current_desc = ""
            if current.data:
                current_desc = ClinicService._strip_rejection_marker(current.data[0].get("description") or "")

            timestamp = datetime.utcnow().isoformat()
            marker = REJECTION_MARKER
            if reason:
                safe_reason = str(reason).replace("::", "--")
                marker_payload = f"reason={safe_reason}::time={timestamp}"
                new_desc = current_desc + ("\n\n" if current_desc else "") + marker + marker_payload
            else:
                marker_payload = f"time={timestamp}"
                new_desc = current_desc + ("\n\n" if current_desc else "") + marker + marker_payload

            # Update clinic: set is_verified false and append description marker
            supabase.table("clinics").update({"is_verified": False, "description": new_desc}).eq("id", clinic_id).execute()

            # Keep associated auth profile active so they can log in, view status, and edit/resubmit profile
            if user_id:
                # Create notification
                rejection_message = f"Your registration for {clinic_name} was rejected by the admin."
                if reason:
                    rejection_message += f" Reason: {reason}"
                else:
                    rejection_message += " Please check your documents and resubmit."
                
                ClinicService._create_notification(
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
    @staticmethod
    def _parse_clinic_status(clinic: dict) -> dict:
        clinic_copy = dict(clinic)
        desc = clinic_copy.get("description") or ""
        is_rejected = False
        rejection_reason = None
        rejected_at = None

        if REJECTION_MARKER in desc:
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

    @staticmethod
    def _strip_rejection_marker(description: Optional[str]) -> str:
        if not description:
            return ""
        if REJECTION_MARKER not in description:
            return description.strip()
        return description.split(REJECTION_MARKER, 1)[0].rstrip()

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
