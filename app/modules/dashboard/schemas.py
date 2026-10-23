from typing import Dict
from pydantic import BaseModel

class DashboardSummaryOut(BaseModel):
    total_users: int
    total_products: int
    total_orders: int
    total_revenue: float
    orders_by_status: Dict[str, int]
    payments_by_status: Dict[str, int]
    low_stock_items_count: int
    pending_returns_count: int
