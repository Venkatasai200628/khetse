"""Business-buyer RFQ (request-for-quote) flow.

A BUSINESS buyer posts what they need in bulk (commodity, quantity, district,
needed-by); FARMERS quote against it from one of their ACTIVE listings; the
buyer accepts one offer, which — in a single transaction — accepts the offer,
reserves the listing stock (same pattern as cart checkout), opens an Order in
`payment_pending` (the farmer made the quote, so their confirmation is
implicit: CREATED → AWAITING_FARMER_CONFIRMATION → ACCEPTED → PAYMENT_PENDING
through the explicit state machine) and closes the purchase request.

Ownership is enforced server-side everywhere: only the buyer who owns the
request sees/accepts its offers, only the listing's own farmer can quote it,
and re-accepting an already-accepted offer is a 409 (idempotency guard backed
by the order's unique idempotency key).
"""

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.core.errors import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
)
from app.db.session import get_db
from app.models.catalog import Commodity, ProduceListing
from app.models.commerce import (
    InventoryReservation,
    Offer,
    Order,
    OrderItem,
    PurchaseRequest,
)
from app.models.enums import (
    FarmerResponseStatus,
    FulfilmentType,
    ListingStatus,
    OfferStatus,
    OrderStatus,
    PaymentStatus,
    PurchaseRequestStatus,
    ReservationStatus,
    RoleEnum,
    UnitEnum,
)
from app.models.profiles import FarmerProfile
from app.models.user import User
from app.schemas.order import OrderPublic
from app.services import order_state
from app.services.pricing import compute_order_money

router = APIRouter(prefix="/rfq", tags=["rfq"])


# --- Schemas -------------------------------------------------------------------


class RfqCreate(BaseModel):
    commodity_id: uuid.UUID
    quantity: float = Field(gt=0)
    unit: UnitEnum
    needed_by: date | None = None
    district: str | None = Field(default=None, max_length=120)
    max_price_paise: int | None = Field(default=None, ge=1)
    notes: str | None = Field(default=None, max_length=2000)


class OfferPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    purchase_request_id: uuid.UUID
    farmer_id: uuid.UUID
    farmer_name: str | None = None
    farmer_district: str | None = None
    listing_id: uuid.UUID | None = None
    quantity: float
    unit: UnitEnum
    price_paise: int
    # Derived (price × quantity), filled in by the serialisers — not a column.
    line_total_paise: int = 0
    status: OfferStatus
    message: str | None = None
    valid_until: datetime | None = None
    responded_at: datetime | None = None
    created_at: datetime


class PurchaseRequestPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_user_id: uuid.UUID
    commodity_id: uuid.UUID
    commodity_name: str | None = None
    quantity: float
    unit: UnitEnum
    needed_by: date | None = None
    district: str | None = None
    max_price_paise: int | None = None
    notes: str | None = None
    status: PurchaseRequestStatus
    created_at: datetime
    offers: list[OfferPublic] = []


class OfferCreate(BaseModel):
    listing_id: uuid.UUID
    quantity: float = Field(gt=0)
    unit: UnitEnum
    price_paise: int = Field(gt=0)
    message: str | None = Field(default=None, max_length=2000)
    valid_until: datetime | None = None


class OfferAcceptResponse(BaseModel):
    offer: OfferPublic
    order: OrderPublic


# --- Serialisation helpers -------------------------------------------------------


def _offer_public(db: Session, offer: Offer) -> OfferPublic:
    data = OfferPublic.model_validate(offer)
    data.line_total_paise = int(offer.price_paise * offer.quantity + 0.5)
    farmer = db.get(User, offer.farmer_id)
    if farmer is not None:
        data.farmer_name = farmer.full_name
    profile = db.scalar(
        select(FarmerProfile).where(FarmerProfile.user_id == offer.farmer_id)
    )
    if profile is not None:
        data.farmer_district = profile.district
    return data


def _offer_public_batch(
    db: Session, offers: list[Offer]
) -> list[OfferPublic]:
    """Bulk variant of :func:`_offer_public` (one query per table)."""
    if not offers:
        return []
    farmer_ids = {offer.farmer_id for offer in offers}
    profiles = {
        row.user_id: row
        for row in db.scalars(
            select(FarmerProfile).where(FarmerProfile.user_id.in_(farmer_ids))
        ).all()
    }
    names = {
        user.id: user.full_name
        for user in db.scalars(select(User).where(User.id.in_(farmer_ids))).all()
    }
    out = []
    for offer in offers:
        data = OfferPublic.model_validate(offer)
        data.line_total_paise = int(offer.price_paise * offer.quantity + 0.5)
        data.farmer_name = names.get(offer.farmer_id)
        profile = profiles.get(offer.farmer_id)
        if profile is not None:
            data.farmer_district = profile.district
        out.append(data)
    return out


def _purchase_request_public(db: Session, request: PurchaseRequest) -> PurchaseRequestPublic:
    commodity = db.get(Commodity, request.commodity_id)
    data = PurchaseRequestPublic.model_validate(request)
    if commodity is not None:
        data.commodity_name = commodity.name_en
    data.offers = _offer_public_batch(db, list(request.offers))
    return data


