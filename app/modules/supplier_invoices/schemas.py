from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.common.enums import InvoiceStatus

class SupplierInvoiceCreate(BaseModel):
    invoice_number: str
    purchase_order_id: int
    amount: float = Field(gt=0)
    due_date: datetime
    file_url: Optional[str] = None

class SupplierInvoiceUpdate(BaseModel):
    status: InvoiceStatus

class SupplierInvoiceOut(BaseModel):
    id: int
    invoice_number: str
    purchase_order_id: int
    supplier_id: int
    amount: float
    due_date: datetime
    status: InvoiceStatus
    file_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
