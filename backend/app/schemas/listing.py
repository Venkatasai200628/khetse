"""Listing schemas. Monetary fields are integer paise (₹1 = 100)."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ListingStatus


class ListingCreate(BaseModel):
    commodity_id: uuid.UUID
    variety_id: uuid.UUID | None = None
    collection_centre_id: uuid.UUID | None = None
    quantity_total: float = Field(gt=0)
    unit: str = Field(pattern="^(kg|quintal|tonne|dozen|piece|litre|bunch)$")
    min_price_paise: int = Field(gt=0)
    listed_price_paise: int = Field(gt=0)
    quality_grade: str = Field(default="ungraded", pattern="^(A|B|C|ungraded)$")
    harvest_date: date | None = None
    available_from: date | None = None
    description: str | None = None
    farm_lat: float | None = None
    farm_lng: float | None = None


class ListingStatusUpdate(BaseModel):
    status: ListingStatus  # paused | active | withdrawn


class ListingPublic(BaseModel):
    """What any authenticated buyer may see. Exact farm coordinates are
    deliberately excluded — buyers get village/district only."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    farmer_id: uuid.UUID
    commodity_id: uuid.UUID
    variety_id: uuid.UUID | None
    description: str | None
    quantity_total: float
    quantity_available: float
    unit: str
    quality_grade: str
    harvest_date: date | None
    available_from: date | None
    min_price_paise: int
    listed_price_paise: int
    currency: str
    status: ListingStatus
    is_synthetic: bool
    created_at: datetime
    commodity_name: str | None = None
    commodity_name_te: str | None = None
    commodity_category: str | None = None
    farmer_district: str | None = None
    farmer_village: str | None = None


class ListingOwnerPublic(ListingPublic):
    """Owner-scoped view (the farmer's own listings): includes the exact
    farm coordinates the farmer entered, which the platform uses for
    logistics but never shows to buyers."""

    farm_lat: float | None
    farm_lng: float | None


class ListingPage(BaseModel):
    items: list[ListingPublic]
    total: int
    page: int
    page_size: int
