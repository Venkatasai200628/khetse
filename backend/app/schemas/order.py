"""Order schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    FarmerResponseStatus,
    FulfilmentType,
    OrderStatus,
    PaymentStatus,
)


class CheckoutRequest(BaseModel):
    idempotency_key: str | None = Field(default=None, max_length=80)
    fulfilment: FulfilmentType = FulfilmentType.DELIVERY
    delivery_name: str | None = None
    delivery_phone: str | None = None
    delivery_address: str | None = None
    delivery_district: str | None = None
    delivery_lat: float | None = None
    delivery_lng: float | None = None
    notes: str | None = None


class FarmerResponse(BaseModel):
    accept: bool
    reason: str | None = None


class CancelRequest(BaseModel):
    reason: str | None = None


class OrderItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    listing_id: uuid.UUID
    farmer_id: uuid.UUID
    commodity_id: uuid.UUID | None
    quantity: float
    unit: str | None
    unit_price_paise: int
    line_total_paise: int
    quality_grade: str | None
    farmer_response: FarmerResponseStatus = FarmerResponseStatus.PENDING
    commodity_name: str | None = None


class OrderStatusEventPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    from_status: OrderStatus | None
    to_status: OrderStatus
    actor_role: str | None
    reason: str | None
    created_at: datetime


class OrderPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    buyer_id: uuid.UUID
    status: OrderStatus
    payment_status: PaymentStatus
    fulfilment: FulfilmentType
    delivery_name: str | None
    delivery_address: str | None
    delivery_district: str | None
    subtotal_paise: int
    delivery_fee_paise: int
    platform_fee_paise: int
    total_paise: int
    currency: str
    notes: str | None
    cancel_reason: str | None
    placed_at: datetime | None
    delivered_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    is_synthetic: bool
    created_at: datetime
    items: list[OrderItemPublic] = []
    status_events: list[OrderStatusEventPublic] = []


class OrderPage(BaseModel):
    items: list[OrderPublic]
    total: int
    page: int
    page_size: int
