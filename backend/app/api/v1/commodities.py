"""Commodity catalogue endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.catalog import Commodity
from app.models.user import User

router = APIRouter(prefix="/commodities", tags=["commodities"])


class CommodityOut(BaseModel):
    id: str
    name_en: str
    name_te: str | None
    name_hi: str | None
    category: str
    default_unit: str
    is_active: bool


@router.get("", response_model=list[CommodityOut])
def list_commodities(
    category: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    q = select(Commodity).where(Commodity.is_active.is_(True))
    if category:
        q = q.where(Commodity.category == category)
    rows = db.scalars(q.order_by(Commodity.name_en)).all()
    return [
        CommodityOut(
            id=str(r.id),
            name_en=r.name_en,
            name_te=r.name_te,
            name_hi=r.name_hi,
            category=r.category.value,
            default_unit=r.default_unit.value,
            is_active=r.is_active,
        )
        for r in rows
    ]
