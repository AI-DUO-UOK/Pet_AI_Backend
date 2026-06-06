"""
Authentication Service for Pet AI Backend
Handles user signup, login, and profile management
"""

import hashlib
import os
from typing import Dict, Optional
from chatbot.supabase_config import supabase, SupabaseStorage
from chatbot.rbac import AuthorizationService, Permission


class AuthService:
    """Authentication service for users and clinics"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return hashlib.sha256(password.encode()).hexdigest() == password_hash

    @staticmethod
    def signup_pet_owner(
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        phone: str = None,
    ) -> Dict:
        """
        Signup new pet owner
        
        Args:
            email: Owner email
            password: Plain text password
            first_name: First name
            last_name: Last name
            phone: Phone number (optional)
        
        Returns:
            Dictionary with success status and user data
        """
        try:
            # Validate input
            if not email or not password or not first_name or not last_name:
                return {
                    "success": False,
                    "error": "Email, password, first name, and last name are required"
                }

            # Check if email already exists
            existing = supabase.table("auth_users").select("id").eq("email", email).execute()
            if existing.data:
                return {
                    "success": False,
                    "error": "Email already registered"
                }

            # 1. Create auth user
            password_hash = AuthService.hash_password(password)

            user_data = {
                "email": email,
                "password_hash": password_hash,
                "first_name": first_name,
                "last_name": last_name,
                "phone": phone,
                "role": "owner",
            }

            response = supabase.table("auth_users").insert(user_data).execute()
            user = response.data[0]
            user_id = user["id"]

            # 2. Create pet owner profile
            owner_data = {
                "user_id": user_id,
                "full_name": f"{first_name} {last_name}",
                "email": email,
                "phone": phone,
            }

            supabase.table("pet_owners").insert(owner_data).execute()

            return {
                "success": True,
                "user_id": user_id,
                "email": email,
                "role": "owner",
                "message": "Pet owner signup successful!"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Signup failed: {str(e)}"
            }

    @staticmethod
    def signup_clinic(
        email: str,
        password: str,
        clinic_name: str,
        phone: str,
        address: str,
        city: str = None,
        state: str = None,
        zip_code: str = None,
        country: str = None,
        website: str = None,
        opening_hours: str = None,
        description: str = None,
        clinic_logo_url: Optional[str] = None,
    ) -> Dict:
        """
        Signup new clinic/veterinary
        
        Args:
            email: Clinic email
            password: Plain text password
            clinic_name: Name of clinic
            phone: Clinic phone number
            address: Full address
            city: City (optional)
            state: State (optional)
            zip_code: Zip code (optional)
            country: Country (optional)
        
        Returns:
            Dictionary with success status and clinic data
        """
        try:
            # Validate input
            if not email or not password or not clinic_name or not phone or not address:
                return {
                    "success": False,
                    "error": "Email, password, clinic name, phone, and address are required"
                }

            # Check if email already exists
            existing = supabase.table("auth_users").select("id").eq("email", email).execute()
            if existing.data:
                return {
                    "success": False,
                    "error": "Email already registered"
                }

            # 1. Create auth user
            password_hash = AuthService.hash_password(password)

            user_data = {
                "email": email,
                "password_hash": password_hash,
                "first_name": clinic_name,
                "phone": phone,
                "role": "clinic",
            }

            response = supabase.table("auth_users").insert(user_data).execute()
            user = response.data[0]
            user_id = user["id"]

            # 2. Create clinic profile
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
                "is_verified": False,  # Starts as pending (not verified)
            }

            supabase.table("clinics").insert(clinic_data).execute()

            return {
                "success": True,
                "user_id": user_id,
                "clinic_name": clinic_name,
                "email": email,
                "role": "clinic",
                "message": "Clinic signup successful!"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Clinic signup failed: {str(e)}"
            }

    @staticmethod
    def login(email: str, password: str) -> Dict:
        """
        Login user
        
        Args:
            email: User email
            password: Plain text password
        
        Returns:
            Dictionary with success status and user data
        """
        try:
            if not email or not password:
                return {
                    "success": False,
                    "error": "Email and password are required"
                }

            # Admin via environment (quick local admin account)
            ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
            ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
            if ADMIN_EMAIL and ADMIN_PASSWORD and email.lower() == ADMIN_EMAIL.lower():
                # Check admin password
                if password == ADMIN_PASSWORD:
                    permissions = AuthorizationService.get_user_permissions("admin")
                    return {
                        "success": True,
                        "user_id": "admin",
                        "email": ADMIN_EMAIL,
                        "role": "admin",
                        "first_name": "Admin",
                        "last_name": None,
                        "permissions": [p.value for p in permissions],
                        "verification_status": None,
                        "message": "Admin login successful"
                    }
                else:
                    return {"success": False, "error": "Invalid email or password"}

            # Find user
            response = supabase.table("auth_users").select("*").eq("email", email).execute()

            if not response.data:
                return {
                    "success": False,
                    "error": "Invalid email or password"
                }

            user = response.data[0]
            password_hash = user.get("password_hash")

            # Verify password
            if not AuthService.verify_password(password, password_hash):
                return {
                    "success": False,
                    "error": "Invalid email or password"
                }

            # Check if active
            if not user.get("is_active"):
                return {
                    "success": False,
                    "error": "Account is inactive"
                }

            # Get user permissions based on role
            role = user["role"]
            permissions = AuthorizationService.get_user_permissions(role)
            
            # Get verification status for clinic users
            verification_status = None
            if role == "clinic":
                clinic_response = supabase.table("clinics").select("is_verified").eq("user_id", user["id"]).execute()
                if clinic_response.data:
                    is_verified = clinic_response.data[0].get("is_verified", False)
                    verification_status = "approved" if is_verified else "pending"

            return {
                "success": True,
                "user_id": user["id"],
                "email": user["email"],
                "role": role,
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name"),
                "permissions": [p.value for p in permissions],
                "verification_status": verification_status,
                "message": "Login successful!"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Login failed: {str(e)}"
            }

    @staticmethod
    def get_user_profile(user_id: str) -> Dict:
        """
        Get user profile based on role
        
        Args:
            user_id: User ID
        
        Returns:
            User profile data
        """
        try:
            # Get user
            user_response = supabase.table("auth_users").select("*").eq("id", user_id).execute()

            if not user_response.data:
                return {"success": False, "error": "User not found"}

            user = user_response.data[0]
            role = user.get("role")

            # Get profile based on role
            if role == "owner":
                profile_response = supabase.table("pet_owners").select("*").eq("user_id", user_id).execute()
            elif role == "clinic":
                profile_response = supabase.table("clinics").select("*").eq("user_id", user_id).execute()
            else:
                return {"success": False, "error": "Unknown user role"}

            if not profile_response.data:
                return {"success": False, "error": "Profile not found"}

            profile = profile_response.data[0]

            return {
                "success": True,
                "user_id": user_id,
                "role": role,
                "profile": profile
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error fetching profile: {str(e)}"
            }


class PetService:
    """Service for managing pets"""

    @staticmethod
    def add_pet(
        user_id: str,
        name: str,
        pet_type: str,  # 'dog' or 'cat'
        breed: str,
        date_of_birth: str,  # Format: YYYY-MM-DD
        weight: float,
        weight_unit: str = "kg",
        gender: str = None,
        blood_type: str = None,
        allergies: str = None,
        medical_conditions: str = None,
        notes: str = None,
        profile_image_url: Optional[str] = None,
    ) -> Dict:
        """
        Add new pet
        
        Args:
            user_id: Owner user ID
            name: Pet name
            pet_type: 'dog' or 'cat'
            breed: Pet breed
            date_of_birth: Date of birth (YYYY-MM-DD)
            weight: Weight
            weight_unit: 'kg' or 'lbs'
            gender: 'Male' or 'Female'
            blood_type: Blood type
            allergies: Allergies (comma-separated)
            medical_conditions: Medical conditions
            notes: Additional notes
        
        Returns:
            Dictionary with success status and pet data
        """
        try:
            if not all([name, pet_type, breed, date_of_birth, weight]):
                return {
                    "success": False,
                    "error": "Name, type, breed, date of birth, and weight are required"
                }

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
                "pets": response.data,
                "count": len(response.data)
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error fetching pets: {str(e)}"
            }

    @staticmethod
    def upload_vaccine_record(
        pet_id: str,
        file_data: bytes,
        file_name: str,
        file_type: str,  # 'image' or 'pdf'
        uploaded_by: str,
        upload_date: str = None,  # Format: YYYY-MM-DD
    ) -> Dict:
        """
        Upload vaccine record file
        
        Args:
            pet_id: Pet ID
            file_data: File bytes
            file_name: Original file name
            file_type: 'image' or 'pdf'
            uploaded_by: User ID who uploaded
            upload_date: Date of upload (defaults to today)
        
        Returns:
            Dictionary with success status
        """
        try:
            from datetime import datetime

            if not upload_date:
                upload_date = datetime.now().strftime("%Y-%m-%d")

            # Create file path: pet_id/timestamp-filename
            import time
            file_path = f"vaccine-records/{pet_id}/{int(time.time())}-{file_name}"

            # Upload to storage
            SupabaseStorage.ensure_bucket("vaccine-records", public=False)
            supabase.storage.from_("vaccine-records").upload(
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
                "records": response.data,
                "count": len(response.data)
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error fetching vaccine records: {str(e)}"
            }
