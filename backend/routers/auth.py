from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Optional
import logging
import time
import os
from datetime import datetime
from backend.core.dependencies import get_current_user
from backend.schemas.schemas import RegisterOwnerRequest, RegisterClinicRequest, NotificationReadRequest
from backend.services.auth_service import AuthService
from backend.core.supabase_config import supabase, SupabaseStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication & Notifications"])

@router.post("/register/owner")
async def register_owner(
    request: RegisterOwnerRequest,
    current_user: dict = Depends(get_current_user)
):
    """Complete registration of a new pet owner profile"""
    logger.info(f"Registering pet owner profile for user: {current_user['id']}")
    
    result = AuthService.register_pet_owner(
        user_id=current_user["id"],
        email=current_user["email"],
        first_name=request.first_name,
        last_name=request.last_name,
        phone=request.phone,
        address=request.address,
        state=request.state,
        zip_code=request.zip_code,
        country=request.country,
        bio=request.bio,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
        
    return result

@router.post("/register/clinic")
async def register_clinic(
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
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Complete registration of a new clinic profile"""
    logger.info(f"Registering clinic profile for user: {current_user['id']}")
    
    clinic_logo_url = None
    license_document_url = None

    # Handle image upload
    if clinic_photo and clinic_photo.filename:
        if not clinic_photo.content_type or not clinic_photo.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Scale photo must be an image")
        
        photo_bytes = await clinic_photo.read()
        photo_ext = os.path.splitext(clinic_photo.filename)[1] or ".jpg"
        photo_name = f"{clinic_name.replace(' ', '_')}-{int(time.time())}{photo_ext}"
        photo_path = SupabaseStorage.upload_clinic_image(
            user_id=current_user["id"],
            file_data=photo_bytes,
            filename=photo_name,
            content_type=clinic_photo.content_type or "image/jpeg"
        )
        clinic_logo_url = supabase.storage.from_("clinic-images").get_public_url(photo_path)

    # Handle license upload
    if clinic_license and clinic_license.filename:
        valid_types = ["image/jpeg", "image/png", "image/jpg", "application/pdf"]
        if clinic_license.content_type and clinic_license.content_type not in valid_types:
            raise HTTPException(status_code=400, detail="License must be a PDF or image (JPG/PNG)")
            
        license_bytes = await clinic_license.read()
        license_ext = os.path.splitext(clinic_license.filename)[1] or ".pdf"
        license_name = f"license-{clinic_name.replace(' ', '_')}-{int(time.time())}{license_ext}"
        license_path = SupabaseStorage.upload_clinic_document(
            user_id=current_user["id"],
            file_data=license_bytes,
            filename=license_name,
            content_type=clinic_license.content_type or "application/pdf"
        )
        license_document_url = supabase.storage.from_("clinic-documents").get_public_url(license_path)

    result = AuthService.register_clinic(
        user_id=current_user["id"],
        email=current_user["email"],
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
        latitude=latitude,
        longitude=longitude,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
        
    return result

@router.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Get the current authenticated user's profile"""
    result = AuthService.get_user_profile(current_user["id"])
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result

@router.put("/profile")
async def update_profile(
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
    current_user: dict = Depends(get_current_user)
):
    """Update pet owner profile details"""
    profile_image_url = None
    
    if photo and photo.filename:
        if not photo.content_type or not photo.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Profile photo must be an image")
        
        photo_bytes = await photo.read()
        photo_ext = os.path.splitext(photo.filename)[1] or ".jpg"
        photo_name = f"avatar-{int(time.time())}{photo_ext}"
        photo_path = SupabaseStorage.upload_user_avatar(
            user_id=current_user["id"],
            file_data=photo_bytes,
            filename=photo_name,
            content_type=photo.content_type or "image/jpeg"
        )
        profile_image_url = supabase.storage.from_("user-avatars").get_public_url(photo_path)

    updates = {}
    if full_name is not None:
        updates["full_name"] = full_name
    if phone is not None:
        updates["phone"] = phone
    if address is not None:
        updates["address"] = address
    if state is not None:
        updates["state"] = state
    if zip_code is not None:
        updates["zip_code"] = zip_code
    if country is not None:
        updates["country"] = country
    if bio is not None:
        updates["bio"] = bio
    if emergency_contact_name is not None:
        updates["emergency_contact_name"] = emergency_contact_name
    if emergency_contact_phone is not None:
        updates["emergency_contact_phone"] = emergency_contact_phone
    if profile_image_url is not None:
        updates["profile_image_url"] = profile_image_url
    if latitude is not None:
        updates["latitude"] = latitude
    if longitude is not None:
        updates["longitude"] = longitude

    result = AuthService.update_user_profile(user_id=current_user["id"], updates=updates)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
        
    return result

# ============================================
# Notification Endpoints
# ============================================

@router.get("/notifications")
async def get_notifications(limit: int = 20, current_user: dict = Depends(get_current_user)):
    """Get notifications for the current authenticated user"""
    logger.info(f"Fetching notifications for user: {current_user['id']}")
    try:
        response = (
            supabase.table("notifications")
            .select("*")
            .eq("user_id", current_user["id"])
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
async def mark_notification_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    """Mark a single notification as read"""
    try:
        # Check authorization
        notif_resp = supabase.table("notifications").select("user_id").eq("id", notification_id).execute()
        if not notif_resp.data or notif_resp.data[0]["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        supabase.table("notifications").update({
            "is_read": True, 
            "read_at": datetime.utcnow().isoformat()
        }).eq("id", notification_id).execute()
        
        return {"success": True, "notification_id": notification_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification read: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/notifications/read-all")
async def mark_all_notifications_read(current_user: dict = Depends(get_current_user)):
    """Mark all notifications for the current user as read"""
    try:
        supabase.table("notifications").update({
            "is_read": True, 
            "read_at": datetime.utcnow().isoformat()
        }).eq("user_id", current_user["id"]).eq("is_read", False).execute()
        
        return {"success": True, "user_id": current_user["id"]}
    except Exception as e:
        logger.error(f"Error marking all notifications read: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
