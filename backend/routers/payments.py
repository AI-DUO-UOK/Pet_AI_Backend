"""
payments.py — Payment API Router (PetPULSE)

This router contains stub endpoints for the Stripe payment integration.
All endpoints are ready to be implemented — just follow the TODO comments.

Prerequisites when ready to implement:
    pip install stripe

Environment variables required (add to .env):
    STRIPE_SECRET_KEY=sk_live_...         (or sk_test_... for testing)
    STRIPE_WEBHOOK_SECRET=whsec_...       (from Stripe Dashboard → Webhooks)
    STRIPE_SUCCESS_URL=https://your-domain.com/payment/success?session_id={CHECKOUT_SESSION_ID}
    STRIPE_CANCEL_URL=https://your-domain.com/payment/cancel

Stripe Dashboard Setup:
    1. https://dashboard.stripe.com/products → Create product "PetPULSE Appointment"
    2. https://dashboard.stripe.com/webhooks → Add endpoint for POST /api/payments/webhook
       Listen to: checkout.session.completed, payment_intent.payment_failed

Related frontend file:
    lib/payment.ts → createCheckoutSession() placeholder
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel

from backend.core.dependencies import get_current_user
from backend.services.appointment_service import AppointmentService

import stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Payments"])


# ──────────────────────────────────────────────
# Request / Response Schemas
# ──────────────────────────────────────────────

class CreateCheckoutSessionRequest(BaseModel):
    """
    Payload sent by the frontend when the user clicks "Pay Securely".
    Mirrors CheckoutPayload in lib/payment.ts.
    """
    clinic_id: str
    clinic_name: str
    pet_id: str
    pet_name: str
    owner_id: str
    service_name: str
    consultation_fee: int          # LKR, integer (e.g. 2500)
    platform_fee: int              # LKR, integer (e.g. 150)
    tax: int                       # LKR, integer (0 for now)
    total_amount: int              # LKR, integer (e.g. 2650)
    appointment_date: str          # ISO date "2026-07-15"
    appointment_time: str          # "10:30"
    notes: Optional[str] = None
    doctor_name: Optional[str] = None


class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: Optional[str] = None


# ──────────────────────────────────────────────
# POST /api/payments/create-checkout-session
# ──────────────────────────────────────────────

@router.post("/payments/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CreateCheckoutSessionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a Stripe Hosted Checkout Session for an appointment booking.

    Frontend calls this when the user clicks "Pay Securely".
    On success, returns a { checkout_url } that the frontend should
    redirect to: window.location.href = checkout_url

    TODO Implementation Steps:
    ──────────────────────────
    1. Validate the request (owner matches current_user, pet belongs to owner)
    2. Create a Stripe checkout session:

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "lkr",
                    "unit_amount": request.total_amount * 100,  # Stripe uses cents
                    "product_data": {
                        "name": f"PetPULSE — {request.service_name}",
                        "description": (
                            f"Clinic: {request.clinic_name} | "
                            f"Pet: {request.pet_name} | "
                            f"Date: {request.appointment_date} {request.appointment_time}"
                        ),
                    },
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=os.getenv("STRIPE_SUCCESS_URL"),
            cancel_url=os.getenv("STRIPE_CANCEL_URL"),
            metadata={
                "clinic_id": request.clinic_id,
                "pet_id": request.pet_id,
                "owner_id": request.owner_id,
                "service_name": request.service_name,
                "appointment_date": request.appointment_date,
                "appointment_time": request.appointment_time,
                "notes": request.notes or "",
                "doctor_name": request.doctor_name or "",
            }
        )

    3. Store a pending payment record in Supabase:

        supabase.table("payments").insert({
            "stripe_session_id": session.id,
            "owner_id": request.owner_id,
            "clinic_id": request.clinic_id,
            "pet_id": request.pet_id,
            "amount": request.total_amount,
            "status": "pending",
        }).execute()

    4. Return the checkout URL:
        return { "checkout_url": session.url, "session_id": session.id }
    """

    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if stripe_key:
        try:
            stripe.api_key = stripe_key
            
            # Setup success URL with pet_id so frontend knows where to redirect
            success_url = os.getenv("STRIPE_SUCCESS_URL")
            if "?" in success_url:
                success_url += f"&pet_id={request.pet_id}"
            else:
                success_url += f"?pet_id={request.pet_id}"

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "lkr",
                        "unit_amount": request.total_amount * 100,  # Stripe uses cents
                        "product_data": {
                            "name": f"PetPULSE — {request.service_name}",
                            "description": (
                                f"Clinic: {request.clinic_name} | "
                                f"Pet: {request.pet_name} | "
                                f"Date: {request.appointment_date} {request.appointment_time}"
                            ),
                        },
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=success_url,
                cancel_url=os.getenv("STRIPE_CANCEL_URL"),
                metadata={
                    "clinic_id": request.clinic_id,
                    "pet_id": request.pet_id,
                    "owner_id": request.owner_id,
                    "service_name": request.service_name,
                    "appointment_date": request.appointment_date,
                    "appointment_time": request.appointment_time,
                    "notes": request.notes or "",
                    "doctor_name": request.doctor_name or "",
                }
            )

            return CheckoutSessionResponse(
                checkout_url=session.url,
                session_id=session.id
            )
        except Exception as stripe_err:
            logger.error(f"Stripe session creation failed: {stripe_err}")
            raise HTTPException(status_code=400, detail=f"Stripe error: {str(stripe_err)}")
    else:
        # Fallback to local mock flow
        # In development/test mode, we immediately create the appointment to make it show up in the database,
        # which automatically triggers the notification system and lists it in "Upcoming Appointments".
        appt_result = AppointmentService.create_appointment(
            pet_id=request.pet_id,
            clinic_id=request.clinic_id,
            owner_id=request.owner_id,
            appointment_date=request.appointment_date,
            appointment_time=request.appointment_time,
            reason=request.service_name,
            notes=request.notes,
        )

        if not appt_result["success"]:
            raise HTTPException(
                status_code=400,
                detail=appt_result.get("error", "Failed to create appointment in development mode")
            )

        # In production, this would be generated by Stripe. We pass pet_id so the success page can redirect back.
        mock_session_id = f"mock_cs_{request.owner_id[:8]}_{request.clinic_id[:8]}"
        return CheckoutSessionResponse(
            checkout_url=f"/payment/success?session_id={mock_session_id}&pet_id={request.pet_id}",
            session_id=mock_session_id
        )


