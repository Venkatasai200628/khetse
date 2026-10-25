"""Shipments, stops, manifests, crate labels and QR verification."""

import uuid
from datetime import datetime

from sqlalchemy import (
    func,
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base
from app.models.enums import (
    CrateStatus,
    QrMethod,
    QrPurpose,
    ShipmentStatus,
    StopStatus,
    StopType,
)


def _enum(e, name: str):
    return Enum(e, name=name, native_enum=False)


class Shipment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A consolidated delivery run: multiple pickups + multiple drop-offs."""

    __tablename__ = "shipments"

    driver_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vehicles.id"))
    collection_centre_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("collection_centres.id"), index=True
    )

    status: Mapped[ShipmentStatus] = mapped_column(
        _enum(ShipmentStatus, "shipment_status"),
        default=ShipmentStatus.PLANNED,
        index=True,
    )
    planned_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    route_distance_km: Mapped[float | None] = mapped_column(Float)
    route_duration_min: Mapped[int | None] = mapped_column(Integer)
    # Solver output: stop order, objective, constraints, unserved stops.
    route_data: Mapped[dict | None] = mapped_column(JSON)
    solver: Mapped[str | None] = mapped_column(String(40))  # ortools | nearest_neighbour

    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)

    driver = relationship("User")
    stops: Mapped[list["ShipmentStop"]] = relationship(
        back_populates="shipment", cascade="all, delete-orphan"
    )
    crates: Mapped[list["CrateLabel"]] = relationship(
        back_populates="shipment", cascade="all, delete-orphan"
    )


class ShipmentStop(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shipment_stops"
    __table_args__ = (
        UniqueConstraint("shipment_id", "sequence", name="uq_stops_shipment_sequence"),
        Index("ix_stops_shipment_status", "shipment_id", "status"),
    )

    shipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shipments.id", ondelete="CASCADE"), index=True
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id"), index=True
    )  # null for pickup stops, set for delivery stops
    stop_type: Mapped[StopType] = mapped_column(_enum(StopType, "stop_type"))
    sequence: Mapped[int] = mapped_column(Integer)
    status: Mapped[StopStatus] = mapped_column(
        _enum(StopStatus, "stop_status"), default=StopStatus.PENDING
    )

    lat: Mapped[float | None]
    lng: Mapped[float | None]
    # Privacy-safe label only — drivers never see full personal details.
    label: Mapped[str] = mapped_column(String(160))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str | None] = mapped_column(Text)

    shipment: Mapped[Shipment] = relationship(back_populates="stops")


class DeliveryManifest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "delivery_manifests"
    __table_args__ = (
        UniqueConstraint("shipment_id", name="uq_manifests_shipment_id"),
    )

    shipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shipments.id", ondelete="CASCADE"), index=True
    )
    manifest_number: Mapped[str] = mapped_column(String(30), unique=True)
    content: Mapped[dict | None] = mapped_column(JSON)  # stops, order IDs, crates
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CrateLabel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Physical crate tag: unpredictable public code + secret QR token.

    The QR payload contains only the opaque token — never personal data or
    access tokens with broader rights.
    """

    __tablename__ = "crate_labels"

    shipment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("shipments.id", ondelete="CASCADE"), index=True
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id"), index=True
    )
    listing_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("produce_listings.id"), index=True
    )
    commodity_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("commodities.id"))
    quantity: Mapped[float | None]
    unit: Mapped[str | None] = mapped_column(String(20))
    grade: Mapped[str | None] = mapped_column(String(20))

    code: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    qr_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[CrateStatus] = mapped_column(
        _enum(CrateStatus, "crate_status"), default=CrateStatus.CREATED
    )
    picked_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    shipment: Mapped[Shipment | None] = relationship(back_populates="crates")


class QrVerificationEvent(UUIDPrimaryKeyMixin, Base):
    """Immutable log of every QR/manual verification attempt (incl. failures)."""

    __tablename__ = "qr_verification_events"
    __table_args__ = (
        Index("ix_qr_stop_purpose", "stop_id", "purpose"),
    )

    qr_code: Mapped[str] = mapped_column(String(64), index=True)
    purpose: Mapped[QrPurpose] = mapped_column(_enum(QrPurpose, "qr_purpose"))
    method: Mapped[QrMethod] = mapped_column(
        _enum(QrMethod, "qr_method"), default=QrMethod.QR_SCAN
    )
    shipment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("shipments.id"), index=True
    )
    stop_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("shipment_stops.id"), index=True
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id"))
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
