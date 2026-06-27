"""
Authentication Service for Pet AI Backend
Handles user signup, login, and profile management
"""

import hashlib
import os
from typing import Dict, Optional
from chatbot.supabase_config import supabase, SupabaseStorage
from chatbot.rbac import AuthorizationService, Permission
import secrets
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta


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
        phone: str,
    ) -> Dict:
        """
        Signup new pet owner
        
        Args:
            email: Owner email
            password: Plain text password
            first_name: First name
            last_name: Last name
            phone: Phone number (mandatory)
        
        Returns:
            Dictionary with success status and user data
        """
        try:
            # Validate input
            if not email or not password or not first_name or not last_name or not phone:
                return {
                    "success": False,
                    "error": "Email, password, first name, last name, and phone number are required"
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
        license_document_url: Optional[str] = None,
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
                "license_document_url": license_document_url,
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
            
            # Get verification status for clinic users and avatar url
            verification_status = None
            avatar_url = None
            if role == "clinic":
                clinic_response = supabase.table("clinics").select("is_verified, clinic_logo_url").eq("user_id", user["id"]).execute()
                if clinic_response.data:
                    is_verified = clinic_response.data[0].get("is_verified", False)
                    verification_status = "approved" if is_verified else "pending"
                    avatar_url = clinic_response.data[0].get("clinic_logo_url")
            elif role == "owner":
                owner_response = supabase.table("pet_owners").select("profile_image_url").eq("user_id", user["id"]).execute()
                if owner_response.data:
                    avatar_url = owner_response.data[0].get("profile_image_url")

            return {
                "success": True,
                "user_id": user["id"],
                "email": user["email"],
                "role": role,
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name"),
                "permissions": [p.value for p in permissions],
                "verification_status": verification_status,
                "avatar_url": avatar_url,
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

    @staticmethod
    def create_password_reset(email: str) -> Dict:
        """
        Generate a password reset token for the given email, store a hashed token and expiry,
        and attempt to send a reset link via SMTP if configured. Returns success (always true
        for security reasons) and optionally the reset link when email delivery is not configured.
        """
        try:
            if not email:
                return {"success": False, "error": "Email is required"}

            # Find user by email
            resp = supabase.table("auth_users").select("id,email").eq("email", email).execute()
            if not resp.data:
                # Don't reveal whether email exists
                return {"success": True, "message": "If that email is registered, a reset link has been sent."}

            user = resp.data[0]
            user_id = user.get("id")

            # Generate token and store hashed version
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            now = datetime.utcnow()
            expires_at = (now + timedelta(hours=1)).isoformat()

            supabase.table("password_reset_tokens").insert({
                "user_id": user_id,
                "token_hash": token_hash,
                "created_at": now.isoformat(),
                "expires_at": expires_at,
                "used": False,
            }).execute()

            # Build reset link
            frontend_base = os.getenv("FRONTEND_URL", "http://localhost:3000")
            reset_link = f"{frontend_base}/auth/reset?token={token}"

            # Try to send email using SMTP if configured
            smtp_host = os.getenv("SMTP_HOST")
            smtp_port = int(os.getenv("SMTP_PORT", "0") or 0)
            smtp_user = os.getenv("SMTP_USER")
            smtp_pass = os.getenv("SMTP_PASS")
            support_from = os.getenv("SUPPORT_FROM", "no-reply@petai.local")

            email_sent = False
            if smtp_host and smtp_port and smtp_user and smtp_pass:
                try:
                    msg = MIMEText(f"You requested a password reset. Click the link to reset your password:\n\n{reset_link}\n\nIf you didn't request this, ignore this email.")
                    msg["Subject"] = "Reset your Pet AI password"
                    msg["From"] = support_from
                    msg["To"] = email

                    server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.sendmail(support_from, [email], msg.as_string())
                    server.quit()
                    email_sent = True
                except Exception as e:
                    # Log and continue; do not fail the request
                    try:
                        import logging
                        logging.getLogger(__name__).warning(f"SMTP send failed: {str(e)}")
                    except Exception:
                        pass

            # For non-configured SMTP, return the reset_link in response for dev/testing
            result = {"success": True, "message": "If that email is registered, a reset link has been sent."}
            if not email_sent:
                result["reset_link"] = reset_link

            return result

        except Exception as e:
            return {"success": False, "error": f"Error creating reset token: {str(e)}"}

    @staticmethod
    def reset_password(token: str, new_password: str) -> Dict:
        """
        Validate a password reset token and set the new password for the associated user.
        Token is expected to be the raw token string (not hashed).
        """
        try:
            if not token or not new_password:
                return {"success": False, "error": "Token and new password are required"}

            token_hash = hashlib.sha256(token.encode()).hexdigest()
            now = datetime.utcnow().isoformat()

            # Look up token
            resp = supabase.table("password_reset_tokens").select("id,user_id,expires_at,used").eq("token_hash", token_hash).execute()
            if not resp.data:
                return {"success": False, "error": "Invalid or expired token"}

            row = resp.data[0]
            if row.get("used"):
                return {"success": False, "error": "Token already used"}

            expires_at = row.get("expires_at")
            if expires_at and expires_at < now:
                return {"success": False, "error": "Token expired"}

            user_id = row.get("user_id")

            # Update user's password_hash
            new_hash = AuthService.hash_password(new_password)
            supabase.table("auth_users").update({"password_hash": new_hash}).eq("id", user_id).execute()

            # Mark token as used
            supabase.table("password_reset_tokens").update({"used": True}).eq("id", row.get("id")).execute()

            return {"success": True, "message": "Password updated successfully"}

        except Exception as e:
            return {"success": False, "error": f"Reset failed: {str(e)}"}

    @staticmethod
    def update_user_profile(
        user_id: str,
        full_name: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        state: Optional[str] = None,
        zip_code: Optional[str] = None,
        country: Optional[str] = None,
        bio: Optional[str] = None,
        emergency_contact_name: Optional[str] = None,
        emergency_contact_phone: Optional[str] = None,
        profile_image_url: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> Dict:
        """Update pet owner user profile"""
        try:
            # Check if user exists
            user_response = supabase.table("auth_users").select("*").eq("id", user_id).execute()
            if not user_response.data:
                return {"success": False, "error": "User not found"}
            
            user = user_response.data[0]
            role = user.get("role")
            
            if role != "owner":
                return {"success": False, "error": "Only pet owner profiles can be updated through this endpoint"}
            
            # Prepare updates for pet_owners table
            owner_updates = {}
            if full_name is not None:
                owner_updates["full_name"] = full_name
            if phone is not None:
                owner_updates["phone"] = phone
            if address is not None:
                owner_updates["address"] = address
            if state is not None:
                owner_updates["state"] = state
            if zip_code is not None:
                owner_updates["zip_code"] = zip_code
            if country is not None:
                owner_updates["country"] = country
            if bio is not None:
                owner_updates["bio"] = bio
            if emergency_contact_name is not None:
                owner_updates["emergency_contact_name"] = emergency_contact_name
            if emergency_contact_phone is not None:
                owner_updates["emergency_contact_phone"] = emergency_contact_phone
            if profile_image_url is not None:
                owner_updates["profile_image_url"] = profile_image_url
            if latitude is not None:
                owner_updates["latitude"] = latitude
            if longitude is not None:
                owner_updates["longitude"] = longitude

            if owner_updates:
                supabase.table("pet_owners").update(owner_updates).eq("user_id", user_id).execute()
                
            # Also update auth_users table first_name and last_name if full_name is provided
            if full_name:
                name_parts = full_name.strip().split(" ", 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ""
                
                auth_updates = {"first_name": first_name, "last_name": last_name}
                if phone is not None:
                    auth_updates["phone"] = phone
                    
                supabase.table("auth_users").update(auth_updates).eq("id", user_id).execute()

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

    @staticmethod
    def update_pet(
        pet_id: str,
        updates: Dict,
    ) -> Dict:
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
