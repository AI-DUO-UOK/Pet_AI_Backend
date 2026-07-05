from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Optional, List
import logging
import time
import os
import tempfile
from backend.core.dependencies import get_current_user
from backend.services.pet_service import PetService
from backend.core.supabase_config import supabase, SupabaseStorage
from backend.services.vaccine_service import VaccineService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Pets, Vaccines & Medical Records"])

# ============================================
# Pet Endpoints
# ============================================

@router.post("/pets")
async def create_pet(
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
    current_user: dict = Depends(get_current_user)
):
    """Add a new pet (Owner only)"""
    if current_user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Only pet owners can add pets")

    profile_image_url = None
    if photo and photo.filename:
        if not photo.content_type or not photo.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Pet photo must be an image")

        file_data = await photo.read()
        file_ext = os.path.splitext(photo.filename)[1] or ".jpg"
        storage_path = f"{current_user['id']}/{int(time.time())}-{name.replace(' ', '_')}{file_ext}"
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

    result = PetService.add_pet(
        user_id=current_user["id"],
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
        profile_image_url=profile_image_url
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result

@router.get("/pets")
async def get_pets(current_user: dict = Depends(get_current_user)):
    """Get all pets for the currently logged-in user (Owner) or all pets if Clinic/Admin"""
    if current_user["role"] == "owner":
        result = PetService.get_user_pets(user_id=current_user["id"])
    else:
        try:
            response = supabase.table("pets").select("*").execute()
            result = {
                "success": True,
                "pets": response.data or [],
                "count": len(response.data or [])
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result

@router.get("/pets/{pet_id}")
async def get_pet_detail(pet_id: str, current_user: dict = Depends(get_current_user)):
    """Get detailed profile of a specific pet"""
    try:
        response = supabase.table("pets").select("*").eq("id", pet_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Pet not found")
        
        pet = response.data[0]
        if current_user["role"] == "owner" and pet["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        return {"success": True, "pet": pet}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/pets/{pet_id}")
async def update_pet_detail(
    pet_id: str,
    name: Optional[str] = Form(None),
    pet_type: Optional[str] = Form(None),
    breed: Optional[str] = Form(None),
    date_of_birth: Optional[str] = Form(None),
    weight: Optional[float] = Form(None),
    weight_unit: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    blood_type: Optional[str] = Form(None),
    allergies: Optional[str] = Form(None),
    medical_conditions: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    """Update details of a specific pet"""
    try:
        current = supabase.table("pets").select("*").eq("id", pet_id).execute()
        if not current.data:
            raise HTTPException(status_code=404, detail="Pet not found")
        
        pet = current.data[0]
        if current_user["role"] == "owner" and pet["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        updates = {}
        if name is not None:
            updates["name"] = name
        if pet_type is not None:
            updates["type"] = pet_type.lower()
        if breed is not None:
            updates["breed"] = breed
        if date_of_birth is not None:
            updates["date_of_birth"] = date_of_birth
        if weight is not None:
            updates["weight"] = weight
        if weight_unit is not None:
            updates["weight_unit"] = weight_unit
        if gender is not None:
            updates["gender"] = gender
        if blood_type is not None:
            updates["blood_type"] = blood_type
        if allergies is not None:
            updates["allergies"] = allergies
        if medical_conditions is not None:
            updates["medical_conditions"] = medical_conditions
        if notes is not None:
            updates["notes"] = notes

        if photo and photo.filename:
            if not photo.content_type or not photo.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="Pet photo must be an image")
            
            file_data = await photo.read()
            file_ext = os.path.splitext(photo.filename)[1] or ".jpg"
            storage_path = f"{pet['user_id']}/{int(time.time())}-{name or pet['name']}{file_ext}".replace(' ', '_')
            SupabaseStorage.ensure_bucket("pet-images", public=True, allowed_mime_types=["image/*"])
            supabase.storage.from_("pet-images").upload(
                file=file_data,
                path=storage_path,
                file_options={
                    "content-type": photo.content_type or "image/jpeg",
                    "upsert": "false",
                },
            )
            updates["profile_image_url"] = supabase.storage.from_("pet-images").get_public_url(storage_path)

        result = PetService.update_pet(pet_id=pet_id, updates=updates)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# Vaccine Records Endpoints
# ============================================

@router.post("/vaccine-records")
async def upload_vaccine_record(
    pet_id: str = Form(...),
    file: UploadFile = File(...),
    upload_date: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Upload a vaccination record for a pet"""
    try:
        pet_resp = supabase.table("pets").select("user_id").eq("id", pet_id).execute()
        if not pet_resp.data:
            raise HTTPException(status_code=404, detail="Pet not found")
        
        if current_user["role"] == "owner" and pet_resp.data[0]["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        file_data = await file.read()
        file_type = "pdf" if file.content_type == "application/pdf" else "image"

        result = PetService.upload_vaccine_record(
            pet_id=pet_id,
            file_data=file_data,
            file_name=file.filename,
            file_type=file_type,
            uploaded_by=current_user["id"],
            upload_date=upload_date
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/vaccine-records")
async def get_vaccine_records(pet_id: str, current_user: dict = Depends(get_current_user)):
    """Get all vaccine records for a pet"""
    try:
        pet_resp = supabase.table("pets").select("user_id").eq("id", pet_id).execute()
        if not pet_resp.data:
            raise HTTPException(status_code=404, detail="Pet not found")
        
        if current_user["role"] == "owner" and pet_resp.data[0]["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        result = PetService.get_pet_vaccine_records(pet_id=pet_id)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================
# Advanced Vaccine Processing Endpoints
# ============================================

@router.post("/vaccines/upload-document")
async def upload_vaccine_document(
    pet_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload vaccine booklet/card image, extract data via VLM, and store records"""
    logger.info(f"Uploading vaccine document for pet: {pet_id} by user: {current_user['id']}")
    
    # Check authorization
    pet_resp = supabase.table("pets").select("user_id").eq("id", pet_id).execute()
    if not pet_resp.data:
        raise HTTPException(status_code=404, detail="Pet not found")
    if current_user["role"] == "owner" and pet_resp.data[0]["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename or ".jpg")[1]) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        file_ext = os.path.splitext(file.filename or ".jpg")[1]
        storage_path = f"vaccine-documents/{pet_id}/{int(time.time())}{file_ext}"
        
        SupabaseStorage.ensure_bucket("vaccine-documents", public=True, allowed_mime_types=["image/*", "application/pdf"])
        
        with open(tmp_path, "rb") as f:
            file_data = f.read()
        
        supabase.storage.from_("vaccine-documents").upload(
            file=file_data,
            path=storage_path,
            file_options={
                "content-type": file.content_type or "image/jpeg",
                "upsert": "false",
            },
        )
        image_url = supabase.storage.from_("vaccine-documents").get_public_url(storage_path)
        
        result = VaccineService.upload_vaccine_document(
            pet_id=pet_id,
            image_url=image_url,
            image_path=tmp_path
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to process vaccine document"))
        
        return {
            "success": True,
            "document_id": result.get("document_id"),
            "records_count": result.get("records_count"),
            "records": result.get("records"),
            "message": f"Successfully extracted {result.get('records_count')} vaccine records!"
        }
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@router.post("/vaccines/manual-entry")
async def add_manual_vaccine(
    pet_id: str = Form(...),
    vaccine_name: str = Form(...),
    vaccination_date: str = Form(...),
    next_due_date: Optional[str] = Form(None),
    batch_number: Optional[str] = Form(None),
    veterinarian_name: Optional[str] = Form(None),
    clinic_name: Optional[str] = Form(None),
    clinic_id: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    source: str = Form("vet_entry"),
    current_user: dict = Depends(get_current_user)
):
    """Add a vaccine record manually (Clinics or Vets)"""
    # Verify clinic role or admin
    if current_user["role"] not in ["clinic", "admin"]:
        raise HTTPException(status_code=403, detail="Only clinics and admins can make manual vaccine entries")

    result = VaccineService.add_manual_vaccine_entry(
        pet_id=pet_id,
        vaccine_name=vaccine_name,
        vaccination_date=vaccination_date,
        next_due_date=next_due_date,
        batch_number=batch_number,
        veterinarian_name=veterinarian_name,
        clinic_name=clinic_name,
        clinic_id=clinic_id,
        notes=notes,
        source=source
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result

@router.get("/vaccines/{pet_id}")
async def get_pet_vaccines(pet_id: str, current_user: dict = Depends(get_current_user)):
    """Get all vaccination records for a pet"""
    pet_resp = supabase.table("pets").select("user_id").eq("id", pet_id).execute()
    if not pet_resp.data:
        raise HTTPException(status_code=404, detail="Pet not found")
    if current_user["role"] == "owner" and pet_resp.data[0]["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = VaccineService.get_pet_vaccines(pet_id=pet_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result

@router.get("/vaccines/{pet_id}/documents")
async def get_pet_vaccine_documents(pet_id: str, current_user: dict = Depends(get_current_user)):
    """Get uploaded vaccine documents for a pet"""
    pet_resp = supabase.table("pets").select("user_id").eq("id", pet_id).execute()
    if not pet_resp.data:
        raise HTTPException(status_code=404, detail="Pet not found")
    if current_user["role"] == "owner" and pet_resp.data[0]["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = VaccineService.get_pet_vaccine_documents(pet_id=pet_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result

@router.post("/vaccines/check-reminders")
async def check_vaccine_reminders(current_user: dict = Depends(get_current_user)):
    """Trigger reminder check for all vaccines (Admin only)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
        
    result = VaccineService.check_and_send_reminders()
    return result

# ============================================
# Medical Records Endpoints
# ============================================

@router.post("/medical-records")
async def create_medical_record(
    clinic_id: str,
    pet_id: str,
    record_type: str,
    visit_date: str,
    diagnosis: Optional[str] = None,
    treatment: Optional[str] = None,
    notes: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Create medical record (Clinics only)"""
    if current_user["role"] != "clinic":
        raise HTTPException(status_code=403, detail="Only clinics can create medical records")

    # Check if the clinic owns this clinic_id
    clinic_resp = supabase.table("clinics").select("id").eq("user_id", current_user["id"]).execute()
    if not clinic_resp.data or clinic_resp.data[0]["id"] != clinic_id:
        raise HTTPException(status_code=403, detail="Access denied. Invalid clinic identity.")

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
        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to create medical record")

        return {
            "success": True,
            "record_id": response.data[0]["id"],
            "message": "Medical record created successfully!"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/pet/medical-records")
async def get_pet_medical_records(pet_id: str, current_user: dict = Depends(get_current_user)):
    """Get all medical records for a pet"""
    pet_resp = supabase.table("pets").select("user_id").eq("id", pet_id).execute()
    if not pet_resp.data:
        raise HTTPException(status_code=404, detail="Pet not found")
    if current_user["role"] == "owner" and pet_resp.data[0]["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        response = supabase.table("medical_records").select("*").eq("pet_id", pet_id).execute()
        return {
            "success": True,
            "records": response.data or [],
            "count": len(response.data or [])
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
