from pydantic import BaseModel, Field
from typing import Optional, List

class RegisterOwnerRequest(BaseModel):
    first_name: str
    last_name: str
    phone: str
    address: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    bio: Optional[str] = None

class RegisterClinicRequest(BaseModel):
    clinic_name: str
    phone: str
    address: str
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    opening_hours: Optional[str] = None
    description: Optional[str] = None
    clinic_logo_url: Optional[str] = None
    license_document_url: Optional[str] = None

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
    appointment_date: str
    appointment_time: str
    reason: Optional[str] = None
    notes: Optional[str] = None

class CreateReviewRequest(BaseModel):
    appointment_id: str
    rating: int = Field(..., ge=1, le=5)
    treatment: str = Field(..., max_length=100)
    comment: Optional[str] = None
