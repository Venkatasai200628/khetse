"""Notification schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import NotificationChannel, NotificationStatus


class NotificationCreate(BaseModel):
    category: str = Field(max_length=60, examples=["order"])
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)
    channel: NotificationChannel = NotificationChannel.IN_APP
    language: str = Field(default="en", max_length=10)
    # Target user — defaults to the caller; only admins may target someone else.
    user_id: uuid.UUID | None = None
    related_order_id: uuid.UUID | None = None
    related_shipment_id: uuid.UUID | None = None
    meta: dict | None = None


class NotificationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    channel: NotificationChannel
    category: str
    title: str
    body: str
    language: str
    status: NotificationStatus
    read_at: datetime | None
    related_order_id: uuid.UUID | None
    related_shipment_id: uuid.UUID | None
    meta: dict | None
    created_at: datetime


class NotificationPage(BaseModel):
    items: list[NotificationPublic]
    total: int
    page: int
    page_size: int
    unread: int
