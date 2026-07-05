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
from datetime import datetime
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

    # Issue 3: Security Validation
    if current_user["id"] != request.owner_id and current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Unauthorized: You can only create checkout sessions for yourself"
        )

    # Import Supabase client
    from backend.core.supabase_config import supabase

    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if stripe_key:
        try:
            stripe.api_key = stripe_key
            
            # 1. Pre-create the appointment as "pending" in the database
            # This is required because payments table has a NOT NULL foreign key constraint on appointment_id.
            appt_data = {
                "pet_id": request.pet_id,
                "clinic_id": request.clinic_id,
                "owner_id": request.owner_id,
                "appointment_date": request.appointment_date,
                "appointment_time": request.appointment_time,
                "reason": request.service_name,
                "notes": request.notes,
                "status": "pending"  # Created as pending; will be confirmed via webhook upon payment
            }
            appt_resp = supabase.table("appointments").insert(appt_data).execute()
            if not appt_resp.data:
                raise HTTPException(status_code=500, detail="Failed to create pending appointment")
            
            created_appt = appt_resp.data[0]
            appt_id = created_appt["id"]

            # Setup success URL with pet_id so frontend knows where to redirect
            success_url = os.getenv("STRIPE_SUCCESS_URL")
            cancel_url = os.getenv("STRIPE_CANCEL_URL")
            if not success_url or not cancel_url:
                raise HTTPException(
                    status_code=500,
                    detail="Stripe environment variables (STRIPE_SUCCESS_URL or STRIPE_CANCEL_URL) are not configured"
                )

            if "?" in success_url:
                success_url += f"&pet_id={request.pet_id}"
            else:
                success_url += f"?pet_id={request.pet_id}"

            # 2. Create Stripe checkout session
            # LKR uses 2 decimal places in Stripe (cents), so multiplying by 100 is correct.
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "lkr",
                        "unit_amount": int(request.total_amount * 100),
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
                cancel_url=cancel_url,
                metadata={
                    "appointment_id": appt_id,
                    "clinic_id": request.clinic_id,
                    "pet_id": request.pet_id,
                    "owner_id": request.owner_id,
                    "service_name": request.service_name,
                }
            )

            # 3. Store a pending payment record in Supabase (Issue 4)
            payment_data = {
                "appointment_id": appt_id,
                "stripe_session_id": session.id,
                "amount": request.total_amount,
                "currency": "LKR",
                "status": "pending"
            }
            payment_resp = supabase.table("payments").insert(payment_data).execute()
            if not payment_resp.data:
                raise HTTPException(status_code=500, detail="Failed to create payment record")

            return CheckoutSessionResponse(
                checkout_url=session.url,
                session_id=session.id
            )
        except HTTPException:
            raise
        except Exception as stripe_err:
            logger.exception("Stripe session creation failed")
            raise HTTPException(status_code=400, detail=f"Stripe error: {str(stripe_err)}")
    else:
        # Fallback to local mock flow (Development Fallback)
        # 1. Immediately create the appointment as "scheduled"
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

        appt_id = appt_result["appointment_id"]
        mock_session_id = f"mock_cs_{request.owner_id[:8]}_{request.clinic_id[:8]}"

        # 2. Store a paid payment record in Supabase for consistency
        payment_data = {
            "appointment_id": appt_id,
            "stripe_session_id": mock_session_id,
            "amount": request.total_amount,
            "currency": "LKR",
            "status": "paid"
        }
        supabase.table("payments").insert(payment_data).execute()

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

    # Import Supabase client
    from backend.core.supabase_config import supabase

    payload = await raw_request.body()

    try:
        # Issue 5: Catch signature verification and value errors separately
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, webhook_secret
        )
    except stripe.error.SignatureVerificationError as sig_err:
        logger.error(f"Webhook signature verification failed: {sig_err}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except ValueError as val_err:
        logger.error(f"Webhook payload parsing failed: {val_err}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except Exception as e:
        logger.error(f"Unexpected webhook error: {e}")
        raise HTTPException(status_code=400, detail="Webhook error")

    # Issue 7: Duplicate Webhook Protection & Issue 6: Saving Payment Status
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        appt_id = metadata.get("appointment_id")

        logger.info(f"Webhook received: Payment completed for session {session['id']}")

        # Retrieve the payment record
        pay_resp = supabase.table("payments").select("*").eq("stripe_session_id", session["id"]).execute()
        if not pay_resp.data:
            logger.error(f"Payment record not found for session: {session['id']}")
            return {"status": "error", "message": "Payment record not found"}

        payment = pay_resp.data[0]

        # Duplicate Webhook Check
        if payment["status"] == "paid":
            logger.info(f"Webhook already processed for session: {session['id']}")
            return {"status": "success", "message": "Already processed"}

        # Update payment record status and details (Issue 6)
        payment_intent_id = session.get("payment_intent")
        
        # Fetch receipt URL if available
        receipt_url = None
        if payment_intent_id:
            try:
                pi = stripe.PaymentIntent.retrieve(payment_intent_id)
                if pi.charges and pi.charges.data:
                    receipt_url = pi.charges.data[0].receipt_url
            except Exception as pi_err:
                logger.warning(f"Failed to fetch receipt URL: {pi_err}")

        supabase.table("payments").update({
            "status": "paid",
            "payment_intent_id": payment_intent_id,
            "receipt_url": receipt_url,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", payment["id"]).execute()

        # Confirm the appointment (update status from pending to scheduled)
        supabase.table("appointments").update({
            "status": "scheduled",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", appt_id).execute()

        # Trigger notifications for the scheduled appointment
        try:
            appt_resp = supabase.table("appointments").select("*").eq("id", appt_id).execute()
            if appt_resp.data:
                AppointmentService._send_appointment_notifications(appt_resp.data[0])
                logger.info(f"Notifications sent for appointment: {appt_id}")
        except Exception as notif_err:
            logger.error(f"Failed to send notifications: {notif_err}")

        logger.info(f"Appointment {appt_id} confirmed and marked paid successfully via webhook")

    # Issue 8: Handle payment failure
    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        logger.warning(f"Webhook received: Payment failed for intent {payment_intent['id']}")

        # Find the payment record by payment_intent_id or lookup via metadata
        pay_resp = supabase.table("payments").select("*").eq("payment_intent_id", payment_intent["id"]).execute()
        if not pay_resp.data:
            # Try to find by session metadata if payment_intent_id wasn't saved yet
            # In most cases, we can find it by querying appointments or sessions
            pass
        else:
            payment = pay_resp.data[0]
            appt_id = payment["appointment_id"]

            # Update payment record to failed
            supabase.table("payments").update({
                "status": "failed",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", payment["id"]).execute()

            # Cancel/Fail the pending appointment
            supabase.table("appointments").update({
                "status": "cancelled",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", appt_id).execute()

            logger.warning(f"Appointment {appt_id} and Payment {payment['id']} marked as failed/cancelled")

    # Issue 10: Handle checkout session expiration (abandoned payments)
    elif event["type"] == "checkout.session.expired":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        appt_id = metadata.get("appointment_id")
        
        logger.info(f"Webhook received: Checkout session expired for session {session['id']}")
        
        # Update payment record to expired
        supabase.table("payments").update({
            "status": "expired",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("stripe_session_id", session["id"]).execute()

        # Cancel the pending appointment
        if appt_id:
            supabase.table("appointments").update({
                "status": "cancelled",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", appt_id).execute()

            logger.info(f"Appointment {appt_id} marked as cancelled due to expired session")

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
    """
    from backend.core.supabase_config import supabase

    result = supabase.table("payments").select("*, appointments(*)").eq("id", payment_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Payment record not found")

    payment = result.data[0]
    appointment = payment.get("appointments")

    # Check authorization: payment must belong to current_user
    if appointment and appointment.get("owner_id") != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    return payment


# ──────────────────────────────────────────────
# GET /api/payments/history
# ──────────────────────────────────────────────

@router.get("/payments/history")
async def get_payment_history(
    current_user: dict = Depends(get_current_user)
):
    """
    List all payment records for the currently authenticated owner.
    """
    from backend.core.supabase_config import supabase

    # Fetch appointments for this owner first
    appt_resp = supabase.table("appointments").select("id").eq("owner_id", current_user["id"]).execute()
    if not appt_resp.data:
        return {"payments": []}

    appt_ids = [appt["id"] for appt in appt_resp.data]

    # Fetch payments referencing those appointments
    result = supabase.table("payments").select("*, appointments(pet_id, clinic_id, appointment_date, reason)").in_("appointment_id", appt_ids).order("created_at", desc=True).execute()
    return {"payments": result.data or []}


# ──────────────────────────────────────────────
# GET /api/payments/{payment_id}/receipt
# ──────────────────────────────────────────────

@router.get("/payments/{payment_id}/receipt")
async def download_receipt(
    payment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate and return a PDF receipt or redirect to Stripe's receipt URL.
    """
    from backend.core.supabase_config import supabase
    from fastapi.responses import RedirectResponse

    result = supabase.table("payments").select("*").eq("id", payment_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Payment record not found")

    payment = result.data[0]
    if payment.get("receipt_url"):
        return RedirectResponse(url=payment["receipt_url"])
    
    # Fallback to text file receipt generation if no Stripe receipt URL exists (e.g. mock payments)
    raise HTTPException(status_code=501, detail="Receipt download is only available for Stripe payments. Use the frontend receipt generator for mock payments.")
