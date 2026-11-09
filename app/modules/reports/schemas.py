from typing import Optional, List, Dict, Any
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

class AdvancedSalesReportOut(BaseModel):
    total_orders: int
    gross_revenue: float
    discounts_total: float
    net_revenue: float
    items_count: int
    breakdown: List[Dict[str, Any]]

class FinancialSummaryReportOut(BaseModel):
    total_payments_received: float
    total_refunds_issued: float
    total_returns_count: int
    total_seller_settlements: float
    net_platform_profit: float

class InventoryAgingReportOut(BaseModel):
    total_inventory_units: int
    low_stock_items_count: int
    slow_moving_items_count: int
    aging_items: List[Dict[str, Any]]

class CustomerRetentionReportOut(BaseModel):
    total_customers: int
    repeat_customers_count: int
    repeat_purchase_rate: float
    average_order_value: float
    segment_breakdown: List[Dict[str, Any]]
