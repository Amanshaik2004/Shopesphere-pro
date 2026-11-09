import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.logistics import WarrantyClaim
from app.models.orders import OrderItem
from app.models.catalog import Product
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import get_current_active_user, require_roles
from app.common.enums import UserRole, WarrantyStatus, AuditAction
from app.core.exceptions import NotFoundError, ForbiddenError, BadRequestError
from app.core.audit import log_audit
from app.modules.returns.schemas import WarrantyClaimCreate, WarrantyClaimReview, WarrantyClaimOut

router = APIRouter(prefix="/warranty", tags=["Module 3.7: Warranty Management"])

@router.post("/claims", response_model=ResponseSchema[WarrantyClaimOut])
def submit_warranty_claim(
    data: WarrantyClaimCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    item = db.query(OrderItem).filter(OrderItem.id == data.order_item_id).first()
    if not item:
        raise NotFoundError("Order item not found")

    prod = db.query(Product).filter(Product.id == data.product_id).first()
    if not prod:
        raise NotFoundError("Product not found")

    claim_num = f"WAR-{uuid.uuid4().hex[:8].upper()}"
    claim = WarrantyClaim(
        claim_number=claim_num,
        user_id=current_user.id,
        order_item_id=item.id,
        product_id=prod.id,
        claim_reason=data.claim_reason,
        description=data.description,
        evidence_url=data.evidence_url,
        status=WarrantyStatus.PENDING
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    log_audit(db, AuditAction.CREATE, "WarrantyClaim", str(claim.id), current_user.id)
    return ResponseSchema(message="Warranty claim submitted successfully", data=WarrantyClaimOut.model_validate(claim))

@router.get("/claims", response_model=ResponseSchema[List[WarrantyClaimOut]])
def get_warranty_claims(
    status: Optional[WarrantyStatus] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(WarrantyClaim)
    if current_user.role == UserRole.CUSTOMER:
        query = query.filter(WarrantyClaim.user_id == current_user.id)
    if status:
        query = query.filter(WarrantyClaim.status == status)

    claims = query.order_by(WarrantyClaim.created_at.desc()).all()
    return ResponseSchema(data=[WarrantyClaimOut.model_validate(c) for c in claims])

@router.get("/claims/{claim_id}", response_model=ResponseSchema[WarrantyClaimOut])
def get_warranty_claim_by_id(
    claim_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    claim = db.query(WarrantyClaim).filter(WarrantyClaim.id == claim_id).first()
    if not claim:
        raise NotFoundError("Warranty claim not found")

    if current_user.role == UserRole.CUSTOMER and claim.user_id != current_user.id:
        raise ForbiddenError("Access denied")

    return ResponseSchema(data=WarrantyClaimOut.model_validate(claim))

@router.put("/claims/{claim_id}/review", response_model=ResponseSchema[WarrantyClaimOut])
def review_warranty_claim(
    claim_id: int,
    data: WarrantyClaimReview,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPPORT_AGENT)),
    db: Session = Depends(get_db)
):
    claim = db.query(WarrantyClaim).filter(WarrantyClaim.id == claim_id).first()
    if not claim:
        raise NotFoundError("Warranty claim not found")

    claim.status = data.status
    claim.resolution_notes = data.resolution_notes
    claim.approved_by_id = current_user.id
    db.commit()
    db.refresh(claim)
    log_audit(db, AuditAction.STATUS_CHANGE, "WarrantyClaim", str(claim.id), current_user.id, new_values={"status": data.status.value, "notes": data.resolution_notes})
    return ResponseSchema(message=f"Warranty claim status updated to {data.status.value}", data=WarrantyClaimOut.model_validate(claim))
