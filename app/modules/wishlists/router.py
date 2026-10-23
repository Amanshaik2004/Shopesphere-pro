from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models.orders import Wishlist
from app.models.catalog import Product
from app.models.inventory import InventoryItem
from app.models.users import User
from app.common.responses import ResponseSchema, MessageResponse
from app.common.dependencies import get_current_active_user
from app.core.exceptions import NotFoundError, ConflictError
from app.modules.wishlists.schemas import WishlistAddRequest, WishlistItemOut

router = APIRouter(prefix="/wishlist", tags=["Module 19: Wishlist Management"])

@router.post("", response_model=ResponseSchema[WishlistItemOut])
def add_to_wishlist(
    data: WishlistAddRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == data.product_id, Product.is_active == True).first()
    if not product:
        raise NotFoundError("Product not found")

    existing = db.query(Wishlist).filter(
        Wishlist.user_id == current_user.id,
        Wishlist.product_id == data.product_id
    ).first()
    if existing:
        raise ConflictError("Product already in wishlist")

    item = Wishlist(user_id=current_user.id, product_id=data.product_id)
    db.add(item)
    db.commit()
    db.refresh(item)

    stock = db.query(func.sum(InventoryItem.quantity - InventoryItem.reserved_quantity)).filter(
        InventoryItem.product_id == product.id
    ).scalar() or 0

    return ResponseSchema(
        message="Product added to wishlist",
        data=WishlistItemOut(
            id=item.id,
            product_id=product.id,
            product_name=product.name,
            base_price=float(product.base_price),
            sale_price=float(product.sale_price) if product.sale_price else None,
            is_available=stock > 0,
            created_at=item.created_at
        )
    )

@router.get("", response_model=ResponseSchema[List[WishlistItemOut]])
def get_my_wishlist(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    items = db.query(Wishlist).filter(Wishlist.user_id == current_user.id).all()
    results = []
    for item in items:
        prod = db.query(Product).filter(Product.id == item.product_id).first()
        if prod:
            stock = db.query(func.sum(InventoryItem.quantity - InventoryItem.reserved_quantity)).filter(
                InventoryItem.product_id == prod.id
            ).scalar() or 0
            results.append(WishlistItemOut(
                id=item.id,
                product_id=prod.id,
                product_name=prod.name,
                base_price=float(prod.base_price),
                sale_price=float(prod.sale_price) if prod.sale_price else None,
                is_available=stock > 0,
                created_at=item.created_at
            ))
    return ResponseSchema(data=results)

@router.delete("/{product_id}", response_model=ResponseSchema[MessageResponse])
def remove_from_wishlist(
    product_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    item = db.query(Wishlist).filter(
        Wishlist.user_id == current_user.id,
        Wishlist.product_id == product_id
    ).first()
    if not item:
        raise NotFoundError("Product not in your wishlist")

    db.delete(item)
    db.commit()
    return ResponseSchema(message="Removed from wishlist", data=MessageResponse(message="Item removed"))
