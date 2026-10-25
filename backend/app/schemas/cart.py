"""Cart schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CartItemAdd(BaseModel):
    listing_id: uuid.UUID
    quantity: float = Field(gt=0)


class CartItemUpdate(BaseModel):
    quantity: float = Field(gt=0)


class CartItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    listing_id: uuid.UUID
    quantity: float
    unit_price_paise: int
    line_total_paise: int = 0  # computed in the endpoint helper
    commodity_name: str | None = None
    farmer_district: str | None = None
    listing_status: str | None = None


class CartPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    buyer_id: uuid.UUID
    items: list[CartItemPublic]
    subtotal_paise: int = 0  # computed in the endpoint helper
    created_at: datetime
