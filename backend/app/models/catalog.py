"""Commodity catalogue and farmer produce listings."""

import uuid
from datetime import date

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base
from app.models.enums import (
    CommodityCategory,
    ListingStatus,
    QualityGrade,
    UnitEnum,
)


def _enum(e, name: str):
    return Enum(e, name=name, native_enum=False)


class Commodity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "commodities"

    name_en: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name_te: Mapped[str | None] = mapped_column(String(80))
    name_hi: Mapped[str | None] = mapped_column(String(80))
    category: Mapped[CommodityCategory] = mapped_column(
        _enum(CommodityCategory, "commodity_category"),
        default=CommodityCategory.VEGETABLE,
        index=True,
    )
    default_unit: Mapped[UnitEnum] = mapped_column(
        _enum(UnitEnum, "unit_enum"), default=UnitEnum.KG
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    varieties: Mapped[list["CommodityVariety"]] = relationship(
        back_populates="commodity", cascade="all, delete-orphan"
    )


class CommodityVariety(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "commodity_varieties"

    commodity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("commodities.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)

    commodity: Mapped[Commodity] = relationship(back_populates="varieties")


class ProduceListing(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "produce_listings"
    __table_args__ = (
        Index(
            "ix_produce_listings_status_commodity",
            "status",
            "commodity_id",
        ),
    )

    farmer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    commodity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("commodities.id"), index=True
    )
    variety_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("commodity_varieties.id")
    )
    collection_centre_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("collection_centres.id"), index=True
    )

    description: Mapped[str | None] = mapped_column(Text)
    quantity_total: Mapped[float]  # in `unit`
    quantity_reserved: Mapped[float] = mapped_column(default=0.0)
    unit: Mapped[UnitEnum] = mapped_column(_enum(UnitEnum, "unit_enum"))
    quality_grade: Mapped[QualityGrade] = mapped_column(
        _enum(QualityGrade, "quality_grade"), default=QualityGrade.UNGRADED
    )
    harvest_date: Mapped[date | None] = mapped_column(Date)
    available_from: Mapped[date | None] = mapped_column(Date)

    # Farmer's minimum acceptable price and asking price per unit (paise).
    min_price_paise: Mapped[int] = mapped_column(Integer)
    listed_price_paise: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="INR")

    status: Mapped[ListingStatus] = mapped_column(
        _enum(ListingStatus, "listing_status"),
        default=ListingStatus.ACTIVE,
        index=True,
    )
    farm_lat: Mapped[float | None]
    farm_lng: Mapped[float | None]

    # Demo/seed data is always flagged so it can be visually labelled.
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)

    farmer = relationship("User")
    commodity = relationship("Commodity")
    images: Mapped[list["ListingImage"]] = relationship(
        back_populates="listing", cascade="all, delete-orphan"
    )

    @property
    def quantity_available(self) -> float:
        return round(self.quantity_total - self.quantity_reserved, 2)


class ListingImage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "listing_images"

    listing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("produce_listings.id", ondelete="CASCADE"), index=True
    )
    image_path: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str | None] = mapped_column(String(60))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    listing: Mapped[ProduceListing] = relationship(back_populates="images")
