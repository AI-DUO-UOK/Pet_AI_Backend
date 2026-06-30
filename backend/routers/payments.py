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

# TODO: Uncomment when stripe is installed
# import stripe
# stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

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

    # TODO: Remove this stub and implement the real Stripe flow above.
    logger.info(
        f"[STUB] create_checkout_session called — "
        f"owner={current_user['id']}, service={request.service_name}, "
        f"total=LKR {request.total_amount}"
    )

    raise HTTPException(
        status_code=501,
        detail=(
            "Payment checkout not yet implemented. "
            "See TODO comments in backend/routers/payments.py"
        )
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

    Configure in Stripe Dashboard:
        https://dashboard.stripe.com/webhooks → Add endpoint
        URL: https://your-domain.com/api/payments/webhook
        Events: checkout.session.completed, payment_intent.payment_failed

    TODO Implementation Steps:
    ──────────────────────────
    1. Read raw body (IMPORTANT: must be raw bytes for signature verification)

        payload = await raw_request.body()

    2. Verify Stripe signature:

        try:
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, os.getenv("STRIPE_WEBHOOK_SECRET")
            )
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")

    3. Handle checkout.session.completed:

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            metadata = session.get("metadata", {})

            # a) Create the appointment in Supabase
            supabase.table("appointments").insert({
                "pet_id": metadata["pet_id"],
                "clinic_id": metadata["clinic_id"],
                "owner_id": metadata["owner_id"],
                "appointment_date": metadata["appointment_date"],
                "appointment_time": metadata["appointment_time"],
                "reason": metadata["service_name"],
                "notes": metadata.get("notes"),
                "status": "confirmed",
            }).execute()

            # b) Update payment record to paid
            supabase.table("payments").update({
                "status": "paid",
                "stripe_payment_intent": session.get("payment_intent"),
            }).eq("stripe_session_id", session["id"]).execute()

            # c) Send confirmation notification / email
            # TODO: Trigger email via SendGrid / Supabase Edge Function

    4. Handle payment_intent.payment_failed similarly.
    """

    logger.info("[STUB] Stripe webhook received — not yet implemented")

    # TODO: Remove this stub and implement the real webhook handler above.
    return {"received": True, "status": "stub"}


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
