"""Carts, orders (state machine), business RFQs, offers and inventory."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    func,
    Boolean,
    Date,
    DateTime,
    Enum,
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
    FarmerResponseStatus,
    FulfilmentType,
    OfferStatus,
    OrderStatus,
    PaymentStatus,
    PurchaseRequestStatus,
    QualityGrade,
    ReservationStatus,
    UnitEnum,
)


def _enum(e, name: str):
    return Enum(e, name=name, native_enum=False)


class Cart(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "carts"
    __table_args__ = (UniqueConstraint("buyer_id", name="uq_carts_buyer_id"),)

    buyer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)

    items: Mapped[list["CartItem"]] = relationship(
        back_populates="cart", cascade="all, delete-orphan"
    )


class CartItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("cart_id", "listing_id", name="uq_cart_items_cart_listing"),
    )

    cart_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("carts.id"), index=True)
    listing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("produce_listings.id"), index=True
    )
    quantity: Mapped[float]
    # Price snapshot when added, so later listing edits don't rewrite history.
    unit_price_paise: Mapped[int] = mapped_column(Integer)

    cart: Mapped[Cart] = relationship(back_populates="items")
    listing = relationship("ProduceListing")


class Order(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        # Idempotency: a client retry can never create a duplicate order.
        UniqueConstraint("idempotency_key", name="uq_orders_idempotency_key"),
        Index("ix_orders_buyer_status_created", "buyer_id", "status", "created_at"),
        Index("ix_orders_status_created", "status", "created_at"),
    )

    buyer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[OrderStatus] = mapped_column(
        _enum(OrderStatus, "order_status"),
        default=OrderStatus.CREATED,
        index=True,
    )

    # Payment tracked separately — a delivered order is not proof of settlement.
    payment_status: Mapped[PaymentStatus] = mapped_column(
        _enum(PaymentStatus, "payment_status"),
        default=PaymentStatus.INITIATED,
        index=True,
    )

    fulfilment: Mapped[FulfilmentType] = mapped_column(
        _enum(FulfilmentType, "fulfilment_type"), default=FulfilmentType.DELIVERY
    )
    # Delivery address snapshot at order time.
    delivery_name: Mapped[str | None] = mapped_column(String(160))
    delivery_phone: Mapped[str | None] = mapped_column(String(20))
    delivery_address: Mapped[str | None] = mapped_column(String(400))
    delivery_district: Mapped[str | None] = mapped_column(String(120), index=True)
    delivery_lat: Mapped[float | None]
    delivery_lng: Mapped[float | None]

    # Money breakdown — all integer paise.
    subtotal_paise: Mapped[int] = mapped_column(Integer, default=0)
    delivery_fee_paise: Mapped[int] = mapped_column(Integer, default=0)
    platform_fee_paise: Mapped[int] = mapped_column(Integer, default=0)
    total_paise: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="INR")

    idempotency_key: Mapped[str | None] = mapped_column(String(80), index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    cancel_reason: Mapped[str | None] = mapped_column(Text)

    placed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)

    buyer = relationship("User", foreign_keys=[buyer_id])
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    status_events: Mapped[list["OrderStatusEvent"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "order_items"

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("produce_listings.id"), index=True
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    commodity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("commodities.id")
    )

    quantity: Mapped[float]
    unit: Mapped[UnitEnum | None] = mapped_column(_enum(UnitEnum, "unit_enum"))
    unit_price_paise: Mapped[int] = mapped_column(Integer)
    line_total_paise: Mapped[int] = mapped_column(Integer)
    quality_grade: Mapped[QualityGrade | None] = mapped_column(
        _enum(QualityGrade, "quality_grade")
    )
    # Per-farmer response so multi-farmer orders only move forward once every
    # farmer in the order has answered.
    farmer_response: Mapped[FarmerResponseStatus] = mapped_column(
        _enum(FarmerResponseStatus, "farmer_response_status"),
        default=FarmerResponseStatus.PENDING,
        index=True,
    )

    order: Mapped[Order] = relationship(back_populates="items")


class OrderStatusEvent(UUIDPrimaryKeyMixin, Base):
    """Audit record for every order state transition."""

    __tablename__ = "order_status_events"
    __table_args__ = (
        Index("ix_ose_order_created", "order_id", "created_at"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    from_status: Mapped[OrderStatus | None] = mapped_column(
        _enum(OrderStatus, "order_status")
    )
    to_status: Mapped[OrderStatus] = mapped_column(_enum(OrderStatus, "order_status"))
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    actor_role: Mapped[str | None] = mapped_column(String(30))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    order: Mapped[Order] = relationship(back_populates="status_events")


class PurchaseRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Business buyer RFQ: request-for-quote for bulk/recurring supply."""

    __tablename__ = "purchase_requests"

    business_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    commodity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("commodities.id"), index=True
    )
    quantity: Mapped[float]
    unit: Mapped[UnitEnum] = mapped_column(_enum(UnitEnum, "unit_enum"))
    needed_by: Mapped[date | None] = mapped_column(Date)
    district: Mapped[str | None] = mapped_column(String(120), index=True)
    max_price_paise: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[PurchaseRequestStatus] = mapped_column(
        _enum(PurchaseRequestStatus, "purchase_request_status"),
        default=PurchaseRequestStatus.OPEN,
        index=True,
    )

    offers: Mapped[list["Offer"]] = relationship(
        back_populates="purchase_request", cascade="all, delete-orphan"
    )


class Offer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "offers"

    purchase_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchase_requests.id"), index=True
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    listing_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("produce_listings.id")
    )
    quantity: Mapped[float]
    unit: Mapped[UnitEnum] = mapped_column(_enum(UnitEnum, "unit_enum"))
    price_paise: Mapped[int] = mapped_column(Integer)  # per unit
    message: Mapped[str | None] = mapped_column(Text)
    status: Mapped[OfferStatus] = mapped_column(
        _enum(OfferStatus, "offer_status"), default=OfferStatus.PENDING, index=True
    )
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    purchase_request: Mapped[PurchaseRequest] = relationship(back_populates="offers")


class InventoryReservation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Reserves listing quantity between acceptance and delivery.

    Prevents overselling: quantity_reserved on the listing is the sum of
    ACTIVE/CONSUMED reservations minus released ones (maintained in services
    inside the same DB transaction).
    """

    __tablename__ = "inventory_reservations"
    __table_args__ = (
        UniqueConstraint("order_id", "listing_id", name="uq_res_order_listing"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("produce_listings.id"), index=True
    )
    quantity: Mapped[float]
    status: Mapped[ReservationStatus] = mapped_column(
        _enum(ReservationStatus, "reservation_status"),
        default=ReservationStatus.ACTIVE,
        index=True,
    )
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
