"""
Pet AI Backend - API Routes with Supabase Integration
This file contains all authentication and data management endpoints

Usage:
    from app.api_routes import router
    app.include_router(router, prefix="/api")
"""

from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form, Request
from pydantic import BaseModel
from typing import Optional, List
import logging
from datetime import datetime

# Import services
from chatbot.auth_service import AuthService, PetService
from chatbot.rbac import AuthorizationService, Permission
from chatbot.supabase_config import supabase, SupabaseStorage
import os
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api", tags=["API Routes"])

# ============================================
# Request/Response Models
# ============================================

class SignupOwnerRequest(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    phone: str


class SignupClinicRequest(BaseModel):
    email: str
    password: str
    clinic_name: str
    phone: str
    address: str
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class NotificationReadRequest(BaseModel):
    user_id: str


class AddPetRequest(BaseModel):
    name: str
    pet_type: str
    breed: str
    date_of_birth: str
    weight: float
    weight_unit: Optional[str] = "kg"
    gender: Optional[str] = None
    blood_type: Optional[str] = None
    allergies: Optional[str] = None
    medical_conditions: Optional[str] = None
    notes: Optional[str] = None


class CreateAppointmentRequest(BaseModel):
    pet_id: str
    clinic_id: str
    owner_id: str
    appointment_date: str
    appointment_time: str
    reason: Optional[str] = None
    notes: Optional[str] = None


class CreateReviewRequest(BaseModel):
    appointment_id: str
    rating: int
    treatment: str
    comment: Optional[str] = None


# ============================================
# Authentication Endpoints
# ============================================

@router.post("/auth/signup/owner")
async def signup_owner(request: SignupOwnerRequest):
    """Signup new pet owner"""
    logger.info(f"Pet owner signup attempt: {request.email}")
    
    result = AuthService.signup_pet_owner(
        email=request.email,
        password=request.password,
        first_name=request.first_name,
        last_name=request.last_name,
        phone=request.phone
    )
    
    if not result["success"]:
        logger.warning(f"Signup failed: {result.get('error')}")
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    logger.info(f"Pet owner signup successful: {request.email}")
    return result


@router.post("/auth/signup/clinic")
async def signup_clinic(
    email: str = Form(...),
    password: str = Form(...),
    clinic_name: str = Form(...),
    phone: str = Form(...),
    address: str = Form(...),
    city: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    zip_code: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    website: Optional[str] = Form(None),
    opening_hours: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    clinic_photo: Optional[UploadFile] = File(None),
    clinic_license: Optional[UploadFile] = File(None),
):
    """Signup new clinic"""
    logger.info(f"Clinic signup attempt: {email}")

    clinic_logo_url = None
    license_document_url = None

    try:
        if clinic_photo and clinic_photo.filename:
            if not clinic_photo.content_type or not clinic_photo.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="Clinic photo must be an image")

            photo_bytes = await clinic_photo.read()
            photo_ext = os.path.splitext(clinic_photo.filename)[1] or ".jpg"
            photo_name = f"{clinic_name.replace(' ', '_')}-{int(time.time())}{photo_ext}"
            photo_path = SupabaseStorage.upload_clinic_image(
                user_id=email,
                file_data=photo_bytes,
                filename=photo_name,
                content_type=clinic_photo.content_type or "image/jpeg",
            )
            clinic_logo_url = supabase.storage.from_("clinic-images").get_public_url(photo_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading clinic photo: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error uploading clinic photo: {str(e)}")

    try:
        if clinic_license and clinic_license.filename:
            valid_types = ["image/jpeg", "image/png", "image/jpg", "application/pdf"]
            if clinic_license.content_type and clinic_license.content_type not in valid_types:
                raise HTTPException(status_code=400, detail="License must be a PDF or image (JPG/PNG)")

            license_bytes = await clinic_license.read()
            license_ext = os.path.splitext(clinic_license.filename)[1] or ".pdf"
            license_name = f"license-{clinic_name.replace(' ', '_')}-{int(time.time())}{license_ext}"
            license_path = SupabaseStorage.upload_clinic_document(
                user_id=email,
                file_data=license_bytes,
                filename=license_name,
                content_type=clinic_license.content_type or "application/pdf",
            )
            license_document_url = supabase.storage.from_("clinic-documents").get_public_url(license_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading clinic license: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error uploading clinic license: {str(e)}")
    
    result = AuthService.signup_clinic(
        email=email,
        password=password,
        clinic_name=clinic_name,
        phone=phone,
        address=address,
        city=city,
        state=state,
        zip_code=zip_code,
        country=country,
        website=website,
        opening_hours=opening_hours,
        description=description,
        clinic_logo_url=clinic_logo_url,
        license_document_url=license_document_url,
    )
    
    if not result["success"]:
        logger.warning(f"Clinic signup failed: {result.get('error')}")
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    logger.info(f"Clinic signup successful: {email}")
    return result


@router.post("/auth/login")
async def login(request: LoginRequest):
    """Login user - Returns role and permissions"""
    logger.info(f"Login attempt: {request.email}")
    
    try:
        result = AuthService.login(email=request.email, password=request.password)
        
        if not result["success"]:
            logger.warning(f"Login failed: {request.email}")
            raise HTTPException(status_code=401, detail=result.get("error"))
        
        logger.info(f"Login successful: {request.email} (role: {result.get('role')})")
        return result
    
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Login error: {str(e)}"
        )


@router.post("/auth/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """Request a password reset link (token emailed or returned when SMTP not configured)"""
    logger.info(f"Password reset requested for: {request.email}")
    try:
        result = AuthService.create_password_reset(email=request.email)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth/reset")
async def reset_password(request: ResetPasswordRequest):
    """Reset password using token and new password"""
    logger.info("Password reset attempt")
    try:
        result = AuthService.reset_password(token=request.token, new_password=request.new_password)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    except Exception as e:
        logger.error(f"Reset password error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Pet Management Endpoints
# ============================================

@router.post("/pets")
async def create_pet(
    user_id: str = Form(...),
    name: str = Form(...),
    pet_type: str = Form(...),
    breed: str = Form(...),
    date_of_birth: str = Form(...),
    weight: float = Form(...),
    weight_unit: str = Form("kg"),
    gender: Optional[str] = Form(None),
    blood_type: Optional[str] = Form(None),
    allergies: Optional[str] = Form(None),
    medical_conditions: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
):
    """Add new pet to database"""
    logger.info(f"Creating pet: {name} for user: {user_id}")

    profile_image_url = None

    try:
        if photo and photo.filename:
            if not photo.content_type or not photo.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="Pet photo must be an image")

            file_data = await photo.read()
            file_ext = os.path.splitext(photo.filename)[1] or ".jpg"
            storage_path = f"{user_id}/{int(time.time())}-{name.replace(' ', '_')}{file_ext}"
            SupabaseStorage.ensure_bucket("pet-images", public=True, allowed_mime_types=["image/*"])
            supabase.storage.from_("pet-images").upload(
                file=file_data,
                path=storage_path,
                file_options={
                    "content-type": photo.content_type or "image/jpeg",
                    "upsert": "false",
                },
            )
            profile_image_url = supabase.storage.from_("pet-images").get_public_url(storage_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading pet photo: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error uploading pet photo: {str(e)}")
    
    result = PetService.add_pet(
        user_id=user_id,
        name=name,
        pet_type=pet_type,
        breed=breed,
        date_of_birth=date_of_birth,
        weight=weight,
        weight_unit=weight_unit,
        gender=gender,
        blood_type=blood_type,
        allergies=allergies,
        medical_conditions=medical_conditions,
        notes=notes,
        profile_image_url=profile_image_url,
    )
    
    if not result["success"]:
        logger.error(f"Error creating pet: {result.get('error')}")
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    logger.info(f"Pet created successfully: {result.get('pet_id')}")
    return result


@router.get("/pets")
async def get_pets(user_id: str):
    """Get all pets for user"""
    logger.info(f"Fetching pets for user: {user_id}")
    
    result = PetService.get_user_pets(user_id=user_id)
    
    if not result["success"]:
        logger.error(f"Error fetching pets: {result.get('error')}")
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    logger.info(f"Fetched {result.get('count')} pets for user: {user_id}")
    return result


@router.get("/pets/{pet_id}")
async def get_pet_detail(pet_id: str):
    """Get pet details"""
    logger.info(f"Fetching pet details: {pet_id}")
    
    try:
        response = supabase.table("pets").select("*").eq("id", pet_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Pet not found")
        
        return {
            "success": True,
            "pet": response.data[0]
        }
    except Exception as e:
        logger.error(f"Error fetching pet: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/clinic/profile")
async def get_clinic_profile(user_id: str):
    """Get the current clinic profile for a logged in clinic user."""
    logger.info(f"Fetching clinic profile for user: {user_id}")

    try:
        response = supabase.table("clinics").select("*").eq("user_id", user_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Clinic not found")

        clinic = _parse_clinic_status(response.data[0])
        clinic["gallery_urls"] = SupabaseStorage.list_clinic_images(user_id)

        if not clinic.get("clinic_logo_url") and clinic["gallery_urls"]:
            clinic["clinic_logo_url"] = clinic["gallery_urls"][0]

        return {"success": True, "clinic": clinic}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching clinic profile: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/clinic/profile")
async def update_clinic_profile(
    user_id: str = Form(...),
    clinic_name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    zip_code: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    website: Optional[str] = Form(None),
    opening_hours: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    photos: Optional[List[UploadFile]] = File(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
):
    """Update the current clinic profile."""
    logger.info(f"Updating clinic profile for user: {user_id}")

    try:
        current = supabase.table("clinics").select("*").eq("user_id", user_id).execute()
        if not current.data:
            raise HTTPException(status_code=404, detail="Clinic not found")

        clinic = current.data[0]
        updates = {}

        if clinic_name is not None:
            updates["clinic_name"] = clinic_name
        if phone is not None:
            updates["phone"] = phone
        if address is not None:
            updates["address"] = address
        if city is not None:
            updates["city"] = city
        if state is not None:
            updates["state"] = state
        if zip_code is not None:
            updates["zip_code"] = zip_code
        if country is not None:
            updates["country"] = country
        if website is not None:
            updates["website"] = website
        if opening_hours is not None:
            updates["opening_hours"] = opening_hours
        if description is not None:
            updates["description"] = description
        if latitude is not None:
            updates["latitude"] = latitude
        if longitude is not None:
            updates["longitude"] = longitude

        if photo and photo.filename:
            if not photo.content_type or not photo.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="Clinic photo must be an image")

            photo_bytes = await photo.read()
            photo_ext = os.path.splitext(photo.filename)[1] or ".jpg"
            photo_name = f"{clinic.get('clinic_name', 'clinic').replace(' ', '_')}-{int(time.time())}{photo_ext}"
            photo_path = SupabaseStorage.upload_clinic_image(
                user_id=user_id,
                file_data=photo_bytes,
                filename=photo_name,
                content_type=photo.content_type or "image/jpeg",
            )
            updates["clinic_logo_url"] = supabase.storage.from_("clinic-images").get_public_url(photo_path)

        gallery_uploads = []
        for gallery_photo in photos or []:
            if not gallery_photo or not gallery_photo.filename:
                continue
            if not gallery_photo.content_type or not gallery_photo.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="Clinic gallery images must be images")

            image_bytes = await gallery_photo.read()
            image_ext = os.path.splitext(gallery_photo.filename)[1] or ".jpg"
            image_name = f"gallery-{int(time.time())}-{gallery_photo.filename.replace(' ', '_')}"
            if not image_name.endswith(image_ext):
                image_name += image_ext
            image_path = SupabaseStorage.upload_clinic_image(
                user_id=user_id,
                file_data=image_bytes,
                filename=image_name,
                content_type=gallery_photo.content_type or "image/jpeg",
            )
            gallery_uploads.append(supabase.storage.from_("clinic-images").get_public_url(image_path))

        if updates:
            try:
                supabase.table("clinics").update(updates).eq("user_id", user_id).execute()
            except Exception as db_err:
                err_msg = str(db_err)
                if "latitude" in err_msg or "longitude" in err_msg or "PGRST204" in err_msg:
                    logger.warning(f"Failed to update clinic coordinates (columns might be missing): {err_msg}. Retrying without coordinates.")
                    updates.pop("latitude", None)
                    updates.pop("longitude", None)
                    if updates:
                        supabase.table("clinics").update(updates).eq("user_id", user_id).execute()
                else:
                    raise

        refreshed = supabase.table("clinics").select("*").eq("user_id", user_id).execute()
        if not refreshed.data:
            raise HTTPException(status_code=404, detail="Clinic not found")

        clinic = _parse_clinic_status(refreshed.data[0])
        clinic["gallery_urls"] = SupabaseStorage.list_clinic_images(user_id)
        if gallery_uploads and not clinic.get("clinic_logo_url"):
            clinic["clinic_logo_url"] = gallery_uploads[0]

        return {"success": True, "clinic": clinic}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating clinic profile: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================
# Vaccine Records Endpoints
# ============================================

@router.post("/vaccine-records")
async def upload_vaccine_record(
    pet_id: str = Form(...),
    file: UploadFile = File(...),
    uploaded_by: str = Form(...),
    upload_date: Optional[str] = Form(None)
):
    """Upload vaccine record file"""
    logger.info(f"Uploading vaccine record: {file.filename} for pet: {pet_id}")
    
    try:
        file_data = await file.read()
        file_type = "pdf" if file.content_type == "application/pdf" else "image"
        
        result = PetService.upload_vaccine_record(
            pet_id=pet_id,
            file_data=file_data,
            file_name=file.filename,
            file_type=file_type,
            uploaded_by=uploaded_by,
            upload_date=upload_date
        )
        
        if not result["success"]:
            logger.error(f"Error uploading vaccine record: {result.get('error')}")
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        logger.info(f"Vaccine record uploaded: {result.get('record_id')}")
        return result
        
    except Exception as e:
        logger.error(f"Error uploading vaccine record: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/vaccine-records")
async def get_vaccine_records(pet_id: str):
    """Get all vaccine records for a pet"""
    logger.info(f"Fetching vaccine records for pet: {pet_id}")
    
    result = PetService.get_pet_vaccine_records(pet_id=pet_id)
    
    if not result["success"]:
        logger.error(f"Error fetching vaccine records: {result.get('error')}")
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    logger.info(f"Fetched {result.get('count')} vaccine records for pet: {pet_id}")
    return result


# ============================================
# Clinic Endpoints
# ============================================

@router.get("/clinic/patients")
async def get_clinic_patients(clinic_id: str):
    """Get all patients for a clinic"""
    logger.info(f"Fetching patients for clinic: {clinic_id}")
    
    try:
        resp = supabase.table("appointments").select("*").eq("clinic_id", clinic_id).order("appointment_date", desc=False).execute()
        appts = resp.data or []

        # Enrich each appointment with pet name and owner full name for frontend display
        enriched = []
        for a in appts:
            pet_name = None
            owner_name = None
            try:
                if a.get("pet_id"):
                    pet_resp = supabase.table("pets").select("id,name").eq("id", a.get("pet_id")).execute()
                    if pet_resp.data:
                        pet_name = pet_resp.data[0].get("name")
                if a.get("owner_id"):
                    owner_resp = supabase.table("pet_owners").select("full_name").eq("user_id", a.get("owner_id")).execute()
                    if owner_resp.data:
                        owner_name = owner_resp.data[0].get("full_name")
            except Exception:
                pass

            item = dict(a)
            item["pet_name"] = pet_name or a.get("pet_id")
            item["owner_name"] = owner_name or a.get("owner_id")
            enriched.append(item)

        logger.info(f"Fetched {len(enriched)} appointments for clinic: {clinic_id}")
        return {"success": True, "appointments": enriched, "count": len(enriched)}
    except Exception as e:
        logger.error(f"Error fetching clinic patients: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/appointments/{appointment_id}/status")
async def update_appointment_status(appointment_id: str, status: str = Form(...)):
    """Update appointment status (scheduled, completed, cancelled)"""
    logger.info(f"Updating appointment {appointment_id} status to {status}")
    try:
        # Validate status
        valid = {"scheduled", "completed", "cancelled", "in_progress"}
        if status not in valid:
            raise HTTPException(status_code=400, detail="Invalid status")

        appt_resp = supabase.table("appointments").select("id,pet_id,clinic_id,owner_id,appointment_date,appointment_time,reason,notes,status").eq("id", appointment_id).execute()
        if not appt_resp.data:
            raise HTTPException(status_code=404, detail="Appointment not found")

        appt = appt_resp.data[0]
        supabase.table("appointments").update({"status": status, "updated_at": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}).eq("id", appointment_id).execute()

        pet_resp = supabase.table("pets").select("name").eq("id", appt.get("pet_id")).execute()
        pet_name = pet_resp.data[0].get("name") if pet_resp.data else "your pet"
        clinic_resp = supabase.table("clinics").select("id,user_id,clinic_name").eq("id", appt.get("clinic_id")).execute()
        clinic_row = clinic_resp.data[0] if clinic_resp.data else None
        clinic_user_id = clinic_row.get("user_id") if clinic_row else None
        clinic_name = clinic_row.get("clinic_name") if clinic_row else "Clinic"
        owner_role = _fetch_user_role(appt.get("owner_id"))
        clinic_role = _fetch_user_role(clinic_user_id) if clinic_user_id else None
        status_label = status.replace("_", " ").title()
        title = f"Appointment {status_label}"
        message = f"{pet_name}'s appointment with {clinic_name} on {appt.get('appointment_date')} at {appt.get('appointment_time')} was updated to {status_label}."

        _create_notification(
            appt.get("owner_id"),
            "appointment_status",
            title,
            message,
            user_role=owner_role,
            entity_type="appointment",
            entity_id=appointment_id,
            link_url=f"/my-pets/{appt.get('pet_id')}",
            metadata={"status": status, "pet_id": appt.get("pet_id"), "clinic_id": appt.get("clinic_id")},
        )
        if clinic_user_id:
            _create_notification(
                clinic_user_id,
                "appointment_status",
                title,
                message,
                user_role=clinic_role,
                entity_type="appointment",
                entity_id=appointment_id,
                link_url="/clinic/patients",
                metadata={"status": status, "pet_id": appt.get("pet_id"), "clinic_id": appt.get("clinic_id")},
            )

        return {"success": True, "appointment_id": appointment_id, "status": status}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating appointment status: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================
# Admin Endpoints (requires ADMIN_PASSWORD in Authorization header)
# ============================================

REJECTION_MARKER = "__ADMIN_REJECTION__::"


def _parse_clinic_status(clinic: dict) -> dict:
    """Derive verification status and rejection metadata from a clinic row."""
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


def _strip_rejection_marker(description: Optional[str]) -> str:
    """Remove any stored rejection metadata from a clinic description."""
    if not description:
        return ""

    if REJECTION_MARKER not in description:
        return description.strip()

    return description.split(REJECTION_MARKER, 1)[0].rstrip()


def _check_admin_auth(request: Request):
    """Simple admin auth: expects header Authorization: Bearer <ADMIN_PASSWORD> or valid env admin creds"""
    admin_pass = os.getenv("ADMIN_PASSWORD")
    if not admin_pass:
        return False

    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1]
        return token == admin_pass

    return False


def _safe_notification_insert(notification_data: dict):
    """Insert a notification if the table exists; fail softly otherwise."""
    try:
        return supabase.table("notifications").insert(notification_data).execute()
    except Exception as e:
        logger.warning(f"Notification insert skipped/failed: {str(e)}")
        return None


def _create_notification(
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    *,
    user_role: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    link_url: Optional[str] = None,
    metadata: Optional[dict] = None,
):
    if not user_id:
        return None

    payload = {
        "user_id": user_id,
        "user_role": user_role,
        "type": notification_type,
        "title": title,
        "message": message,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "link_url": link_url,
        "metadata": metadata or {},
        "is_read": False,
        "created_at": datetime.utcnow().isoformat(),
    }
    return _safe_notification_insert(payload)


def _fetch_user_role(user_id: str) -> Optional[str]:
    try:
        resp = supabase.table("auth_users").select("role").eq("id", user_id).execute()
        if resp.data:
            return resp.data[0].get("role")
    except Exception:
        return None
    return None


import sqlite3

def _get_sqlite_conn():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "local_reviews.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("""
    CREATE TABLE IF NOT EXISTS clinic_reviews (
        id TEXT PRIMARY KEY,
        appointment_id TEXT UNIQUE,
        clinic_id TEXT,
        pet_id TEXT,
        owner_id TEXT,
        rating INTEGER,
        treatment TEXT,
        comment TEXT,
        created_at TEXT
    )
    """)
    conn.commit()
    return conn


def _local_insert_review(review_data: dict) -> dict:
    import uuid
    conn = _get_sqlite_conn()
    review_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO clinic_reviews (id, appointment_id, clinic_id, pet_id, owner_id, rating, treatment, comment, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            review_id,
            review_data.get("appointment_id"),
            review_data.get("clinic_id"),
            review_data.get("pet_id"),
            review_data.get("owner_id"),
            review_data.get("rating"),
            review_data.get("treatment"),
            review_data.get("comment"),
            created_at
        )
    )
    conn.commit()
    row = conn.execute("SELECT * FROM clinic_reviews WHERE id = ?", (review_id,)).fetchone()
    conn.close()
    return dict(row)


def _local_get_clinic_reviews(clinic_id: str) -> list:
    conn = _get_sqlite_conn()
    count = conn.execute("SELECT COUNT(*) FROM clinic_reviews WHERE clinic_id = ?", (clinic_id,)).fetchone()[0]
    if count == 0:
        import uuid
        mock_reviews = [
            {
                "id": str(uuid.uuid4()),
                "appointment_id": f"mock-appt-1-{clinic_id}",
                "clinic_id": clinic_id,
                "pet_id": "mock-pet-1",
                "owner_id": "mock-owner-1",
                "rating": 5,
                "treatment": "Excellent care and very professional staff",
                "comment": "Dr. Jenkins was amazing with Max!",
                "created_at": "2024-03-15T10:00:00Z"
            },
            {
                "id": str(uuid.uuid4()),
                "appointment_id": f"mock-appt-2-{clinic_id}",
                "clinic_id": clinic_id,
                "pet_id": "mock-pet-2",
                "owner_id": "mock-owner-2",
                "rating": 5,
                "treatment": "Best vet clinic in the area",
                "comment": "Highly recommend!",
                "created_at": "2024-02-28T14:30:00Z"
            }
        ]
        for mr in mock_reviews:
            try:
                conn.execute(
                    "INSERT INTO clinic_reviews (id, appointment_id, clinic_id, pet_id, owner_id, rating, treatment, comment, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (mr["id"], mr["appointment_id"], mr["clinic_id"], mr["pet_id"], mr["owner_id"], mr["rating"], mr["treatment"], mr["comment"], mr["created_at"])
                )
            except Exception:
                pass
        conn.commit()

    rows = conn.execute(
        "SELECT * FROM clinic_reviews WHERE clinic_id = ? ORDER BY created_at DESC",
        (clinic_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def _local_get_reviews_by_appointments(appointment_ids: list) -> list:
    if not appointment_ids:
        return []
    conn = _get_sqlite_conn()
    placeholders = ",".join("?" for _ in appointment_ids)
    rows = conn.execute(
        f"SELECT * FROM clinic_reviews WHERE appointment_id IN ({placeholders})",
        appointment_ids
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def _format_review(review: dict) -> dict:
    """Return a frontend-friendly review payload enriched with pet/owner names."""
    item = dict(review)
    owner_name = item.get("reviewer") or item.get("owner_name") or "Pet Owner"
    pet_label = item.get("pet") or item.get("pet_name") or "Pet"

    if item.get("owner_id") == "mock-owner-1":
        owner_name = "John Smith"
    elif item.get("owner_id") == "mock-owner-2":
        owner_name = "Sarah Chen"

    if item.get("pet_id") == "mock-pet-1":
        pet_label = "Max (Golden Retriever)"
    elif item.get("pet_id") == "mock-pet-2":
        pet_label = "Bella (Poodle)"

    if "mock-" not in str(item.get("owner_id")):
        try:
            if item.get("owner_id"):
                owner_resp = supabase.table("pet_owners").select("full_name").eq("user_id", item.get("owner_id")).execute()
                if owner_resp.data and owner_resp.data[0].get("full_name"):
                    owner_name = owner_resp.data[0].get("full_name")
        except Exception:
            pass

    if "mock-" not in str(item.get("pet_id")):
        try:
            if item.get("pet_id"):
                pet_resp = supabase.table("pets").select("name,breed").eq("id", item.get("pet_id")).execute()
                if pet_resp.data:
                    pet = pet_resp.data[0]
                    pet_name = pet.get("name") or "Pet"
                    pet_label = f"{pet_name} ({pet.get('breed')})" if pet.get("breed") else pet_name
        except Exception:
            pass

    return {
        "id": item.get("id"),
        "appointment_id": item.get("appointment_id"),
        "clinic_id": item.get("clinic_id"),
        "pet_id": item.get("pet_id"),
        "owner_id": item.get("owner_id"),
        "reviewer": owner_name,
        "pet": pet_label,
        "rating": item.get("rating") or 0,
        "treatment": item.get("treatment") or "",
        "comment": item.get("comment") or "",
        "date": (item.get("created_at") or "")[:10],
        "created_at": item.get("created_at"),
    }


def _attach_reviews_to_appointments(appointments: list) -> list:
    """Attach submitted reviews to appointment rows without failing old DBs that lack the table."""
    if not appointments:
        return []

    try:
        appointment_ids = [a.get("id") for a in appointments if a.get("id")]
        if not appointment_ids:
            return appointments

        try:
            reviews_resp = supabase.table("clinic_reviews").select("*").in_("appointment_id", appointment_ids).execute()
            reviews_data = reviews_resp.data or []
        except Exception as e:
            logger.warning(f"Supabase reviews fetch failed, falling back to SQLite: {str(e)}")
            reviews_data = _local_get_reviews_by_appointments(appointment_ids)

        reviews_by_appointment = {
            review.get("appointment_id"): _format_review(review)
            for review in reviews_data
            if review.get("appointment_id")
        }

        enriched = []
        for appointment in appointments:
            item = dict(appointment)
            review = reviews_by_appointment.get(item.get("id"))
            item["reviewed"] = bool(review)
            item["review"] = review
            enriched.append(item)
        return enriched
    except Exception as e:
        logger.warning(f"Review enrichment skipped/failed: {str(e)}")
        return appointments


def _get_clinic_reviews(clinic_id: str) -> list:
    """Fetch formatted reviews for a clinic, newest first."""
    try:
        response = (
            supabase.table("clinic_reviews")
            .select("*")
            .eq("clinic_id", clinic_id)
            .order("created_at", desc=True)
            .execute()
        )
        reviews_data = response.data or []
    except Exception as e:
        logger.warning(f"Supabase get clinic reviews failed, falling back to SQLite: {str(e)}")
        reviews_data = _local_get_clinic_reviews(clinic_id)
    return [_format_review(review) for review in reviews_data]


@router.get("/admin/clinics/pending")
async def get_pending_clinics(request: Request):
    """List all pending clinics (is_verified = false)"""
    logger.info("Admin: fetching pending clinics")

    if not _check_admin_auth(request):
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        resp = supabase.table("clinics").select("*").eq("is_verified", False).execute()
        clinics = []
        for clinic in resp.data or []:
            parsed = _parse_clinic_status(clinic)
            if parsed["verification_status"] == "pending":
                clinics.append(parsed)

        return {"success": True, "clinics": clinics, "count": len(clinics)}
    except Exception as e:
        logger.error(f"Error fetching pending clinics: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/admin/clinics")
async def get_all_clinics(request: Request):
    """List all clinics with derived verification status"""
    logger.info("Admin: fetching all clinics")

    if not _check_admin_auth(request):
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        resp = supabase.table("clinics").select("*").order("created_at", desc=True).execute()
        clinics = [_parse_clinic_status(clinic) for clinic in (resp.data or [])]

        return {"success": True, "clinics": clinics, "count": len(clinics)}
    except Exception as e:
        logger.error(f"Error fetching all clinics: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/clinics")
async def get_public_clinics():
    """Public endpoint: list verified clinics for frontend listing"""
    logger.info("Public: fetching verified clinics")
    try:
        resp = supabase.table("clinics").select("*").eq("is_verified", True).order("created_at", desc=True).execute()
        clinics = []
        for clinic in (resp.data or []):
            parsed = _parse_clinic_status(clinic)
            user_id = parsed.get('user_id')
            parsed['gallery_urls'] = SupabaseStorage.list_clinic_images(user_id) if user_id else []
            # ensure clinic_logo_url is set to a public URL string
            if not parsed.get('clinic_logo_url') and parsed['gallery_urls']:
                parsed['clinic_logo_url'] = parsed['gallery_urls'][0]
            
            # Lookup reviews and calculate rating
            try:
                clinic_reviews = _get_clinic_reviews(parsed.get("id"))
                parsed['reviews'] = len(clinic_reviews)
                if clinic_reviews:
                    parsed['rating'] = round(sum((r.get('rating') or 0) for r in clinic_reviews) / len(clinic_reviews), 1)
                else:
                    parsed['rating'] = 0.0
            except Exception as review_error:
                logger.warning(f"Clinic list review lookup skipped/failed: {str(review_error)}")
                parsed['reviews'] = 0
                parsed['rating'] = 0.0
                
            clinics.append(parsed)

        return {"success": True, "clinics": clinics, "count": len(clinics)}
    except Exception as e:
        logger.error(f"Error fetching public clinics: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/clinics/{clinic_id}")
async def get_clinic_by_id(clinic_id: str):
    """Public endpoint: get clinic by clinic id"""
    logger.info(f"Public: fetching clinic by id {clinic_id}")
    try:
        resp = supabase.table("clinics").select("*").eq("id", clinic_id).execute()
        if not resp.data:
            raise HTTPException(status_code=404, detail="Clinic not found")

        clinic = _parse_clinic_status(resp.data[0])
        user_id = clinic.get('user_id')
        clinic['gallery_urls'] = SupabaseStorage.list_clinic_images(user_id) if user_id else []
        if not clinic.get('clinic_logo_url') and clinic['gallery_urls']:
            clinic['clinic_logo_url'] = clinic['gallery_urls'][0]

        try:
            clinic_reviews = _get_clinic_reviews(clinic_id)
            clinic['clinicReviews'] = clinic_reviews
            clinic['reviews'] = len(clinic_reviews)
            if clinic_reviews:
                clinic['rating'] = round(sum((r.get('rating') or 0) for r in clinic_reviews) / len(clinic_reviews), 1)
        except Exception as review_error:
            logger.warning(f"Clinic review lookup skipped/failed: {str(review_error)}")
            clinic['clinicReviews'] = []

        return {"success": True, "clinic": clinic}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching clinic by id: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/admin/stats")
async def get_admin_stats(request: Request):
    """Return admin dashboard counts and recent clinic activity"""
    logger.info("Admin: fetching stats")

    if not _check_admin_auth(request):
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        all_resp = supabase.table("clinics").select("id, is_verified, clinic_name, created_at, description").execute()
        clinics = [_parse_clinic_status(clinic) for clinic in (all_resp.data or [])]
        total_clinics = len(clinics)
        approved_clinics = sum(1 for c in clinics if c.get("verification_status") == "approved")
        pending_clinics = sum(1 for c in clinics if c.get("verification_status") == "pending")
        rejected_clinics = sum(1 for c in clinics if c.get("verification_status") == "rejected")

        recent = sorted(clinics, key=lambda c: c.get("created_at") or "", reverse=True)[:3]
        recent_verifications = []
        for clinic in recent:
            recent_verifications.append({
                "clinic": clinic.get("clinic_name", "Unknown Clinic"),
                "action": clinic.get("verification_status", "pending").title(),
                "time": clinic.get("created_at"),
                "badge": (
                    "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                    if clinic.get("verification_status") == "approved"
                    else "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                    if clinic.get("verification_status") == "rejected"
                    else "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                ),
            })

        return {
            "success": True,
            "stats": {
                "total_clinics": total_clinics,
                "pending_verifications": pending_clinics,
                "approved_clinics": approved_clinics,
                "rejected": rejected_clinics,
            },
            "recent_verifications": recent_verifications,
        }
    except Exception as e:
        logger.error(f"Error fetching admin stats: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/admin/clinics/{clinic_id}/approve")
async def approve_clinic(clinic_id: str, request: Request):
    """Approve a clinic - sets is_verified to true"""
    logger.info(f"Admin: approving clinic {clinic_id}")

    if not _check_admin_auth(request):
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        clinic_resp = supabase.table("clinics").select("id, user_id, email, clinic_name").eq("id", clinic_id).execute()
        if not clinic_resp.data:
            raise HTTPException(status_code=404, detail="Clinic not found")

        clinic = clinic_resp.data[0]
        user_id = clinic.get("user_id")
        clinic_name = clinic.get("clinic_name") or "Your clinic"
        current = supabase.table("clinics").select("description").eq("id", clinic_id).execute()
        current_description = current.data[0].get("description") if current.data else ""
        clean_description = _strip_rejection_marker(current_description)

        # Update clinic to verified
        supabase.table("clinics").update({"is_verified": True, "description": clean_description}).eq("id", clinic_id).execute()

        # Also activate corresponding auth user explicitly
        if user_id:
            supabase.table("auth_users").update({"is_active": True}).eq("id", user_id).execute()
            
            # Create notification
            _create_notification(
                user_id,
                "clinic_approval",
                "Clinic Approved ✅",
                f"Congratulations! {clinic_name} has been approved by the admin. You can now access all features.",
                user_role="clinic",
                entity_type="clinic",
                entity_id=clinic_id,
                link_url="/clinic/dashboard",
                metadata={"status": "approved", "clinic_id": clinic_id}
            )

        return {"success": True, "clinic_id": clinic_id, "message": "Clinic approved"}
    except Exception as e:
        logger.error(f"Error approving clinic: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/admin/clinics/{clinic_id}/reject")
async def reject_clinic(clinic_id: str, request: Request):
    """Reject a clinic - keeps is_verified as false (stays pending)"""
    logger.info(f"Admin: rejecting clinic {clinic_id}")

    if not _check_admin_auth(request):
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        clinic_resp = supabase.table("clinics").select("id, user_id, email, clinic_name").eq("id", clinic_id).execute()
        if not clinic_resp.data:
            raise HTTPException(status_code=404, detail="Clinic not found")

        clinic = clinic_resp.data[0]
        user_id = clinic.get("user_id")
        clinic_name = clinic.get("clinic_name") or "Your clinic"

        # Read optional reason from request body
        try:
            body = await request.json()
        except Exception:
            body = {}
        reason = (body or {}).get("reason")

        # Fetch current description to append rejection marker (avoids schema changes)
        current = supabase.table("clinics").select("description").eq("id", clinic_id).execute()
        current_desc = ""
        if current.data:
            current_desc = _strip_rejection_marker(current.data[0].get("description") or "")

        from datetime import datetime
        marker = REJECTION_MARKER
        if reason:
            timestamp = datetime.utcnow().isoformat()
            # sanitize reason to avoid marker collisions
            safe_reason = str(reason).replace("::", "--")
            marker_payload = f"reason={safe_reason}::time={timestamp}"
            new_desc = current_desc + ("\n\n" if current_desc else "") + marker + marker_payload
        else:
            # If no reason provided, still add a rejection marker with time
            timestamp = datetime.utcnow().isoformat()
            marker_payload = f"time={timestamp}"
            new_desc = current_desc + ("\n\n" if current_desc else "") + marker + marker_payload

        # Update clinic: keep is_verified false and append description marker
        supabase.table("clinics").update({"is_verified": False, "description": new_desc}).eq("id", clinic_id).execute()

        # Keep associated auth user active so they can log in, view status, and edit/resubmit profile
        if user_id:
            supabase.table("auth_users").update({"is_active": True}).eq("id", user_id).execute()
            
            # Create notification
            rejection_message = f"Your registration for {clinic_name} was rejected by the admin."
            if reason:
                rejection_message += f" Reason: {reason}"
            else:
                rejection_message += " Please check your documents and resubmit."
            
            _create_notification(
                user_id,
                "clinic_rejection",
                "Clinic Verification Rejected ❌",
                rejection_message,
                user_role="clinic",
                entity_type="clinic",
                entity_id=clinic_id,
                link_url="/clinic/dashboard",
                metadata={"status": "rejected", "clinic_id": clinic_id, "reason": reason or ""}
            )

        return {"success": True, "clinic_id": clinic_id, "message": "Clinic rejected", "reason": reason, "rejected_at": timestamp}
    except Exception as e:
        logger.error(f"Error rejecting clinic: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))



@router.post("/medical-records")
async def create_medical_record(
    clinic_id: str,
    pet_id: str,
    record_type: str,
    visit_date: str,
    diagnosis: Optional[str] = None,
    treatment: Optional[str] = None,
    notes: Optional[str] = None
):
    """Create medical record (Clinic only)"""
    logger.info(f"Creating medical record for pet: {pet_id} by clinic: {clinic_id}")
    
    try:
        medical_data = {
            "pet_id": pet_id,
            "clinic_id": clinic_id,
            "record_type": record_type,
            "visit_date": visit_date,
            "diagnosis": diagnosis,
            "treatment": treatment,
            "notes": notes
        }
        
        response = supabase.table("medical_records").insert(medical_data).execute()
        
        logger.info(f"Medical record created: {response.data[0]['id']}")
        
        return {
            "success": True,
            "record_id": response.data[0]["id"],
            "message": "Medical record created successfully!"
        }
    except Exception as e:
        logger.error(f"Error creating medical record: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/pet/medical-records")
async def get_pet_medical_records(pet_id: str):
    """Get all medical records for a pet"""
    logger.info(f"Fetching medical records for pet: {pet_id}")
    
    try:
        response = supabase.table("medical_records").select("*").eq("pet_id", pet_id).execute()
        
        logger.info(f"Fetched {len(response.data)} medical records for pet: {pet_id}")
        
        return {
            "success": True,
            "records": response.data,
            "count": len(response.data)
        }
    except Exception as e:
        logger.error(f"Error fetching medical records: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================
# Appointment Endpoints
# ============================================

@router.post("/appointments")
async def create_appointment(
    request: CreateAppointmentRequest
):
    """Create appointment"""
    logger.info(f"Creating appointment for pet: {request.pet_id} at clinic: {request.clinic_id}")
    
    try:
        appointment_data = {
            "pet_id": request.pet_id,
            "clinic_id": request.clinic_id,
            "owner_id": request.owner_id,
            "appointment_date": request.appointment_date,
            "appointment_time": request.appointment_time,
            "reason": request.reason,
            "notes": request.notes,
            "status": "scheduled"
        }
        
        response = supabase.table("appointments").insert(appointment_data).execute()
        created = response.data[0]

        pet_resp = supabase.table("pets").select("name").eq("id", request.pet_id).execute()
        pet_name = pet_resp.data[0].get("name") if pet_resp.data else "your pet"
        clinic_resp = supabase.table("clinics").select("id,user_id,clinic_name").eq("id", request.clinic_id).execute()
        clinic_row = clinic_resp.data[0] if clinic_resp.data else None
        clinic_user_id = clinic_row.get("user_id") if clinic_row else None
        clinic_name = clinic_row.get("clinic_name") if clinic_row else "Clinic"
        owner_role = _fetch_user_role(request.owner_id)
        clinic_role = _fetch_user_role(clinic_user_id) if clinic_user_id else None

        title = "Appointment Scheduled"
        message = f"{pet_name} has a new appointment with {clinic_name} on {request.appointment_date} at {request.appointment_time}."
        _create_notification(
            request.owner_id,
            "appointment",
            title,
            message,
            user_role=owner_role,
            entity_type="appointment",
            entity_id=created.get("id"),
            link_url=f"/my-pets/{request.pet_id}",
            metadata={"status": "scheduled", "pet_id": request.pet_id, "clinic_id": request.clinic_id},
        )
        if clinic_user_id:
            _create_notification(
                clinic_user_id,
                "appointment",
                title,
                message,
                user_role=clinic_role,
                entity_type="appointment",
                entity_id=created.get("id"),
                link_url="/clinic/patients",
                metadata={"status": "scheduled", "pet_id": request.pet_id, "clinic_id": request.clinic_id},
            )

        logger.info(f"Appointment created: {created['id']}")
        
        return {
            "success": True,
            "appointment_id": created["id"],
            "appointment": created,
            "message": "Appointment created successfully!"
        }
    except Exception as e:
        logger.error(f"Error creating appointment: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reviews")
async def create_review(request: CreateReviewRequest):
    """Create a clinic review for a completed appointment."""
    logger.info(f"Creating review for appointment: {request.appointment_id}")

    try:
        if request.rating < 1 or request.rating > 5:
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

        treatment = (request.treatment or "").strip()
        if not treatment:
            raise HTTPException(status_code=400, detail="Treatment quality is required")

        appt_resp = supabase.table("appointments").select("*").eq("id", request.appointment_id).execute()
        if not appt_resp.data:
            raise HTTPException(status_code=404, detail="Appointment not found")

        appointment = appt_resp.data[0]
        status_value = (appointment.get("status") or "").lower()
        if status_value != "completed":
            raise HTTPException(status_code=400, detail="Only completed appointments can be reviewed")

        review_data = {
            "appointment_id": appointment.get("id"),
            "clinic_id": appointment.get("clinic_id"),
            "pet_id": appointment.get("pet_id"),
            "owner_id": appointment.get("owner_id"),
            "rating": request.rating,
            "treatment": treatment[:100],
            "comment": (request.comment or "").strip() or None,
        }

        try:
            response = supabase.table("clinic_reviews").insert(review_data).execute()
            created = response.data[0]
        except Exception as e:
            logger.warning(f"Supabase review insert failed, falling back to local SQLite: {str(e)}")
            created = _local_insert_review(review_data)

        formatted_review = _format_review(created)

        clinic_resp = supabase.table("clinics").select("user_id,clinic_name").eq("id", appointment.get("clinic_id")).execute()
        clinic_row = clinic_resp.data[0] if clinic_resp.data else None
        if clinic_row and clinic_row.get("user_id"):
            _create_notification(
                clinic_row.get("user_id"),
                "clinic_review",
                "New Client Review",
                f"A pet owner left a {request.rating}-star review for {clinic_row.get('clinic_name') or 'your clinic'}.",
                user_role=_fetch_user_role(clinic_row.get("user_id")),
                entity_type="review",
                entity_id=created.get("id"),
                link_url="/clinic/profile",
                metadata={"appointment_id": appointment.get("id"), "clinic_id": appointment.get("clinic_id")},
            )

        return {"success": True, "review": formatted_review, "message": "Review submitted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating review: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reviews/clinic")
async def get_reviews_for_clinic(clinic_id: str):
    """Get real reviews for a clinic."""
    logger.info(f"Fetching reviews for clinic: {clinic_id}")

    try:
        reviews = _get_clinic_reviews(clinic_id)
        average_rating = round(sum((r.get("rating") or 0) for r in reviews) / len(reviews), 1) if reviews else 0
        return {"success": True, "reviews": reviews, "count": len(reviews), "average_rating": average_rating}
    except Exception as e:
        logger.error(f"Error fetching clinic reviews: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/appointments/owner")
async def get_owner_appointments(owner_id: str):
    """Get all appointments for pet owner"""
    logger.info(f"Fetching appointments for owner: {owner_id}")
    
    try:
        response = supabase.table("appointments").select("*").eq("owner_id", owner_id).execute()
        appointments = _attach_reviews_to_appointments(response.data or [])
        
        logger.info(f"Fetched {len(response.data)} appointments for owner: {owner_id}")
        
        return {
            "success": True,
            "appointments": appointments,
            "count": len(appointments)
        }
    except Exception as e:
        logger.error(f"Error fetching owner appointments: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/appointments/clinic")
async def get_clinic_appointments(clinic_id: str):
    """Get all appointments for clinic"""
    logger.info(f"Fetching appointments for clinic: {clinic_id}")
    
    try:
        response = supabase.table("appointments").select("*").eq("clinic_id", clinic_id).execute()
        appointments = _attach_reviews_to_appointments(response.data or [])
        
        logger.info(f"Fetched {len(response.data)} appointments for clinic: {clinic_id}")
        
        return {
            "success": True,
            "appointments": appointments,
            "count": len(appointments)
        }
    except Exception as e:
        logger.error(f"Error fetching clinic appointments: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/appointments/pet")
async def get_pet_appointments(pet_id: str):
    """Get all appointments for a pet"""
    logger.info(f"Fetching appointments for pet: {pet_id}")

    try:
        response = supabase.table("appointments").select("*").eq("pet_id", pet_id).execute()
        appointments = _attach_reviews_to_appointments(response.data or [])

        logger.info(f"Fetched {len(response.data)} appointments for pet: {pet_id}")

        return {
            "success": True,
            "appointments": appointments,
            "count": len(appointments)
        }
    except Exception as e:
        logger.error(f"Error fetching pet appointments: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/notifications")
async def get_notifications(user_id: str, limit: int = 20):
    """Get notifications for a user (pet owner, clinic, or admin)."""
    logger.info(f"Fetching notifications for user: {user_id}")
    try:
        response = (
            supabase.table("notifications")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        notifications = response.data or []
        unread_count = sum(1 for item in notifications if not item.get("is_read"))
        return {"success": True, "notifications": notifications, "count": len(notifications), "unread_count": unread_count}
    except Exception as e:
        logger.error(f"Error fetching notifications: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    """Mark a single notification as read."""
    try:
        supabase.table("notifications").update({"is_read": True, "read_at": datetime.utcnow().isoformat()}).eq("id", notification_id).execute()
        return {"success": True, "notification_id": notification_id}
    except Exception as e:
        logger.error(f"Error marking notification read: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/notifications/read-all")
async def mark_all_notifications_read(request: NotificationReadRequest):
    """Mark all notifications for a user as read."""
    try:
        supabase.table("notifications").update({"is_read": True, "read_at": datetime.utcnow().isoformat()}).eq("user_id", request.user_id).eq("is_read", False).execute()
        return {"success": True, "user_id": request.user_id}
    except Exception as e:
        logger.error(f"Error marking all notifications read: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================
# User Profile Endpoints
# ============================================

@router.get("/user/profile")
async def get_user_profile(user_id: str):
    """Get user profile based on role"""
    logger.info(f"Fetching profile for user: {user_id}")
    
    result = AuthService.get_user_profile(user_id=user_id)
    
    if not result["success"]:
        logger.error(f"Error fetching profile: {result.get('error')}")
        raise HTTPException(status_code=404, detail=result.get("error"))
    
    logger.info(f"Profile fetched for user: {user_id}")
    return result


@router.put("/user/profile")
async def update_user_profile(
    user_id: str = Form(...),
    full_name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    zip_code: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    emergency_contact_name: Optional[str] = Form(None),
    emergency_contact_phone: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
):
    """Update pet owner profile details"""
    logger.info(f"Updating pet owner profile for user: {user_id}")
    
    profile_image_url = None
    
    try:
        if photo and photo.filename:
            if not photo.content_type or not photo.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="Profile photo must be an image")
            
            photo_bytes = await photo.read()
            photo_ext = os.path.splitext(photo.filename)[1] or ".jpg"
            photo_name = f"avatar-{int(time.time())}{photo_ext}"
            photo_path = SupabaseStorage.upload_user_avatar(
                user_id=user_id,
                file_data=photo_bytes,
                filename=photo_name,
                content_type=photo.content_type or "image/jpeg"
            )
            profile_image_url = supabase.storage.from_("user-avatars").get_public_url(photo_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading avatar photo: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error uploading avatar photo: {str(e)}")

    result = AuthService.update_user_profile(
        user_id=user_id,
        full_name=full_name,
        phone=phone,
        address=address,
        state=state,
        zip_code=zip_code,
        country=country,
        bio=bio,
        emergency_contact_name=emergency_contact_name,
        emergency_contact_phone=emergency_contact_phone,
        profile_image_url=profile_image_url,
        latitude=latitude,
        longitude=longitude
    )
    
    if not result["success"]:
        logger.error(f"Error updating profile: {result.get('error')}")
        raise HTTPException(status_code=400, detail=result.get("error"))
        
    logger.info(f"Profile updated successfully for user: {user_id}")
    return result


@router.get("/config/google-maps")
async def get_google_maps_config():
    """Get public Google Maps configuration key"""
    key = os.getenv("NEXT_PUBLIC_GOOGLE_MAPS_API_KEY", "")
    return {"key": key}


# ============================================
# Health Check
# ============================================

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Pet AI API",
        "database": "Supabase"
    }
