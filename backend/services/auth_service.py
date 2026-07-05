from typing import Dict, Optional
from chatbot.supabase_config import supabase

class AuthService:
    """Authentication and Profile Service"""

    @staticmethod
    def register_pet_owner(
        user_id: str,
        email: str,
        first_name: str,
        last_name: str,
        phone: str,
        address: Optional[str] = None,
        state: Optional[str] = None,
        zip_code: Optional[str] = None,
        country: Optional[str] = None,
        bio: Optional[str] = None,
    ) -> Dict:
        """Complete pet owner profile registration"""
        try:
            # 1. Update phone and role in users
            supabase.table("users").update({"phone_number": phone, "role": "owner"}).eq("id", user_id).execute()

            # 2. Insert or update pet_owners (idempotent registration)
            owner_data = {
                "user_id": user_id,
                "full_name": f"{first_name} {last_name}",
                "email": email,
                "phone": phone,
                "address": address,
                "state": state,
                "zip_code": zip_code,
                "country": country,
                "bio": bio,
            }

            existing = supabase.table("pet_owners").select("*").eq("user_id", user_id).execute()
            if existing.data:
                response = existing
            else:
                response = supabase.table("pet_owners").insert(owner_data).execute()
            
            return {
                "success": True,
                "user_id": user_id,
                "role": "owner",
                "profile": response.data[0] if response.data else {},
                "message": "Pet owner profile registered successfully!"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Registration failed: {str(e)}"
            }

    @staticmethod
    def register_clinic(
        user_id: str,
        email: str,
        clinic_name: str,
        phone: str,
        address: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        zip_code: Optional[str] = None,
        country: Optional[str] = None,
        website: Optional[str] = None,
        opening_hours: Optional[str] = None,
        description: Optional[str] = None,
        clinic_logo_url: Optional[str] = None,
        license_document_url: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> Dict:
        """Complete clinic profile registration"""
        try:
            # 1. Update phone and role in users
            supabase.table("users").update({"phone_number": phone, "role": "clinic"}).eq("id", user_id).execute()

            # 2. Insert or update clinics (idempotent registration)
            clinic_data = {
                "user_id": user_id,
                "clinic_name": clinic_name,
                "email": email,
                "phone": phone,
                "address": address,
                "city": city,
                "state": state,
                "zip_code": zip_code,
                "country": country,
                "website": website,
                "opening_hours": opening_hours,
                "description": description,
                "clinic_logo_url": clinic_logo_url,
                "license_document_url": license_document_url,
                "latitude": latitude,
                "longitude": longitude,
            }

            existing = supabase.table("clinics").select("*").eq("user_id", user_id).execute()
            if existing.data:
                # Preserve existing verification status
                clinic_data["is_verified"] = existing.data[0].get("is_verified", False)
                response = supabase.table("clinics").update(clinic_data).eq("user_id", user_id).execute()
            else:
                clinic_data["is_verified"] = False  # Starts as pending
                response = supabase.table("clinics").insert(clinic_data).execute()
            
            return {
                "success": True,
                "user_id": user_id,
                "role": "clinic",
                "profile": response.data[0] if response.data else {},
                "message": "Clinic profile registered successfully! Pending admin approval."
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Clinic registration failed: {str(e)}"
            }

    @staticmethod
    def get_user_profile(user_id: str) -> Dict:
        """Get user profile based on their role in the users table"""
        try:
            # Get profile
            profile_response = supabase.table("users").select("*").eq("id", user_id).execute()
            if not profile_response.data:
                return {"success": False, "error": "User profile not found"}

            profile = profile_response.data[0]
            role = profile.get("role")

            # Get detail profile based on role
            if role == "owner":
                detail_response = supabase.table("pet_owners").select("*").eq("user_id", user_id).execute()
            elif role == "clinic":
                detail_response = supabase.table("clinics").select("*").eq("user_id", user_id).execute()
            else:
                return {
                    "success": True,
                    "user_id": user_id,
                    "role": role,
                    "profile": {
                        "id": user_id,
                        "role": role,
                        "email": "admin@petai.com" if role == "admin" else ""
                    }
                }

            if not detail_response.data:
                return {"success": False, "error": f"{role.title()} details not found"}

            return {
                "success": True,
                "user_id": user_id,
                "role": role,
                "profile": detail_response.data[0]
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error fetching profile: {str(e)}"
            }

    @staticmethod
    def update_user_profile(user_id: str, updates: Dict) -> Dict:
        """Update pet owner user profile"""
        try:
            # Check role
            profile_resp = supabase.table("users").select("role").eq("id", user_id).execute()
            if not profile_resp.data or profile_resp.data[0].get("role") != "owner":
                return {"success": False, "error": "Only pet owner profiles can be updated here"}

            # Update pet_owners
            if updates:
                # Filter updates to only include columns that exist in pet_owners
                allowed_columns = {
                    "full_name", "email", "phone", "address", "state", "zip_code",
                    "country", "profile_image_url", "bio", "latitude", "longitude"
                }
                filtered_updates = {k: v for k, v in updates.items() if k in allowed_columns}
                
                if filtered_updates:
                    supabase.table("pet_owners").update(filtered_updates).eq("user_id", user_id).execute()
                
                # Also update the users table to keep them in sync
                user_updates = {}
                if "full_name" in updates:
                    user_updates["full_name"] = updates["full_name"]
                if "phone" in updates:
                    user_updates["phone_number"] = updates["phone"]
                if "profile_image_url" in updates:
                    user_updates["avatar_url"] = updates["profile_image_url"]
                
                if user_updates:
                    supabase.table("users").update(user_updates).eq("id", user_id).execute()
                
            # Retrieve updated profile
            refreshed = supabase.table("pet_owners").select("*").eq("user_id", user_id).execute()
            
            return {
                "success": True,
                "profile": refreshed.data[0] if refreshed.data else {}
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error updating profile: {str(e)}"
            }
