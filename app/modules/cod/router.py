from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.payments import CODRecord, Payment
from app.models.orders import Order
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import require_roles
from app.common.enums import UserRole, PaymentStatus, AuditAction
from app.core.exceptions import NotFoundError, BadRequestError
from app.core.audit import log_audit
from app.modules.cod.schemas import CODCollectionUpdate, CODReconciliationRequest, CODRecordOut

router = APIRouter(prefix="/cod", tags=["Module 32: Cash on Delivery Management"])

@router.put("/{order_id}/collect", response_model=ResponseSchema[CODRecordOut])
def update_cod_collection(
    order_id: int,
    data: CODCollectionUpdate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DELIVERY_MANAGER)),
    db: Session = Depends(get_db)
):
    rec = db.query(CODRecord).filter(CODRecord.order_id == order_id).first()
    if not rec:
        raise NotFoundError("COD record not found for this order")

    rec.collection_status = data.collection_status
    if data.collection_status == "COLLECTED":
        rec.collected_at = datetime.now(timezone.utc)
        rec.collected_by_id = current_user.id
        
        # update payment status to SUCCESSFUL
        payment = db.query(Payment).filter(Payment.order_id == order_id).first()
        if payment:
            payment.status = PaymentStatus.SUCCESSFUL

    rec.notes = data.notes
    db.commit()
    db.refresh(rec)
    log_audit(db, AuditAction.UPDATE, "CODRecord", str(rec.id), current_user.id, new_values=data.model_dump())
    return ResponseSchema(message=f"COD status updated to {data.collection_status}", data=CODRecordOut.model_validate(rec))

@router.post("/reconcile", response_model=ResponseSchema[CODRecordOut])
def reconcile_cod_payment(
    req: CODReconciliationRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.FINANCE_MANAGER)),
    db: Session = Depends(get_db)
):
    rec = db.query(CODRecord).filter(CODRecord.order_id == req.order_id).first()
    if not rec:
        raise NotFoundError("COD record not found")

    if rec.collection_status != "COLLECTED":
        raise BadRequestError("Cannot reconcile uncollected COD order")

    rec.reconciled = True
    rec.reconciliation_date = datetime.now(timezone.utc)
    if req.notes:
        rec.notes = f"{rec.notes or ''} | {req.notes}"

    db.commit()
    db.refresh(rec)
    log_audit(db, AuditAction.UPDATE, "CODRecord", str(rec.id), current_user.id, new_values={"reconciled": True})
    return ResponseSchema(message="COD reconciled successfully with order", data=CODRecordOut.model_validate(rec))

@router.get("", response_model=ResponseSchema[List[CODRecordOut]])
def get_cod_records(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.FINANCE_MANAGER, UserRole.DELIVERY_MANAGER)),
    db: Session = Depends(get_db)
):
    records = db.query(CODRecord).order_by(CODRecord.created_at.desc()).all()
    return ResponseSchema(data=[CODRecordOut.model_validate(r) for r in records])
