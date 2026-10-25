"""Listing endpoints: farmer CRUD + buyer browsing."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.catalog import Commodity, ProduceListing
from app.models.enums import ListingStatus, RoleEnum
from app.models.profiles import FarmerProfile
from app.models.user import User
from app.schemas.listing import (
    ListingCreate,
    ListingOwnerPublic,
    ListingPage,
    ListingPublic,
    ListingStatusUpdate,
)
from app.services import listing_service

router = APIRouter(prefix="/listings", tags=["listings"])


def _apply_catalog_fields(data: ListingPublic, listing: ProduceListing, db: Session) -> None:
    commodity = db.get(Commodity, listing.commodity_id)
    farmer_profile = db.scalar(
        select(FarmerProfile).where(FarmerProfile.user_id == listing.farmer_id)
    )
    if commodity is not None:
        data.commodity_name = commodity.name_en
        data.commodity_name_te = commodity.name_te
        data.commodity_category = commodity.category.value
    if farmer_profile is not None:
        # Privacy: buyers see village/district, never exact farm coordinates
        # or contact details.
        data.farmer_district = farmer_profile.district
        data.farmer_village = farmer_profile.village


def _to_public(listing: ProduceListing, db: Session) -> ListingPublic:
    """Buyer-safe view: no farm coordinates."""
    data = ListingPublic.model_validate(listing)
    _apply_catalog_fields(data, listing, db)
    return data


def _to_owner_public(listing: ProduceListing, db: Session) -> ListingOwnerPublic:
    """Owner view for the farmer's own listings: includes farm coordinates."""
    data = ListingOwnerPublic.model_validate(listing)
    _apply_catalog_fields(data, listing, db)
    return data


@router.get("", response_model=ListingPage)
def browse(
    category: str | None = None,
    commodity_id: uuid.UUID | None = None,
    district: str | None = None,
    quality_grade: str | None = None,
    max_price_paise: int | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rows, total = listing_service.browse_listings(
        db,
        category=category,
        commodity_id=commodity_id,
        district=district,
        quality_grade=quality_grade,
        max_price_paise=max_price_paise,
        search=search,
        page=page,
        page_size=page_size,
    )
    return ListingPage(
        items=[_to_public(r, db) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/mine", response_model=list[ListingOwnerPublic])
def my_listings(
    db: Session = Depends(get_db),
    farmer: User = Depends(require_roles(RoleEnum.FARMER)),
):
    rows = db.scalars(
        select(ProduceListing)
        .where(ProduceListing.farmer_id == farmer.id)
        .order_by(ProduceListing.created_at.desc())
    ).all()
    return [_to_owner_public(r, db) for r in rows]


@router.post("", response_model=ListingOwnerPublic, status_code=201)
def create_listing(
    body: ListingCreate,
    db: Session = Depends(get_db),
    farmer: User = Depends(require_roles(RoleEnum.FARMER)),
):
    listing = listing_service.create_listing(
        db,
        farmer,
        commodity_id=body.commodity_id,
        quantity_total=body.quantity_total,
        unit=body.unit,
        min_price_paise=body.min_price_paise,
        listed_price_paise=body.listed_price_paise,
        description=body.description,
        quality_grade=body.quality_grade,
        harvest_date=body.harvest_date,
        available_from=body.available_from,
        variety_id=body.variety_id,
        collection_centre_id=body.collection_centre_id,
        farm_lat=body.farm_lat,
        farm_lng=body.farm_lng,
    )
    return _to_owner_public(listing, db)


@router.get("/{listing_id}", response_model=ListingPublic)
def get_listing(
    listing_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    listing = db.get(ProduceListing, listing_id)
    if listing is None:
        from app.core.errors import NotFoundError

        raise NotFoundError("Listing not found.")
    return _to_public(listing, db)


@router.patch("/{listing_id}/status", response_model=ListingOwnerPublic)
def update_status(
    listing_id: uuid.UUID,
    body: ListingStatusUpdate,
    db: Session = Depends(get_db),
    farmer: User = Depends(require_roles(RoleEnum.FARMER, RoleEnum.FPO_OPERATOR)),
):
    listing = listing_service.set_listing_status(db, farmer, listing_id, body.status)
    return _to_owner_public(listing, db)
