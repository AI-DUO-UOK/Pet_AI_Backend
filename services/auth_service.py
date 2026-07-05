from typing import Dict, Optional
from interfaces.user_repository import IUserRepository
from interfaces.clinic_repository import IClinicRepository

class AuthService:
    """Authentication and Profile Service"""

    def __init__(self, user_repo: IUserRepository, clinic_repo: IClinicRepository):
        self.user_repo = user_repo
        self.clinic_repo = clinic_repo

    def register_pet_owner(
        self,
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
            self.user_repo.update_user(user_id, {"phone_number": phone, "role": "owner"})

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

            existing = self.user_repo.get_owner_profile(user_id)
            if existing:
                profile = self.user_repo.update_owner_profile(user_id, owner_data)
            else:
                profile = self.user_repo.insert_owner_profile(owner_data)
            
            return {
                "success": True,
                "user_id": user_id,
                "role": "owner",
                "profile": profile or {},
                "message": "Pet owner profile registered successfully!"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Registration failed: {str(e)}"
            }

    def register_clinic(
        self,
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
            self.user_repo.update_user(user_id, {"phone_number": phone, "role": "clinic"})

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

            existing = self.clinic_repo.get_by_user_id(user_id)
            if existing:
                # Preserve existing verification status
                clinic_data["is_verified"] = existing.get("is_verified", False)
                profile = self.clinic_repo.update_clinic(existing["id"], clinic_data)
            else:
                clinic_data["is_verified"] = False  # Starts as pending
                profile = self.clinic_repo.insert_clinic(clinic_data)
            
            return {
                "success": True,
                "user_id": user_id,
                "role": "clinic",
                "profile": profile or {},
                "message": "Clinic profile registered successfully! Pending admin approval."
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Clinic registration failed: {str(e)}"
            }

    def get_user_profile(self, user_id: str) -> Dict:
        """Get user profile based on their role in the users table"""
        try:
            # Get profile
            profile = self.user_repo.get_by_id(user_id)
            if not profile:
                return {"success": False, "error": "User profile not found"}

            role = profile.get("role")

            # Get detail profile based on role
            if role == "owner":
                detail_profile = self.user_repo.get_owner_profile(user_id)
            elif role == "clinic":
                detail_profile = self.clinic_repo.get_by_user_id(user_id)
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

            if not detail_profile:
                return {"success": False, "error": f"{role.title()} details not found"}

            return {
                "success": True,
                "user_id": user_id,
                "role": role,
                "profile": detail_profile
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error fetching profile: {str(e)}"
            }

    def update_user_profile(self, user_id: str, updates: Dict) -> Dict:
        """Update pet owner user profile"""
        try:
            # Check role
            profile = self.user_repo.get_by_id(user_id)
            if not profile or profile.get("role") != "owner":
                return {"success": False, "error": "Only pet owner profiles can be updated here"}

            # Update pet_owners
            if updates:
                self.user_repo.update_owner_profile(user_id, updates)
                
                # Also update the users table to keep them in sync
                user_updates = {}
                if "full_name" in updates:
                    user_updates["full_name"] = updates["full_name"]
                if "phone" in updates:
                    user_updates["phone_number"] = updates["phone"]
                if "profile_image_url" in updates:
                    user_updates["avatar_url"] = updates["profile_image_url"]
                
                if user_updates:
                    self.user_repo.update_user(user_id, user_updates)
                
            # Retrieve updated profile
            refreshed = self.user_repo.get_owner_profile(user_id)
            
            return {
                "success": True,
                "profile": refreshed or {}
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error updating profile: {str(e)}"
            }