def _is_expired(valid_until: datetime | None, now: datetime) -> bool:
    """Timezone-tolerant expiry check (SQLite returns naive datetimes)."""
    if valid_until is None:
        return False
    if valid_until.tzinfo is None:
        valid_until = valid_until.replace(tzinfo=timezone.utc)
    return valid_until < now


def _get_request_or_404(db: Session, request_id: uuid.UUID) -> PurchaseRequest:
    request = db.get(PurchaseRequest, request_id)
    if request is None:
        raise NotFoundError("Purchase request not found.")
    return request


# --- Endpoints: buyer side ---------------------------------------------------------


@router.post("", response_model=PurchaseRequestPublic, status_code=201)
def create_purchase_request(
    body: RfqCreate,
    db: Session = Depends(get_db),
    business: User = Depends(require_roles(RoleEnum.BUSINESS)),
):
    """Business buyer opens an RFQ for bulk supply (status: open)."""
    commodity = db.get(Commodity, body.commodity_id)
    if commodity is None or not commodity.is_active:
        raise NotFoundError("Commodity not found.")

    request = PurchaseRequest(
        business_user_id=business.id,
        commodity_id=body.commodity_id,
        quantity=round(body.quantity, 2),
        unit=body.unit,
        needed_by=body.needed_by,
        district=(body.district or None),
        max_price_paise=body.max_price_paise,
        notes=body.notes,
        status=PurchaseRequestStatus.OPEN,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return _purchase_request_public(db, request)


@router.get("/mine", response_model=list[PurchaseRequestPublic])
def my_purchase_requests(
    db: Session = Depends(get_db),
    business: User = Depends(require_roles(RoleEnum.BUSINESS)),
):
    """The buyer's own RFQs with every offer received."""
    rows = db.scalars(
        select(PurchaseRequest)
        .where(PurchaseRequest.business_user_id == business.id)
        .order_by(PurchaseRequest.created_at.desc())
    ).all()
    return [_purchase_request_public(db, r) for r in rows]


@router.get("/{request_id}/offers", response_model=list[OfferPublic])
def request_offers(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    business: User = Depends(require_roles(RoleEnum.BUSINESS)),
):
    """Offer comparison view for the owning buyer only."""
    request = _get_request_or_404(db, request_id)
    if request.business_user_id != business.id:
        raise AuthorizationError("You can only view offers on your own requests.")
    return [_offer_public(db, offer) for offer in request.offers]


@router.post("/offers/{offer_id}/accept", response_model=OfferAcceptResponse)
def accept_offer(
    offer_id: uuid.UUID,
    db: Session = Depends(get_db),
    business: User = Depends(require_roles(RoleEnum.BUSINESS)),
):
    """Accept one farmer quote: reserve stock, open the order, close the RFQ.

    Atomic: offer, reservation, order (with its full CREATED → … →
    PAYMENT_PENDING transition trail) and the RFQ status all commit together;
    any failure rolls everything back. Accepting twice is a 409.
    """
    offer = db.get(Offer, offer_id)
    if offer is None:
        raise NotFoundError("Offer not found.")
    request = _get_request_or_404(db, offer.purchase_request_id)
    if request.business_user_id != business.id:
        raise AuthorizationError("You can only accept offers on your own requests.")
    if offer.status == OfferStatus.ACCEPTED:
        # Idempotency guard: a retried accept never double-fulfils.
        raise ConflictError("This offer has already been accepted.")
    if request.status != PurchaseRequestStatus.OPEN:
        raise ConflictError("This purchase request is no longer open.")
    if offer.status != OfferStatus.PENDING:
        raise ConflictError(
            f"This offer is no longer actionable (status '{offer.status.value}')."
        )
    now = datetime.now(timezone.utc)
    if _is_expired(offer.valid_until, now):
        raise ConflictError("This offer has expired.")

    listing = db.get(ProduceListing, offer.listing_id)
    if listing is None:
        raise NotFoundError("The quoted listing no longer exists.")

    try:
        # ---- single transaction: reserve → order → offer → RFQ ----
        listing = db.scalar(
            select(ProduceListing)
            .where(ProduceListing.id == offer.listing_id)
            .with_for_update()  # no-op on SQLite; row lock on PostgreSQL
        )
        available = round(listing.quantity_total - listing.quantity_reserved, 2)
        if listing.status != ListingStatus.ACTIVE or available < offer.quantity:
            raise ConflictError(
                "The listing no longer has enough quantity available.",
                details={
                    "listing_id": str(listing.id),
                    "requested": offer.quantity,
                    "available": available,
                },
            )
        listing.quantity_reserved = round(
            listing.quantity_reserved + offer.quantity, 2
        )

        subtotal_paise = int(offer.price_paise * offer.quantity + 0.5)
        money = compute_order_money(db, subtotal_paise)
        commodity = db.get(Commodity, listing.commodity_id)

        order = Order(
            buyer_id=business.id,
            status=OrderStatus.CREATED,
            payment_status=PaymentStatus.PENDING,
            fulfilment=FulfilmentType.DELIVERY,
            delivery_district=request.district,
            subtotal_paise=money.subtotal_paise,
            delivery_fee_paise=money.delivery_fee_paise,
            platform_fee_paise=money.platform_fee_paise,
            total_paise=money.total_paise,
            # Unique-key idempotency: even under a race, one offer ⇒ one order.
            idempotency_key=f"rfq-offer-{offer.id}",
            notes=(
                "RFQ offer accepted"
                + (f" for {commodity.name_en}" if commodity is not None else "")
            ),
            placed_at=now,
        )
        db.add(order)
        db.flush()  # order.id available

        db.add(
            OrderItem(
                order_id=order.id,
                listing_id=listing.id,
                farmer_id=offer.farmer_id,
                commodity_id=listing.commodity_id,
                quantity=offer.quantity,
                unit=offer.unit,
                unit_price_paise=offer.price_paise,
                line_total_paise=subtotal_paise,
                quality_grade=listing.quality_grade,
                # The farmer quoted this offer — their confirmation is implicit.
                farmer_response=FarmerResponseStatus.ACCEPTED,
            )
        )
        db.add(
            InventoryReservation(
                order_id=order.id,
                listing_id=listing.id,
                quantity=offer.quantity,
                status=ReservationStatus.ACTIVE,
            )
        )

        # The farmer already offered to sell, so the order walks the standard
        # path to payment_pending. The state machine reserves the
        # AWAITING_FARMER_CONFIRMATION → ACCEPTED hop for the farmer role —
        # the quoting farmer's standing offer IS that acceptance, so it is
        # applied with the farmer as the recorded actor; the other hops are
        # pure system steps.
        farmer = db.get(User, offer.farmer_id)
        order_state.apply_transition(
            db,
            order,
            OrderStatus.AWAITING_FARMER_CONFIRMATION,
            role_override="system",
            reason="RFQ offer accepted",
        )
        order_state.apply_transition(
            db,
            order,
            OrderStatus.ACCEPTED,
            user=farmer,
            reason="RFQ offer accepted (farmer quote)",
        )
        order_state.apply_transition(
            db,
            order,
            OrderStatus.PAYMENT_PENDING,
            role_override="system",
            reason="RFQ offer accepted; awaiting payment",
        )

        offer.status = OfferStatus.ACCEPTED
        offer.responded_at = now
        request.status = PurchaseRequestStatus.CLOSED

        db.commit()
        db.refresh(order)
        db.refresh(offer)
        return OfferAcceptResponse(
            offer=_offer_public(db, offer),
            order=OrderPublic.model_validate(order),
        )
    except Exception:
        db.rollback()
        raise


# --- Endpoints: farmer side ---------------------------------------------------------


@router.get("/open", response_model=list[PurchaseRequestPublic])
def open_purchase_requests(
    db: Session = Depends(get_db),
    _farmer: User = Depends(require_roles(RoleEnum.FARMER)),
):
    """Every still-open RFQ, for farmers looking to quote.

    Other farmers' quotes are sensitive — the open list never includes
    competing offers; farmers see only their own via their quotes.
    """
    rows = db.scalars(
        select(PurchaseRequest)
        .where(PurchaseRequest.status == PurchaseRequestStatus.OPEN)
        .order_by(PurchaseRequest.created_at.desc())
    ).all()
    results = []
    for request in rows:
        data = _purchase_request_public(db, request)
        data.offers = []
        results.append(data)
    return results


@router.post("/{request_id}/offers", response_model=OfferPublic, status_code=201)
def create_offer(
    request_id: uuid.UUID,
    body: OfferCreate,
    db: Session = Depends(get_db),
    farmer: User = Depends(require_roles(RoleEnum.FARMER)),
):
    """Quote an open RFQ from one of the farmer's own ACTIVE listings."""
    request = _get_request_or_404(db, request_id)
    if request.status != PurchaseRequestStatus.OPEN:
        raise ConflictError("This purchase request is no longer open.")

    listing = db.get(ProduceListing, body.listing_id)
    if listing is None:
        raise NotFoundError("Listing not found.")
    if listing.farmer_id != farmer.id:
        raise AuthorizationError("You can only quote from your own listings.")
    if listing.status != ListingStatus.ACTIVE:
        raise ConflictError("Only active listings can be quoted.")
    available = round(listing.quantity_total - listing.quantity_reserved, 2)
    if available < body.quantity:
        raise ConflictError(
            "The listing does not have enough quantity available.",
            details={
                "listing_id": str(listing.id),
                "requested": body.quantity,
                "available": available,
            },
        )

    offer = Offer(
        purchase_request_id=request.id,
        farmer_id=farmer.id,
        listing_id=listing.id,
        quantity=round(body.quantity, 2),
        unit=body.unit,
        price_paise=body.price_paise,
        message=body.message,
        status=OfferStatus.PENDING,
        valid_until=body.valid_until,
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return _offer_public(db, offer)
