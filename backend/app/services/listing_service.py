"""Farmer produce listings: creation, edits, lifecycle, browsing."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, ValidationAppError
from app.models.catalog import Commodity, ProduceListing
from app.models.commerce import InventoryReservation
from app.models.enums import ListingStatus, ReservationStatus
from app.models.profiles import FarmerProfile
from app.models.user import User


def _validate_money(min_price_paise: int, listed_price_paise: int) -> None:
    if min_price_paise <= 0 or listed_price_paise <= 0:
        raise ValidationAppError("Prices must be positive (in paise).")
    if min_price_paise > listed_price_paise:
        raise ValidationAppError(
            "Minimum acceptable price cannot exceed the listed price."
        )


def create_listing(
    db: Session,
    farmer: User,
    *,
    commodity_id: uuid.UUID,
    quantity_total: float,
    unit: str,
    min_price_paise: int,
    listed_price_paise: int,
    description: str | None = None,
    quality_grade: str = "ungraded",
    harvest_date=None,
    available_from=None,
    variety_id: uuid.UUID | None = None,
    collection_centre_id: uuid.UUID | None = None,
    farm_lat: float | None = None,
    farm_lng: float | None = None,
    is_synthetic: bool = False,
) -> ProduceListing:
    if quantity_total <= 0:
        raise ValidationAppError("Quantity must be positive.")
    _validate_money(min_price_paise, listed_price_paise)

    commodity = db.get(Commodity, commodity_id)
    if commodity is None or not commodity.is_active:
        raise NotFoundError("Commodity not found or inactive.")

    listing = ProduceListing(
        farmer_id=farmer.id,
        commodity_id=commodity_id,
        variety_id=variety_id,
        collection_centre_id=collection_centre_id,
        description=description,
        quantity_total=round(float(quantity_total), 2),
        unit=unit,
        quality_grade=quality_grade,
        harvest_date=harvest_date,
        available_from=available_from,
        min_price_paise=min_price_paise,
        listed_price_paise=listed_price_paise,
        farm_lat=farm_lat,
        farm_lng=farm_lng,
        status=ListingStatus.ACTIVE,
        is_synthetic=is_synthetic,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def _active_reservation_qty(db: Session, listing_id: uuid.UUID) -> float:
    total = db.scalar(
        select(func.coalesce(func.sum(InventoryReservation.quantity), 0.0)).where(
            InventoryReservation.listing_id == listing_id,
            InventoryReservation.status.in_(
                [ReservationStatus.ACTIVE, ReservationStatus.CONSUMED]
            ),
        )
    )
    return float(total or 0.0)


def set_listing_status(
    db: Session, farmer: User, listing_id: uuid.UUID, new_status: ListingStatus
) -> ProduceListing:
    listing = db.get(ProduceListing, listing_id)
    if listing is None:
        raise NotFoundError("Listing not found.")
    if listing.farmer_id != farmer.id:
        raise ConflictError("You can only manage your own listings.")

    reserved = _active_reservation_qty(db, listing_id)
    if new_status in (ListingStatus.WITHDRAWN, ListingStatus.PAUSED) and reserved > 0:
        raise ConflictError(
            "Listing has quantity tied to confirmed orders and cannot be "
            "paused or withdrawn.",
            details={"reserved_quantity": reserved},
        )

    listing.status = new_status
    if new_status == ListingStatus.WITHDRAWN:
        # Release nothing (no active reservations by the check above).
        pass
    db.commit()
    db.refresh(listing)
    return listing


def browse_listings(
    db: Session,
    *,
    category: str | None = None,
    commodity_id: uuid.UUID | None = None,
    district: str | None = None,
    quality_grade: str | None = None,
    max_price_paise: int | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list, int]:
    """Active listings with optional filters; returns (rows, total_count)."""
    q = (
        select(ProduceListing)
        .join(Commodity, ProduceListing.commodity_id == Commodity.id)
        .where(ProduceListing.status == ListingStatus.ACTIVE)
    )
    if category:
        q = q.where(Commodity.category == category)
    if commodity_id:
        q = q.where(ProduceListing.commodity_id == commodity_id)
    if district:
        q = q.join(
            FarmerProfile, FarmerProfile.user_id == ProduceListing.farmer_id
        ).where(FarmerProfile.district == district)
    if quality_grade:
        q = q.where(ProduceListing.quality_grade == quality_grade)
    if max_price_paise:
        q = q.where(ProduceListing.listed_price_paise <= max_price_paise)
    if search:
        q = q.where(Commodity.name_en.ilike(f"%{search}%"))

    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(
        q.order_by(ProduceListing.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), int(total)
