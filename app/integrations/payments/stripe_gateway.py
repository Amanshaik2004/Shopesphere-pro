import uuid
from typing import Dict, Any, Optional
from app.integrations.payments.base import PaymentGateway
from app.core.config import settings
from app.core.logging import logger

class StripeGateway(PaymentGateway):
    def __init__(self):
        self.api_key = settings.STRIPE_SECRET_KEY
        self.is_sandbox = not self.api_key.startswith("sk_live_")

    def create_payment_intent(self, amount: float, currency: str = "usd", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        amount_cents = int(amount * 100)
        logger.info(f"Creating Stripe PaymentIntent for amount: {amount} {currency}")
        intent_id = f"pi_mock_{uuid.uuid4().hex[:16]}"
        client_secret = f"{intent_id}_secret_{uuid.uuid4().hex[:12]}"
        return {
            "id": intent_id,
            "amount": amount,
            "currency": currency,
            "status": "requires_payment_method",
            "client_secret": client_secret,
            "metadata": metadata or {}
        }

    def confirm_payment(self, payment_intent_id: str) -> Dict[str, Any]:
        logger.info(f"Confirming payment intent: {payment_intent_id}")
        return {
            "id": payment_intent_id,
            "status": "succeeded",
            "charge_id": f"ch_mock_{uuid.uuid4().hex[:16]}",
            "amount_received": 100
        }

    def create_refund(self, charge_or_intent_id: str, amount: float, reason: Optional[str] = None) -> Dict[str, Any]:
        logger.info(f"Refunding Stripe charge/intent: {charge_or_intent_id} for amount: {amount}")
        refund_id = f"re_mock_{uuid.uuid4().hex[:16]}"
        return {
            "id": refund_id,
            "payment_intent": charge_or_intent_id,
            "amount": amount,
            "status": "succeeded",
            "reason": reason or "requested_by_customer"
        }

stripe_gateway = StripeGateway()
