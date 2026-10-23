from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class PaymentGateway(ABC):
    @abstractmethod
    def create_payment_intent(self, amount: float, currency: str = "usd", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def confirm_payment(self, payment_intent_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def create_refund(self, charge_or_intent_id: str, amount: float, reason: Optional[str] = None) -> Dict[str, Any]:
        pass
