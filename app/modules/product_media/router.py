from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.catalog import ProductMedia, Product, ProductVariant
from app.models.users import User
from app.common.responses import ResponseSchema, MessageResponse
from app.common.dependencies import require_roles
from app.common.enums import UserRole, AuditAction
from app.core.exceptions import NotFoundError, BadRequestError
from app.integrations.storage.local import local_storage
from app.core.audit import log_audit
from app.modules.product_media.schemas import ProductMediaOut, ProductMediaCreate

router = APIRouter(prefix="/product-media", tags=["Module 10: Product Images & Documents"])

@router.post("/upload", response_model=ResponseSchema[ProductMediaOut])
async def upload_product_media(
    product_id: int = Form(...),
    variant_id: Optional[int] = Form(None),
    is_primary: bool = Form(False),
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    if not db.query(Product).filter(Product.id == product_id).first():
        raise NotFoundError("Product not found")

    if variant_id and not db.query(ProductVariant).filter(ProductVariant.id == variant_id).first():
        raise NotFoundError("Product variant not found")

    file_url = await local_storage.save_file(file)

    if is_primary:
        # unset other primary images for this product
        db.query(ProductMedia).filter(ProductMedia.product_id == product_id).update({"is_primary": False})

    media = ProductMedia(
        product_id=product_id,
        variant_id=variant_id,
        file_name=file.filename or "unknown",
        file_url=file_url,
        file_type=file.content_type or "application/octet-stream",
        file_size=file.size or 0,
        is_primary=is_primary
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    log_audit(db, AuditAction.CREATE, "ProductMedia", str(media.id), current_user.id)
    return ResponseSchema(message="Media uploaded successfully", data=ProductMediaOut.model_validate(media))

@router.get("/product/{product_id}", response_model=ResponseSchema[List[ProductMediaOut]])
def get_media_for_product(product_id: int, db: Session = Depends(get_db)):
    items = db.query(ProductMedia).filter(ProductMedia.product_id == product_id).all()
    return ResponseSchema(data=[ProductMediaOut.model_validate(m) for m in items])

@router.delete("/{media_id}", response_model=ResponseSchema[MessageResponse])
def delete_product_media(
    media_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    media = db.query(ProductMedia).filter(ProductMedia.id == media_id).first()
    if not media:
        raise NotFoundError("Product media not found")

    db.delete(media)
    db.commit()
    log_audit(db, AuditAction.DELETE, "ProductMedia", str(media_id), current_user.id)
    return ResponseSchema(message="Product media removed successfully", data=MessageResponse(message="Media deleted"))
