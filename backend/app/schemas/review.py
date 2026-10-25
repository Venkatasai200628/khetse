"""Review schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    order_id: uuid.UUID
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class ReviewPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    reviewer_id: uuid.UUID
    reviewer_name: str | None = None
    farmer_id: uuid.UUID | None
    rating: int
    comment: str | None
    created_at: datetime
