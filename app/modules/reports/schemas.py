from typing import Optional, List
from pydantic import BaseModel

class SalesReportItem(BaseModel):
    date: str
    orders_count: int
    gross_sales: float
    discounts: float
    net_sales: float

class InventoryValuationReport(BaseModel):
    total_items: int
    total_quantity: int
    total_inventory_value: float

class ProductPerformanceReport(BaseModel):
    product_id: int
    product_name: str
    sku: str
    units_sold: int
    revenue_generated: float
