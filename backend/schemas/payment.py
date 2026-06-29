from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CreateCheckoutSessionRequest(BaseModel):
    appointment_id: str = Field(..., description="The UUID of the appointment to pay for")

class CheckoutSessionResponse(BaseModel):
    checkout_url: str = Field(..., description="Stripe Checkout hosted URL to redirect the user to")
    session_id: str = Field(..., description="Stripe Session ID for tracking")

class RefundRequest(BaseModel):
    payment_id: str = Field(..., description="Internal payment UUID or Stripe Payment Intent ID")
    amount: Optional[int] = Field(None, description="Amount to refund in cents. If None, refunds the full amount.")
    reason: Optional[str] = Field("requested_by_customer", description="Reason for refund")

class PaymentHistoryResponse(BaseModel):
    id: str
    appointment_id: str
    stripe_session_id: Optional[str]
    payment_intent_id: Optional[str]
    amount: float
    currency: str
    status: str
    receipt_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
