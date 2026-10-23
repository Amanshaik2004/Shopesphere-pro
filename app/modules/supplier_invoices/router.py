from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.suppliers import SupplierInvoice, PurchaseOrder
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import require_roles
from app.common.enums import UserRole, InvoiceStatus, AuditAction
from app.core.exceptions import NotFoundError, ConflictError
from app.core.audit import log_audit
from app.modules.supplier_invoices.schemas import SupplierInvoiceCreate, SupplierInvoiceUpdate, SupplierInvoiceOut

router = APIRouter(prefix="/supplier-invoices", tags=["Module 45: Supplier Invoice Management"])

@router.post("", response_model=ResponseSchema[SupplierInvoiceOut])
def create_supplier_invoice(
    data: SupplierInvoiceCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.FINANCE_MANAGER)),
    db: Session = Depends(get_db)
):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == data.purchase_order_id).first()
    if not po:
        raise NotFoundError("Purchase order not found")

    if db.query(SupplierInvoice).filter(SupplierInvoice.invoice_number == data.invoice_number).first():
        raise ConflictError("Invoice number already registered")

    inv = SupplierInvoice(
        invoice_number=data.invoice_number,
        purchase_order_id=po.id,
        supplier_id=po.supplier_id,
        amount=data.amount,
        due_date=data.due_date,
        file_url=data.file_url,
        status=InvoiceStatus.ISSUED
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    log_audit(db, AuditAction.CREATE, "SupplierInvoice", str(inv.id), current_user.id, new_values=data.model_dump())
    return ResponseSchema(message="Supplier invoice recorded", data=SupplierInvoiceOut.model_validate(inv))

@router.get("", response_model=ResponseSchema[List[SupplierInvoiceOut]])
def list_supplier_invoices(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.FINANCE_MANAGER)),
    db: Session = Depends(get_db)
):
    invoices = db.query(SupplierInvoice).order_by(SupplierInvoice.created_at.desc()).all()
    return ResponseSchema(data=[SupplierInvoiceOut.model_validate(i) for i in invoices])

@router.put("/{invoice_id}/status", response_model=ResponseSchema[SupplierInvoiceOut])
def update_invoice_status(
    invoice_id: int,
    data: SupplierInvoiceUpdate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.FINANCE_MANAGER)),
    db: Session = Depends(get_db)
):
    inv = db.query(SupplierInvoice).filter(SupplierInvoice.id == invoice_id).first()
    if not inv:
        raise NotFoundError("Invoice not found")

    inv.status = data.status
    db.commit()
    db.refresh(inv)
    log_audit(db, AuditAction.STATUS_CHANGE, "SupplierInvoice", str(inv.id), current_user.id, new_values={"status": data.status.value})
    return ResponseSchema(message="Invoice status updated", data=SupplierInvoiceOut.model_validate(inv))