# ──────────────────────────────────────────────
# POST /api/payments/webhook
# ──────────────────────────────────────────────

@router.post("/payments/webhook")
async def stripe_webhook(
    raw_request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature")
):
    """
    Stripe webhook endpoint — receives events after payment completion.
    """
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    if not stripe_key:
        return {"status": "ignored", "reason": "Stripe not configured"}

    payload = await raw_request.body()

    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, webhook_secret
        )
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})

        # Create the appointment in the database using the same AppointmentService!
        logger.info(f"Webhook received: Payment completed for session {session['id']}")
        
        appt_result = AppointmentService.create_appointment(
            pet_id=metadata.get("pet_id"),
            clinic_id=metadata.get("clinic_id"),
            owner_id=metadata.get("owner_id"),
            appointment_date=metadata.get("appointment_date"),
            appointment_time=metadata.get("appointment_time"),
            reason=metadata.get("service_name"),
            notes=metadata.get("notes"),
        )
        
        if not appt_result["success"]:
            logger.error(f"Failed to create appointment via webhook: {appt_result.get('error')}")
            return {"status": "error", "message": appt_result.get("error")}

        logger.info(f"Appointment created successfully via webhook: {appt_result['appointment_id']}")

    return {"status": "success"}


# ──────────────────────────────────────────────
# GET /api/payments/{payment_id}
# ──────────────────────────────────────────────

@router.get("/payments/{payment_id}")
async def get_payment(
    payment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve a single payment record by ID.

    TODO:
        result = supabase.table("payments")
            .select("*, appointments(*)")
            .eq("id", payment_id)
            .single()
            .execute()

        # Check authorization: payment must belong to current_user
        if result.data["owner_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        return result.data
    """
    raise HTTPException(status_code=501, detail="Not yet implemented")


# ──────────────────────────────────────────────
# GET /api/payments/history
# ──────────────────────────────────────────────

@router.get("/payments/history")
async def get_payment_history(
    current_user: dict = Depends(get_current_user)
):
    """
    List all payment records for the currently authenticated owner.

    TODO:
        result = supabase.table("payments")
            .select("*, appointments(pet_id, clinic_id, appointment_date, reason)")
            .eq("owner_id", current_user["id"])
            .order("created_at", desc=True)
            .execute()
        return {"payments": result.data}
    """
    raise HTTPException(status_code=501, detail="Not yet implemented")


# ──────────────────────────────────────────────
# GET /api/payments/{payment_id}/receipt
# ──────────────────────────────────────────────

@router.get("/payments/{payment_id}/receipt")
async def download_receipt(
    payment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate and return a PDF receipt for a completed payment.

    TODO:
        1. Fetch payment + appointment details from Supabase
        2. Generate PDF using reportlab or weasyprint:
               pip install reportlab
        3. Return as StreamingResponse with Content-Type: application/pdf

        from fastapi.responses import StreamingResponse
        import io

        pdf_buffer = io.BytesIO()
        # ... generate PDF ...
        pdf_buffer.seek(0)

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=receipt_{payment_id}.pdf"}
        )
    """
    raise HTTPException(status_code=501, detail="Not yet implemented")
