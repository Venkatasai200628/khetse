"""Notifications, communication logs, grievances, reviews, audit, settings."""

import uuid
from datetime import datetime

from sqlalchemy import (
    func,
    JSON,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base
from app.models.enums import (
    CommunicationStatus,
    GrievanceCategory,
    GrievanceStatus,
    NotificationChannel,
    NotificationStatus,
)


def _enum(e, name: str):
    return Enum(e, name=name, native_enum=False)


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_status", "user_id", "status"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        _enum(NotificationChannel, "notification_channel"),
        default=NotificationChannel.IN_APP,
    )
    category: Mapped[str] = mapped_column(String(60), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(10), default="en")
    status: Mapped[NotificationStatus] = mapped_column(
        _enum(NotificationStatus, "notification_status"),
        default=NotificationStatus.QUEUED,
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    related_order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id"))
    related_shipment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("shipments.id")
    )
    meta: Mapped[dict | None] = mapped_column(JSON)


class CommunicationLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Outbound SMS/voice attempts with retries and provider results."""

    __tablename__ = "communication_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    notification_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("notifications.id")
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        _enum(NotificationChannel, "notification_channel")
    )
    provider: Mapped[str] = mapped_column(String(40), default="mock")
    provider_message_id: Mapped[str | None] = mapped_column(String(120))
    recipient: Mapped[str | None] = mapped_column(String(30))  # phone — masked in APIs
    content: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(10), default="en")
    status: Mapped[CommunicationStatus] = mapped_column(
        _enum(CommunicationStatus, "communication_status"),
        default=CommunicationStatus.QUEUED,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)


class Grievance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "grievances"
    __table_args__ = (Index("ix_grievances_status_created", "status", "created_at"),)

    raised_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[GrievanceCategory] = mapped_column(
        _enum(GrievanceCategory, "grievance_category")
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id"), index=True)
    shipment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("shipments.id"), index=True
    )
    subject: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[GrievanceStatus] = mapped_column(
        _enum(GrievanceStatus, "grievance_status"),
        default=GrievanceStatus.OPEN,
        index=True,
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    # Complaint acknowledgement deadline (admin SLA), then resolution.
    ack_deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_notes: Mapped[str | None] = mapped_column(Text)


class Review(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_reviews_order_id"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating_range"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    farmer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text)


class AuditLog(UUIDPrimaryKeyMixin, Base):
    """Append-only trail for administrative and financial actions."""

    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_id"),)

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    actor_role: Mapped[str | None] = mapped_column(String(30))
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(60), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(64))
    before: Mapped[dict | None] = mapped_column(JSON)
    after: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PlatformSetting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Runtime-configurable business rules (fees, limits, toggles)."""

    __tablename__ = "platform_settings"

    key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    value: Mapped[dict | None] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(String(255))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
