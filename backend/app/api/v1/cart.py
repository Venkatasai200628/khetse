"""Cart endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.catalog import Commodity, ProduceListing
from app.models.enums import RoleEnum
from app.models.profiles import FarmerProfile
from app.models.user import User
from app.schemas.cart import CartItemAdd, CartItemPublic, CartItemUpdate, CartPublic
from app.services import cart_service

router = APIRouter(prefix="/cart", tags=["cart"])


def _to_public(cart, db) -> CartPublic:
    data = CartPublic.model_validate(cart)
    subtotal = 0
    for item_dto, item_row in zip(data.items, cart.items):
        listing = db.get(ProduceListing, item_row.listing_id)
        if listing is not None:
            commodity = db.get(Commodity, listing.commodity_id)
            if commodity is not None:
                item_dto.commodity_name = commodity.name_en
            item_dto.listing_status = listing.status.value
            farmer_profile = db.scalar(
                select(FarmerProfile).where(FarmerProfile.user_id == listing.farmer_id)
            )
            if farmer_profile is not None:
                item_dto.farmer_district = farmer_profile.district
        item_dto.line_total_paise = int(
            item_row.unit_price_paise * item_row.quantity + 0.5
        )
        subtotal += item_dto.line_total_paise
    data.subtotal_paise = subtotal
    return data


@router.get("", response_model=CartPublic)
def get_cart(
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(RoleEnum.BUYER, RoleEnum.BUSINESS)),
):
    cart = cart_service.get_or_create_cart(db, buyer)
    return _to_public(cart, db)


@router.post("/items", response_model=CartPublic)
def add_cart_item(
    body: CartItemAdd,
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(RoleEnum.BUYER, RoleEnum.BUSINESS)),
):
    cart = cart_service.add_item(db, buyer, body.listing_id, body.quantity)
    return _to_public(cart, db)


@router.patch("/items/{item_id}", response_model=CartPublic)
def update_cart_item(
    item_id: uuid.UUID,
    body: CartItemUpdate,
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(RoleEnum.BUYER, RoleEnum.BUSINESS)),
):
    cart = cart_service.update_item_quantity(db, buyer, item_id, body.quantity)
    return _to_public(cart, db)


@router.delete("/items/{item_id}", response_model=CartPublic)
def remove_cart_item(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(RoleEnum.BUYER, RoleEnum.BUSINESS)),
):
    cart = cart_service.remove_item(db, buyer, item_id)
    return _to_public(cart, db)
