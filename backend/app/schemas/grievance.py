"""Grievance schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import GrievanceCategory, GrievanceStatus


class GrievanceCreate(BaseModel):
    category: GrievanceCategory = GrievanceCategory.OTHER
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=3)
    order_id: uuid.UUID | None = None
    shipment_id: uuid.UUID | None = None


class GrievancePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    raised_by: uuid.UUID
    category: GrievanceCategory
    order_id: uuid.UUID | None
    shipment_id: uuid.UUID | None
    subject: str
    description: str
    status: GrievanceStatus
    ack_deadline_at: datetime | None
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    resolution_notes: str | None
    created_at: datetime


class GrievancePage(BaseModel):
    items: list[GrievancePublic]
    total: int
    page: int
    page_size: int
