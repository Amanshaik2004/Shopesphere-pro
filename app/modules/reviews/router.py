from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models.engagement import ProductReview
from app.models.catalog import Product
from app.models.orders import Order, OrderItem
from app.models.users import User
from app.common.responses import ResponseSchema, MessageResponse
from app.common.dependencies import get_current_active_user, require_roles
from app.common.enums import UserRole, OrderStatus, AuditAction
from app.core.exceptions import NotFoundError, ConflictError
from app.core.audit import log_audit
from app.modules.reviews.schemas import ReviewCreate, ReviewOut, ProductRatingSummary

router = APIRouter(prefix="/reviews", tags=["Module 38: Product Reviews and Ratings"])

@router.post("", response_model=ResponseSchema[ReviewOut])
def submit_review(
    data: ReviewCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if not db.query(Product).filter(Product.id == data.product_id).first():
        raise NotFoundError("Product not found")

    existing = db.query(ProductReview).filter(
        ProductReview.product_id == data.product_id,
        ProductReview.user_id == current_user.id
    ).first()
    if existing:
        raise ConflictError("You have already reviewed this product")

    # Check verified purchase
    verified = db.query(OrderItem).join(Order).filter(
        Order.user_id == current_user.id,
        Order.status == OrderStatus.DELIVERED,
        OrderItem.product_id == data.product_id
    ).first() is not None

    review = ProductReview(
        product_id=data.product_id,
        user_id=current_user.id,
        rating=data.rating,
        title=data.title,
        comment=data.comment,
        is_verified_purchase=verified,
        is_approved=True
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    log_audit(db, AuditAction.CREATE, "ProductReview", str(review.id), current_user.id)
    return ResponseSchema(message="Review submitted successfully", data=ReviewOut.model_validate(review))

@router.get("/product/{product_id}", response_model=ResponseSchema[List[ReviewOut]])
def get_product_reviews(product_id: int, db: Session = Depends(get_db)):
    reviews = db.query(ProductReview).filter(
        ProductReview.product_id == product_id,
        ProductReview.is_approved == True
    ).order_by(ProductReview.created_at.desc()).all()
    return ResponseSchema(data=[ReviewOut.model_validate(r) for r in reviews])

@router.get("/product/{product_id}/summary", response_model=ResponseSchema[ProductRatingSummary])
def get_product_rating_summary(product_id: int, db: Session = Depends(get_db)):
    stats = db.query(
        func.avg(ProductReview.rating),
        func.count(ProductReview.id)
    ).filter(
        ProductReview.product_id == product_id,
        ProductReview.is_approved == True
    ).first()

    avg_rating = round(float(stats[0] or 0.0), 1)
    count = int(stats[1] or 0)

    return ResponseSchema(data=ProductRatingSummary(
        product_id=product_id,
        average_rating=avg_rating,
        total_reviews=count
    ))

@router.put("/{review_id}/moderate", response_model=ResponseSchema[ReviewOut])
def moderate_review(
    review_id: int,
    is_approved: bool = Query(...),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPPORT_AGENT)),
    db: Session = Depends(get_db)
):
    review = db.query(ProductReview).filter(ProductReview.id == review_id).first()
    if not review:
        raise NotFoundError("Review not found")

    review.is_approved = is_approved
    db.commit()
    db.refresh(review)
    return ResponseSchema(message=f"Review approval status updated to {is_approved}", data=ReviewOut.model_validate(review))
