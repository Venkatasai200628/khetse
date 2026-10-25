"""Order lifecycle: creation from cart, acceptance, rejection, cancellation.

Key invariants:
- Order creation runs in ONE transaction: rows are locked (SELECT … FOR
  UPDATE on PostgreSQL), availability re-checked, reservations written.
- Idempotency keys make client retries safe (same key AND same buyer ⇒
  same order); a key that belongs to another buyer is rejected, never
  returned to them.
- Overselling is impossible: quantity_reserved can never exceed total.
- Only a farmer with items in the order (or the FPO operator of those
  farmers) may accept/reject — and only for their own lines.
- A multi-farmer order only moves forward once EVERY farmer in it has
  responded; a rejection frees that farmer's stock immediately.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from app.core.config import get_settings
from app.models.catalog import ProduceListing
from app.models.commerce import (
    CartItem,
    InventoryReservation,
    Order,
    OrderItem,
)
from app.models.enums import (
    FarmerResponseStatus,
    FulfilmentType,
    ListingStatus,
    OrderStatus,
    PaymentStatus,
    ReservationStatus,
    RoleEnum,
)
from app.models.profiles import FarmerProfile
from app.models.user import User
from app.services import order_state
from app.services.cart_service import get_or_create_cart
from app.services.pricing import compute_order_money
from app.utils.geo import haversine_km


def create_order_from_cart(
    db: Session,
    buyer: User,
    *,
    idempotency_key: str | None,
    fulfilment: str = FulfilmentType.DELIVERY.value,
    delivery_name: str | None = None,
    delivery_phone: str | None = None,
    delivery_address: str | None = None,
    delivery_district: str | None = None,
    delivery_lat: float | None = None,
    delivery_lng: float | None = None,
    notes: str | None = None,
) -> Order:
    if idempotency_key:
        existing = db.scalar(
            select(Order).where(Order.idempotency_key == idempotency_key)
        )
        if existing is not None:
            if existing.buyer_id != buyer.id:
                # Never hand another buyer's order (address, phone, …) to
                # whoever happens to reuse the key.
                raise ConflictError("This idempotency key is already in use.")
            return existing  # safe retry — never double-order

    if fulfilment == FulfilmentType.DELIVERY.value and not delivery_address:
        raise ValidationAppError("Delivery address is required for delivery orders.")

    cart = get_or_create_cart(db, buyer)
    items = list(cart.items)
    if not items:
        raise ValidationAppError("Cart is empty.")

    try:
        # ---- Transactional reservation block ----
        subtotal = 0
        locked_items: list[tuple[CartItem, ProduceListing]] = []
        for item in items:
            listing = db.scalar(
                select(ProduceListing)
                .where(ProduceListing.id == item.listing_id)
                .with_for_update()
            )
            if listing is None or listing.status != ListingStatus.ACTIVE:
                raise ConflictError(
                    "A listing in your cart is no longer available.",
                    details={"listing_id": str(item.listing_id)},
                )
            available = round(listing.quantity_total - listing.quantity_reserved, 2)
            if available < item.quantity:
                raise ConflictError(
                    "Insufficient stock for a listing in your cart.",
                    details={
                        "listing_id": str(listing.id),
                        "requested": item.quantity,
                        "available": available,
                    },
                )
            listing.quantity_reserved = round(
                listing.quantity_reserved + item.quantity, 2
            )
            subtotal += int(item.unit_price_paise * item.quantity + 0.5)
            locked_items.append((item, listing))

        money = compute_order_money(
            db,
            subtotal,
            fulfilment=fulfilment,
            distance_km=_delivery_distance_km(delivery_lat, delivery_lng, locked_items),
        )

        order = Order(
            buyer_id=buyer.id,
            status=OrderStatus.CREATED,
            fulfilment=fulfilment,
            delivery_name=delivery_name,
            delivery_phone=delivery_phone,
            delivery_address=delivery_address,
            delivery_district=delivery_district,
            delivery_lat=delivery_lat,
            delivery_lng=delivery_lng,
            subtotal_paise=money.subtotal_paise,
            delivery_fee_paise=money.delivery_fee_paise,
            platform_fee_paise=money.platform_fee_paise,
            total_paise=money.total_paise,
            idempotency_key=idempotency_key,
            notes=notes,
            placed_at=datetime.now(timezone.utc),
        )
        db.add(order)
        db.flush()  # order.id available

        for item, listing in locked_items:
            db.add(
                OrderItem(
                    order_id=order.id,
                    listing_id=listing.id,
                    farmer_id=listing.farmer_id,
                    commodity_id=listing.commodity_id,
                    quantity=item.quantity,
                    unit=listing.unit,
                    unit_price_paise=item.unit_price_paise,
                    line_total_paise=int(item.unit_price_paise * item.quantity + 0.5),
                    quality_grade=listing.quality_grade,
                    farmer_response=FarmerResponseStatus.PENDING,
                )
            )
            db.add(
                InventoryReservation(
                    order_id=order.id,
                    listing_id=listing.id,
                    quantity=item.quantity,
                    status=ReservationStatus.ACTIVE,
                )
            )
            db.delete(item)

        order_state.apply_transition(
            db,
            order,
            OrderStatus.AWAITING_FARMER_CONFIRMATION,
            role_override="system",
            reason="Order placed from cart",
        )
        db.commit()
        db.refresh(order)
        return order
    except Exception:
        db.rollback()
        raise


def _delivery_distance_km(
    delivery_lat: float | None,
    delivery_lng: float | None,
    locked_items: list[tuple[CartItem, ProduceListing]],
) -> float | None:
    """Distance to the FARTHEST farm in the order, or None when unknown.

    Farm coordinates are used server-side for the delivery quote only —
    they are never exposed to buyers.
    """
    if delivery_lat is None or delivery_lng is None:
        return None
    farm_points = [
        (listing.farm_lat, listing.farm_lng)
        for _, listing in locked_items
        if listing.farm_lat is not None and listing.farm_lng is not None
    ]
    if not farm_points:
        return None
    return max(
        haversine_km(delivery_lat, delivery_lng, lat, lng)
        for lat, lng in farm_points
    )


def _get_order_for(db: Session, order_id: uuid.UUID) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise NotFoundError("Order not found.")
    return order


def _member_farmer_ids(db: Session, user: User) -> set[uuid.UUID]:
    """Farmer ids belonging to the FPO the operator account is tied to."""
    if not (user.has_role(RoleEnum.FPO_OPERATOR) and user.fpo_id is not None):
        return set()
    return set(
        db.scalars(
            select(FarmerProfile.user_id).where(FarmerProfile.fpo_id == user.fpo_id)
        )
    )


def responder_items(db: Session, order: Order, user: User) -> list[OrderItem]:
    """Order lines `user` may respond on: their own, plus (for an FPO
    operator) lines farmed by members of their FPO."""
    member_ids = _member_farmer_ids(db, user)
    return [
        item
        for item in order.items
        if item.farmer_id == user.id or item.farmer_id in member_ids
    ]


def is_order_participant(db: Session, order: Order, user: User) -> bool:
    """True when the user is the buyer, a farmer in the order, or the FPO
    operator of a farmer in the order."""
    if order.buyer_id == user.id:
        return True
    return bool(responder_items(db, order, user))


def farmer_respond(
    db: Session, farmer: User, order_id: uuid.UUID, accept: bool, reason: str | None = None
) -> Order:
    order = _get_order_for(db, order_id)
    actionable = responder_items(db, order, farmer)
    if not actionable:
        raise ConflictError("This order does not include your produce.")
    if order.status != OrderStatus.AWAITING_FARMER_CONFIRMATION:
        raise ConflictError("This order is not awaiting a farmer response.")
    if any(item.farmer_response != FarmerResponseStatus.PENDING for item in actionable):
        raise ConflictError("You have already responded to this order.")

    for item in actionable:
        item.farmer_response = (
            FarmerResponseStatus.ACCEPTED if accept else FarmerResponseStatus.REJECTED
        )
    all_responded = all(
        item.farmer_response != FarmerResponseStatus.PENDING for item in order.items
    )
    any_rejected = any(
        item.farmer_response == FarmerResponseStatus.REJECTED for item in order.items
    )

    if accept:
        if all_responded:
            if any_rejected:
                # A co-farmer already rejected — the order cannot proceed.
                order_state.apply_transition(
                    db,
                    order,
                    OrderStatus.REJECTED,
                    user=farmer,
                    reason="Another farmer in this order rejected it",
                )
                _release_reservations(db, order)  # frees the rest
            else:
                # Every farmer accepted — the order can move forward.
                order_state.apply_transition(
                    db, order, OrderStatus.ACCEPTED, user=farmer, reason=reason
                )
                order_state.apply_transition(
                    db,
                    order,
                    OrderStatus.PAYMENT_PENDING,
                    role_override="system",
                    reason="All farmers accepted; awaiting payment",
                )
                order.payment_status = PaymentStatus.PENDING
        # Otherwise: wait for the remaining farmers before moving the order.
    else:
        # A rejection frees this farmer's stock immediately; other farmers'
        # items stay reserved until the order resolves.
        _release_reservations(db, order, items=actionable)
        if all_responded:
            # The order can no longer be fulfilled as placed.
            order_state.apply_transition(
                db, order, OrderStatus.REJECTED, user=farmer, reason=reason
            )
            _release_reservations(db, order)  # idempotent — frees the rest
    db.commit()
    db.refresh(order)
    return order


def _release_reservations(
    db: Session, order: Order, items: list[OrderItem] | None = None
) -> None:
    """Mark ACTIVE reservations RELEASED and give the quantity back.

    Idempotent — already-released rows are skipped — so it is safe to call
    repeatedly (e.g. per-farmer release, then order-wide release). When
    `items` is given, only those order lines' reservations are released.
    """
    now = datetime.now(timezone.utc)
    listing_ids = {item.listing_id for item in items} if items is not None else None
    for res in db.scalars(
        select(InventoryReservation).where(InventoryReservation.order_id == order.id)
    ):
        if res.status != ReservationStatus.ACTIVE:
            continue
        if listing_ids is not None and res.listing_id not in listing_ids:
            continue
        listing = db.get(ProduceListing, res.listing_id)
        if listing is not None:
            listing.quantity_reserved = round(
                max(0.0, listing.quantity_reserved - res.quantity), 2
            )
        res.status = ReservationStatus.RELEASED
        res.released_at = now


def buyer_cancel(db: Session, buyer: User, order_id: uuid.UUID, reason: str | None) -> Order:
    order = _get_order_for(db, order_id)
    if order.buyer_id != buyer.id:
        raise ConflictError("You can only cancel your own orders.")

    order_state.apply_transition(
        db, order, OrderStatus.CANCELLED, user=buyer, reason=reason
    )
    order.cancelled_at = datetime.now(timezone.utc)
    order.cancel_reason = reason
    _release_reservations(db, order)
    db.commit()
    db.refresh(order)
    return order


def pay_order(db: Session, buyer: User, order_id: uuid.UUID) -> Order:
    """Buyer-side mock payment capture — demo mode only.

    There is no real payment provider wired up yet, so the in-app capture
    exists only while demo mode is on; production captures arrive through
    the signed /payments/webhook instead.
    """
    if not get_settings().demo_mode:
        raise AuthorizationError(
            "In-app payments are not enabled in this environment yet."
        )
    order = _get_order_for(db, order_id)
    if order.buyer_id != buyer.id:
        raise ConflictError("You can only pay for your own orders.")
    return capture_payment(db, order)


def capture_payment(db: Session, order: Order) -> Order:
    """Apply PAYMENT_PENDING → CONFIRMED and mark the payment SUCCESS.

    Shared by the demo pay endpoint and the payment-provider webhook; the
    state machine enforces that only an order awaiting payment can be
    captured, so out-of-order calls are rejected with 409.
    """
    order_state.apply_transition(
        db,
        order,
        OrderStatus.CONFIRMED,
        role_override="system",
        reason="Payment captured",
    )
    order.payment_status = PaymentStatus.SUCCESS
    db.commit()
    db.refresh(order)
    return order


def complete_order(db: Session, actor: User, order_id: uuid.UUID) -> Order:
    """Admin close-out after delivery: finalise the inventory and ledger
    timestamps. Payment settlement is tracked separately — completing an
    order is not proof of payment."""
    order = _get_order_for(db, order_id)
    order_state.apply_transition(
        db,
        order,
        OrderStatus.COMPLETED,
        user=actor,
        reason="Delivery confirmed; order closed out",
    )
    order.completed_at = datetime.now(timezone.utc)
    consume_reservations(db, order)
    db.commit()
    db.refresh(order)
    return order


def consume_reservations(db: Session, order: Order) -> None:
    """Called when the order completes: deduct reserved qty from listings."""
    for res in db.scalars(
        select(InventoryReservation).where(InventoryReservation.order_id == order.id)
    ):
        if res.status != ReservationStatus.ACTIVE:
            continue
        listing = db.get(ProduceListing, res.listing_id)
        if listing is not None:
            listing.quantity_total = round(
                max(0.0, listing.quantity_total - res.quantity), 2
            )
            listing.quantity_reserved = round(
                max(0.0, listing.quantity_reserved - res.quantity), 2
            )
            if listing.quantity_total <= 0:
                listing.status = ListingStatus.SOLD_OUT
        res.status = ReservationStatus.CONSUMED
