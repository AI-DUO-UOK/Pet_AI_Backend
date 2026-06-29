import os
import stripe
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Initialize Stripe with Secret Key
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

class StripeService:
    @staticmethod
    def create_checkout_session(
        appointment_id: str, 
        amount_lkr: int, 
        clinic_name: str,
        customer_email: Optional[str] = None
    ) -> Dict:
        """
        Creates a Stripe Checkout Session for an appointment.
        amount_lkr: Amount in cents (e.g., LKR 3,996.00 is 399600)
        """
        try:
            session_data = {
                "payment_method_types": ["card"],
                "line_items": [{
                    "price_data": {
                        "currency": "lkr",
                        "product_data": {
                            "name": f"Veterinary Appointment - {clinic_name}",
                            "description": f"Appointment ID: {appointment_id}",
                        },
                        "unit_amount": amount_lkr,
                    },
                    "quantity": 1,
                }],
                "mode": "payment",
                "success_url": f"{FRONTEND_URL}/appointments/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
                "cancel_url": f"{FRONTEND_URL}/appointments/checkout/cancelled",
                "metadata": {
                    "appointment_id": appointment_id
                }
            }

            if customer_email:
                session_data["customer_email"] = customer_email

            session = stripe.checkout.Session.create(**session_data)
            return {
                "checkout_url": session.url,
                "session_id": session.id
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe Session Creation Error: {str(e)}")
            raise ValueError(f"Stripe error: {e.user_message or str(e)}")

    @staticmethod
    def verify_webhook(payload: bytes, sig_header: str) -> stripe.Event:
        """
        Verifies the Stripe Webhook signature to ensure the request came from Stripe.
        """
        if not STRIPE_WEBHOOK_SECRET:
            raise ValueError("STRIPE_WEBHOOK_SECRET is not set in environment variables.")
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
            return event
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid Stripe Webhook Signature: {str(e)}")
            raise ValueError("Invalid webhook signature.")
        except Exception as e:
            logger.error(f"Webhook parsing error: {str(e)}")
            raise ValueError(f"Error parsing webhook: {str(e)}")

    @staticmethod
    def create_refund(payment_intent_id: str, amount_cents: Optional[int] = None) -> Dict:
        """
        Refunds a completed payment intent.
        """
        try:
            refund_data = {"payment_intent": payment_intent_id}
            if amount_cents:
                refund_data["amount"] = amount_cents

            refund = stripe.Refund.create(**refund_data)
            return {
                "refund_id": refund.id,
                "status": refund.status,
                "amount": refund.amount
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe Refund Error: {str(e)}")
            raise ValueError(f"Refund failed: {e.user_message or str(e)}")
