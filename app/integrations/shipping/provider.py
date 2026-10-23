from typing import Dict, Any
from app.common.utils import generate_tracking_number

class ShippingProvider:
    def create_shipment(self, order_id: int, carrier: str = "Standard Express") -> Dict[str, Any]:
        tracking_number = generate_tracking_number(carrier[:3])
        return {
            "tracking_number": tracking_number,
            "carrier": carrier,
            "label_url": f"https://shipping.shopspherepro.com/labels/{tracking_number}.pdf",
            "estimated_delivery_days": 3
        }

shipping_provider = ShippingProvider()
