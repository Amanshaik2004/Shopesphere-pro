from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.orders import TaxRate
from app.models.users import User
from app.common.responses import ResponseSchema, MessageResponse
from app.common.dependencies import require_roles
from app.common.enums import UserRole, AuditAction
from app.core.exceptions import NotFoundError
from app.core.audit import log_audit
from app.modules.taxes.schemas import TaxRateCreate, TaxRateUpdate, TaxRateOut

router = APIRouter(prefix="/taxes", tags=["Module 22: Tax Management"])

@router.post("", response_model=ResponseSchema[TaxRateOut])
def create_tax_rate(
    data: TaxRateCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.FINANCE_MANAGER)),
    db: Session = Depends(get_db)
):
    tax = TaxRate(**data.model_dump())
    db.add(tax)
    db.commit()
    db.refresh(tax)
    log_audit(db, AuditAction.CREATE, "TaxRate", str(tax.id), current_user.id, new_values=data.model_dump())
    return ResponseSchema(message="Tax rate created successfully", data=TaxRateOut.model_validate(tax))

@router.get("", response_model=ResponseSchema[List[TaxRateOut]])
def get_tax_rates(
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(TaxRate)
    if is_active is not None:
        query = query.filter(TaxRate.is_active == is_active)
    return ResponseSchema(data=[TaxRateOut.model_validate(t) for t in query.all()])

@router.get("/{tax_id}", response_model=ResponseSchema[TaxRateOut])
def get_tax_rate_by_id(tax_id: int, db: Session = Depends(get_db)):
    tax = db.query(TaxRate).filter(TaxRate.id == tax_id).first()
    if not tax:
        raise NotFoundError("Tax rate not found")
    return ResponseSchema(data=TaxRateOut.model_validate(tax))

@router.put("/{tax_id}", response_model=ResponseSchema[TaxRateOut])
def update_tax_rate(
    tax_id: int,
    data: TaxRateUpdate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.FINANCE_MANAGER)),
    db: Session = Depends(get_db)
):
    tax = db.query(TaxRate).filter(TaxRate.id == tax_id).first()
    if not tax:
        raise NotFoundError("Tax rate not found")

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(tax, key, val)

    db.commit()
    db.refresh(tax)
    log_audit(db, AuditAction.UPDATE, "TaxRate", str(tax.id), current_user.id, new_values=data.model_dump(exclude_unset=True))
    return ResponseSchema(message="Tax rate updated successfully", data=TaxRateOut.model_validate(tax))

@router.delete("/{tax_id}", response_model=ResponseSchema[MessageResponse])
def delete_tax_rate(
    tax_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.FINANCE_MANAGER)),
    db: Session = Depends(get_db)
):
    tax = db.query(TaxRate).filter(TaxRate.id == tax_id).first()
    if not tax:
        raise NotFoundError("Tax rate not found")

    db.delete(tax)
    db.commit()
    log_audit(db, AuditAction.DELETE, "TaxRate", str(tax_id), current_user.id)
    return ResponseSchema(message="Tax rate deleted successfully", data=MessageResponse(message="Tax rate removed"))
