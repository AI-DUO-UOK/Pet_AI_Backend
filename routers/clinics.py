from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
from typing import Optional, List
import logging
import time
import os
from core.dependencies import get_current_user, require_role, get_clinic_service
from services.clinic_service import ClinicService
from core.supabase_config import supabase, SupabaseStorage

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Clinics"])

@router.get("/clinic/profile")
async def get_clinic_profile(
    current_user: dict = Depends(get_current_user),
    clinic_service: ClinicService = Depends(get_clinic_service)
):
    """Get the current logged-in clinic's profile details"""
    if current_user["role"] != "clinic":
        raise HTTPException(status_code=403, detail="Access denied. Clinic role required.")

    result = clinic_service.get_clinic_profile(user_id=current_user["id"])
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result

@router.put("/clinic/profile")
async def update_clinic_profile(
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
    current_user: dict = Depends(get_current_user),
    clinic_service: ClinicService = Depends(get_clinic_service)
):
    """Update the current logged-in clinic's profile details"""
    if current_user["role"] != "clinic":
        raise HTTPException(status_code=403, detail="Access denied. Clinic role required.")

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

    # Upload main photo
    if photo and photo.filename:
        if not photo.content_type or not photo.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Clinic photo must be an image")
        
        photo_bytes = await photo.read()
        photo_ext = os.path.splitext(photo.filename)[1] or ".jpg"
        photo_name = f"{clinic_name or 'logo'}-{int(time.time())}{photo_ext}"
        photo_path = SupabaseStorage.upload_clinic_image(
            user_id=current_user["id"],
            file_data=photo_bytes,
            filename=photo_name,
            content_type=photo.content_type or "image/jpeg"
        )
        updates["clinic_logo_url"] = supabase.storage.from_("clinic-images").get_public_url(photo_path)

    # Upload gallery photos
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
        
        # We upload it but we don't save to the main table, as SupabaseStorage lists them
        SupabaseStorage.upload_clinic_image(
            user_id=current_user["id"],
            file_data=image_bytes,
            filename=image_name,
            content_type=gallery_photo.content_type or "image/jpeg",
        )

    result = clinic_service.update_clinic_profile(user_id=current_user["id"], updates=updates)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
        
    return result

@router.get("/clinics")
async def get_public_clinics(clinic_service: ClinicService = Depends(get_clinic_service)):
    """Public endpoint: Get all verified clinics"""
    result = clinic_service.get_public_clinics()
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@router.get("/clinics/{clinic_id}")
async def get_clinic_by_id(
    clinic_id: str,
    clinic_service: ClinicService = Depends(get_clinic_service)
):
    """Public endpoint: Get clinic details by clinic ID"""
    result = clinic_service.get_clinic_by_id(clinic_id=clinic_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result

@router.get("/clinic/patients")
async def get_clinic_patients(
    current_user: dict = Depends(get_current_user),
    clinic_service: ClinicService = Depends(get_clinic_service)
):
    """Get all appointments / patients for the current clinic"""
    if current_user["role"] != "clinic":
        raise HTTPException(status_code=403, detail="Access denied. Clinic role required.")

    result = clinic_service.get_clinic_patients(user_id=current_user["id"])
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result
