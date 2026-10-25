"""Role-specific profiles, FPOs, collection centres and vehicles."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base
from app.models.enums import (
    BusinessType,
    VerificationStatus,
    VehicleType,
)


def _enum(e, name: str):
    return Enum(e, name=name, native_enum=False)


class FarmerProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "farmer_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_farmer_profiles_user_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    village: Mapped[str] = mapped_column(String(120))
    district: Mapped[str] = mapped_column(String(120), index=True)
    state: Mapped[str] = mapped_column(String(120))
    farm_lat: Mapped[float | None]
    farm_lng: Mapped[float | None]
    fpo_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("fpo_profiles.id"), index=True
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        _enum(VerificationStatus, "verification_status"),
        default=VerificationStatus.PENDING,
        index=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    user = relationship("User", foreign_keys=[user_id])


class BuyerProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "buyer_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_buyer_profiles_user_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    address_line: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(120))
    district: Mapped[str | None] = mapped_column(String(120), index=True)
    state: Mapped[str | None] = mapped_column(String(120))
    pincode: Mapped[str | None] = mapped_column(String(10))
    lat: Mapped[float | None]
    lng: Mapped[float | None]

    user = relationship("User", foreign_keys=[user_id])


class BusinessProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "business_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_business_profiles_user_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    business_name: Mapped[str] = mapped_column(String(160))
    business_type: Mapped[BusinessType] = mapped_column(
        _enum(BusinessType, "business_type"), default=BusinessType.KIRANA
    )
    gstin: Mapped[str | None] = mapped_column(String(20))
    address_line: Mapped[str | None] = mapped_column(String(255))
    district: Mapped[str | None] = mapped_column(String(120), index=True)
    state: Mapped[str | None] = mapped_column(String(120))
    pincode: Mapped[str | None] = mapped_column(String(10))
    lat: Mapped[float | None]
    lng: Mapped[float | None]
    verification_status: Mapped[VerificationStatus] = mapped_column(
        _enum(VerificationStatus, "verification_status"),
        default=VerificationStatus.PENDING,
        index=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user = relationship("User", foreign_keys=[user_id])


class DriverProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "driver_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_driver_profiles_user_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    license_number: Mapped[str | None] = mapped_column(String(40))
    service_district: Mapped[str | None] = mapped_column(String(120), index=True)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        _enum(VerificationStatus, "verification_status"),
        default=VerificationStatus.PENDING,
        index=True,
    )
    # Availability toggle shown on the driver dashboard.
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    last_lat: Mapped[float | None]
    last_lng: Mapped[float | None]

    user = relationship("User", foreign_keys=[user_id])


class FpoProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fpo_profiles"

    name: Mapped[str] = mapped_column(String(180), index=True)
    registration_number: Mapped[str | None] = mapped_column(String(60), unique=True)
    district: Mapped[str] = mapped_column(String(120), index=True)
    state: Mapped[str] = mapped_column(String(120))
    address_line: Mapped[str | None] = mapped_column(String(255))
    lat: Mapped[float | None]
    lng: Mapped[float | None]
    verification_status: Mapped[VerificationStatus] = mapped_column(
        _enum(VerificationStatus, "verification_status"),
        default=VerificationStatus.PENDING,
        index=True,
    )


class CollectionCentre(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "collection_centres"

    fpo_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("fpo_profiles.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(180))
    district: Mapped[str] = mapped_column(String(120), index=True)
    state: Mapped[str] = mapped_column(String(120))
    address_line: Mapped[str | None] = mapped_column(String(255))
    lat: Mapped[float | None]
    lng: Mapped[float | None]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Vehicle(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "vehicles"

    driver_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    plate_number: Mapped[str] = mapped_column(String(20), unique=True)
    vehicle_type: Mapped[VehicleType] = mapped_column(
        _enum(VehicleType, "vehicle_type")
    )
    capacity_kg: Mapped[int] = mapped_column(Integer)
    service_district: Mapped[str | None] = mapped_column(String(120), index=True)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        _enum(VerificationStatus, "verification_status"),
        default=VerificationStatus.PENDING,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
