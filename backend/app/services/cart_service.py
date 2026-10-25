"""Buyer cart operations."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationAppError
from app.models.catalog import ProduceListing
from app.models.commerce import Cart, CartItem
from app.models.enums import ListingStatus
from app.models.user import User


def get_or_create_cart(db: Session, buyer: User) -> Cart:
    cart = db.scalar(select(Cart).where(Cart.buyer_id == buyer.id))
    if cart is None:
        cart = Cart(buyer_id=buyer.id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def add_item(db: Session, buyer: User, listing_id: uuid.UUID, quantity: float) -> Cart:
    if quantity <= 0:
        raise ValidationAppError("Quantity must be positive.")

    listing = db.get(ProduceListing, listing_id)
    if listing is None or listing.status != ListingStatus.ACTIVE:
        raise NotFoundError("Listing not found or not available.")

    cart = get_or_create_cart(db, buyer)
    item = db.scalar(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.listing_id == listing_id)
    )
    # Validate the CUMULATIVE cart line, not just the increment — otherwise
    # "10 available, 8 in cart, add 5 more" would silently build a 13-unit
    # line that only fails later at checkout.
    new_quantity = round((item.quantity if item is not None else 0.0) + float(quantity), 2)
    if listing.quantity_available < new_quantity:
        raise ValidationAppError(
            "Requested quantity exceeds availability.",
            details={"available": listing.quantity_available, "unit": listing.unit.value},
        )

    if item is None:
        item = CartItem(
            cart_id=cart.id,
            listing_id=listing_id,
            quantity=new_quantity,
            unit_price_paise=listing.listed_price_paise,
        )
        db.add(item)
    else:
        # Re-snapshot the current price; availability is re-checked at checkout.
        item.quantity = new_quantity
        item.unit_price_paise = listing.listed_price_paise
    db.commit()
    db.refresh(cart)
    return cart


def update_item_quantity(
    db: Session, buyer: User, item_id: uuid.UUID, quantity: float
) -> Cart:
    if quantity <= 0:
        raise ValidationAppError("Quantity must be positive.")
    cart = get_or_create_cart(db, buyer)
    item = db.get(CartItem, item_id)
    if item is None or item.cart_id != cart.id:
        raise NotFoundError("Cart item not found.")

    listing = db.get(ProduceListing, item.listing_id)
    if listing is not None and listing.quantity_available < quantity:
        raise ValidationAppError(
            "Requested quantity exceeds availability.",
            details={"available": listing.quantity_available},
        )
    item.quantity = round(float(quantity), 2)
    db.commit()
    db.refresh(cart)
    return cart


def remove_item(db: Session, buyer: User, item_id: uuid.UUID) -> Cart:
    cart = get_or_create_cart(db, buyer)
    item = db.get(CartItem, item_id)
    if item is None or item.cart_id != cart.id:
        raise NotFoundError("Cart item not found.")
    db.delete(item)
    db.commit()
    db.refresh(cart)
    return cart
