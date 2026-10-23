import uuid
import random
import string
from datetime import datetime, timezone

def generate_order_number() -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_str = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"ORD-{now}-{random_str}"

def generate_tracking_number(carrier: str = "SPP") -> str:
    now = datetime.now(timezone.utc).strftime("%y%m%d")
    random_str = "".join(random.choices(string.digits, k=8))
    return f"{carrier[:3].upper()}{now}{random_str}"

def generate_invoice_number() -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m")
    random_str = "".join(random.choices(string.digits, k=5))
    return f"INV-{now}-{random_str}"

def generate_sku(prefix: str = "SKU") -> str:
    random_str = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"{prefix.upper()}-{random_str}"
