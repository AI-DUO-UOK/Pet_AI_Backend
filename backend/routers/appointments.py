from fastapi import APIRouter, Depends, HTTPException, status, Form
from typing import Optional
import logging
from backend.core.dependencies import get_current_user
from backend.schemas.schemas import CreateAppointmentRequest, CreateReviewRequest
from backend.services.appointment_service import AppointmentService
from backend.core.supabase_config import supabase

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Appointments & Reviews"])

@router.post("/appointments")
async def create_appointment(
    request: CreateAppointmentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new appointment"""
    logger.info(f"Creating appointment for pet {request.pet_id} by user: {current_user['id']}")
    
    # Check authorization: If owner, must be the owner of the pet
    if current_user["role"] == "owner":
        pet_resp = supabase.table("pets").select("user_id").eq("id", request.pet_id).execute()
        if not pet_resp.data or pet_resp.data[0]["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="You can only schedule appointments for your own pets")

    result = AppointmentService.create_appointment(
        pet_id=request.pet_id,
        clinic_id=request.clinic_id,
        owner_id=current_user["id"] if current_user["role"] == "owner" else request.owner_id,
        appointment_date=request.appointment_date,
        appointment_time=request.appointment_time,
        reason=request.reason,
        notes=request.notes,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
        
    return result

@router.get("/appointments/owner")
async def get_owner_appointments(
    owner_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get appointments for a pet owner"""
    target_owner_id = owner_id or current_user["id"]
    
    # Check authorization: Owners can only view their own appointments
    if current_user["role"] == "owner" and target_owner_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = AppointmentService.get_owner_appointments(owner_id=target_owner_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
        
    return result

@router.get("/appointments/clinic")
async def get_clinic_appointments(
    clinic_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get appointments for a clinic"""
    # Check authorization: Clinics can only view their own appointments
    if current_user["role"] == "clinic":
        # Get the clinic's ID from user_id
        clinic_resp = supabase.table("clinics").select("id").eq("user_id", current_user["id"]).execute()
        if not clinic_resp.data or clinic_resp.data[0]["id"] != clinic_id:
            raise HTTPException(status_code=403, detail="Access denied")

    result = AppointmentService.get_clinic_appointments(clinic_id=clinic_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
        
    return result

@router.get("/appointments/pet")
async def get_pet_appointments(
    pet_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all appointments for a pet"""
    # Check authorization: Owners can only view appointments for their own pets
    if current_user["role"] == "owner":
        pet_resp = supabase.table("pets").select("user_id").eq("id", pet_id).execute()
        if not pet_resp.data or pet_resp.data[0]["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

    result = AppointmentService.get_pet_appointments(pet_id=pet_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
        
    return result

@router.post("/appointments/{appointment_id}/status")
async def update_appointment_status(
    appointment_id: str,
    status: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """Update status of an appointment"""
    # Validate status
    valid_statuses = {"scheduled", "completed", "cancelled", "in_progress"}
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status value")

    # Check authorization
    appt_resp = supabase.table("appointments").select("owner_id", "clinic_id").eq("id", appointment_id).execute()
    if not appt_resp.data:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    appt = appt_resp.data[0]
    
    if current_user["role"] == "owner":
        if appt["owner_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        if status != "cancelled":
            raise HTTPException(status_code=403, detail="Owners can only cancel appointments")
    elif current_user["role"] == "clinic":
        clinic_resp = supabase.table("clinics").select("id").eq("user_id", current_user["id"]).execute()
        if not clinic_resp.data or clinic_resp.data[0]["id"] != appt["clinic_id"]:
            raise HTTPException(status_code=403, detail="Access denied")

    result = AppointmentService.update_appointment_status(appointment_id=appointment_id, status=status)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
        
    return result

@router.post("/reviews")
async def create_review(
    request: CreateReviewRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a clinic review for a completed appointment"""
    if current_user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Only pet owners can review clinics")

    # Check authorization: Must be the owner of the appointment
    appt_resp = supabase.table("appointments").select("owner_id").eq("id", request.appointment_id).execute()
    if not appt_resp.data:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    if appt_resp.data[0]["owner_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = AppointmentService.create_review(
        appointment_id=request.appointment_id,
        rating=request.rating,
        treatment=request.treatment,
        comment=request.comment
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
        
    return result

@router.get("/reviews/clinic")
async def get_reviews_for_clinic(
    clinic_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all reviews for a clinic"""
    result = AppointmentService.get_reviews_for_clinic(clinic_id=clinic_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
        
    return result
