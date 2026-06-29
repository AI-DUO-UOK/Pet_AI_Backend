from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from typing import List, Dict
import logging
from backend.core.dependencies import get_current_user
from backend.schemas.payment import CreateCheckoutSessionRequest, CheckoutSessionResponse, RefundRequest, PaymentHistoryResponse
from backend.services.stripe_service import StripeService
from chatbot.supabase_config import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["payments"])

@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CreateCheckoutSessionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Validates the appointment and creates a Stripe Checkout Session.
    Only the pet owner who owns the appointment can pay.
    """
    appointment_id = request.appointment_id
    
    # 1. Fetch appointment details
    appt_resp = supabase.table("appointments").select("*, clinics(clinic_name)").eq("id", appointment_id).execute()
    if not appt_resp.data:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    appointment = appt_resp.data[0]
    
    # 2. Authorization: Only the owner can pay
    if appointment.get("owner_id") != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to pay for this appointment"
        )
        
    # 3. Check if already paid
    if appointment.get("status") == "paid":
        raise HTTPException(status_code=400, detail="This appointment has already been paid")

    # 4. Calculate amount (using mock LKR 3,996.00 = 399600 cents)
    # TODO: In production, fetch the actual price based on the clinic's service cost
    amount_cents = 399600 
    clinic_name = appointment.get("clinics", {}).get("clinic_name", "Pet Clinic")

    try:
        # 5. Create checkout session
        session_info = StripeService.create_checkout_session(
            appointment_id=appointment_id,
            amount_lkr=amount_cents,
            clinic_name=clinic_name,
            customer_email=current_user.get("email")
        )
        
        # 6. Log pending transaction
        supabase.table("payments").insert({
            "appointment_id": appointment_id,
            "stripe_session_id": session_info["session_id"],
            "amount": amount_cents / 100.0,
            "currency": "LKR",
            "status": "pending"
        }).execute()
        
        return session_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    """
    Webhook endpoint for Stripe events.
    Verifies signature and updates appointment and payment statuses in Supabase.
    """
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")
        
    payload = await request.body()
    try:
        event = StripeService.verify_webhook(payload, stripe_signature)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    event_type = event["type"]
    logger.info(f"Received Stripe Webhook Event: {event_type}")

    # Handle completed checkout session
    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        appointment_id = session.get("metadata", {}).get("appointment_id")
        payment_intent_id = session.get("payment_intent")
        
        if appointment_id:
            # Update payments record and get the updated row
            pay_resp = supabase.table("payments").update({
                "status": "paid",
                "payment_intent_id": payment_intent_id
            }).eq("stripe_session_id", session.get("id")).execute()

            # Update appointment status
            supabase.table("appointments").update({
                "status": "paid"
            }).eq("id", appointment_id).execute()
            
            # Generate invoice/receipt URL
            if pay_resp.data:
                payment_id = pay_resp.data[0]["id"]
                from backend.utils.receipt import ReceiptGenerator
                await ReceiptGenerator.create_and_upload_receipt(payment_id)

    elif event_type == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        payment_intent_id = payment_intent.get("id")
        
        # Update payments record to failed
        supabase.table("payments").update({
            "status": "failed"
        }).eq("payment_intent_id", payment_intent_id).execute()

    return {"status": "success"}


@router.get("/history", response_model=List[PaymentHistoryResponse])
async def get_payment_history(current_user: dict = Depends(get_current_user)):
    """
    Returns payment history.
    Pet Owners see their own payments.
    Admins can see all payments.
    """
    role = current_user.get("role")
    
    if role == "admin":
        # Admin gets all payments
        resp = supabase.table("payments").select("*").order("created_at", desc=True).execute()
    elif role == "owner":
        # Owner gets payments linked to their appointments
        resp = supabase.table("payments").select(
            "*, appointments!inner(owner_id)"
        ).eq("appointments.owner_id", current_user["id"]).order("created_at", desc=True).execute()
    else:
        raise HTTPException(status_code=403, detail="Clinics do not have payment history")

    return resp.data or []


@router.get("/{payment_id}", response_model=PaymentHistoryResponse)
async def get_payment_details(payment_id: str, current_user: dict = Depends(get_current_user)):
    """
    Retrieves details for a specific payment.
    """
    resp = supabase.table("payments").select("*, appointments!inner(owner_id)").eq("id", payment_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Payment not found")
        
    payment = resp.data[0]
    
    # Auth check: Owner can only view their own payment details
    if current_user.get("role") != "admin" and payment["appointments"]["owner_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Unauthorized to view this payment")
        
    return payment


@router.post("/refund")
async def refund_payment(request: RefundRequest, current_user: dict = Depends(get_current_user)):
    """
    Refunds a payment. Only accessible by Admins.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only administrators can issue refunds")
        
    payment_id = request.payment_id
    
    # Fetch payment record
    pay_resp = supabase.table("payments").select("*").eq("id", payment_id).execute()
    if not pay_resp.data:
        # Fallback check by Stripe Payment Intent ID
        pay_resp = supabase.table("payments").select("*").eq("payment_intent_id", payment_id).execute()
        
    if not pay_resp.data:
        raise HTTPException(status_code=404, detail="Payment record not found")
        
    payment = pay_resp.data[0]
    
    if payment["status"] != "paid":
        raise HTTPException(status_code=400, detail="Only paid transactions can be refunded")
        
    try:
        # Process refund via Stripe
        refund_info = StripeService.create_refund(
            payment_intent_id=payment["payment_intent_id"],
            amount_cents=request.amount
        )
        
        # Update payment record
        supabase.table("payments").update({
            "status": "refunded"
        }).eq("id", payment["id"]).execute()
        
        # Update appointment record
        supabase.table("appointments").update({
            "status": "refunded"
        }).eq("id", payment["appointment_id"]).execute()
        
        return {
            "success": True,
            "message": "Refund processed successfully",
            **refund_info
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
