"""Payments, webhooks, double-entry ledger, settlements and refunds."""

import uuid
from datetime import datetime

from sqlalchemy import (
    func,
    JSON,
    Boolean,
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
    LedgerEntryType,
    PaymentProviderKind,
    PaymentStatus,
    RefundStatus,
    SettlementStatus,
)


def _enum(e, name: str):
    return Enum(e, name=name, native_enum=False)


class PaymentTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payment_transactions"
    __table_args__ = (
        Index("ix_paytxn_order_status", "order_id", "status"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id"), index=True
    )
    provider: Mapped[PaymentProviderKind] = mapped_column(
        _enum(PaymentProviderKind, "payment_provider_kind")
    )
    provider_ref: Mapped[str | None] = mapped_column(String(100), unique=True)
    amount_paise: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    status: Mapped[PaymentStatus] = mapped_column(
        _enum(PaymentStatus, "payment_status"),
        default=PaymentStatus.INITIATED,
        index=True,
    )
    # Sandbox transactions are ALWAYS labelled as such end-to-end.
    is_sandbox: Mapped[bool] = mapped_column(Boolean, default=True)
    initiated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    initiated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_payload: Mapped[dict | None] = mapped_column(JSON)
    failure_reason: Mapped[str | None] = mapped_column(Text)


class PaymentWebhookEvent(UUIDPrimaryKeyMixin, Base):
    """Idempotent webhook storage: unique provider event_id + signature check."""

    __tablename__ = "payment_webhook_events"

    provider: Mapped[PaymentProviderKind] = mapped_column(
        _enum(PaymentProviderKind, "payment_provider_kind")
    )
    event_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(80))
    signature_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    payload: Mapped[dict | None] = mapped_column(JSON)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_error: Mapped[str | None] = mapped_column(Text)
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payment_transactions.id")
    )


class LedgerEntry(UUIDPrimaryKeyMixin, Base):
    """Double-entry style accounting rows; append-only, never mutated.

    Idempotency key guarantees no double charging / duplicate settlement.
    """

    __tablename__ = "ledger_entries"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_ledger_idempotency_key"),
        Index("ix_ledger_order_type", "order_id", "entry_type"),
    )

    entry_type: Mapped[LedgerEntryType] = mapped_column(
        _enum(LedgerEntryType, "ledger_entry_type")
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id"), index=True)
    shipment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("shipments.id"), index=True
    )
    payment_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payment_transactions.id")
    )
    # Account labels, e.g. "buyer:<uuid>", "platform_revenue", "farmer:<uuid>".
    debit_account: Mapped[str] = mapped_column(String(100))
    credit_account: Mapped[str] = mapped_column(String(100))
    amount_paise: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    memo: Mapped[str | None] = mapped_column(String(255))
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class FarmerSettlement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "farmer_settlements"
    __table_args__ = (
        UniqueConstraint("order_id", "farmer_id", name="uq_farmer_settlements"),
    )

    farmer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    gross_paise: Mapped[int] = mapped_column(Integer)
    deductions_paise: Mapped[int] = mapped_column(Integer, default=0)
    net_paise: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    breakdown: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[SettlementStatus] = mapped_column(
        _enum(SettlementStatus, "settlement_status"),
        default=SettlementStatus.PENDING,
        index=True,
    )
    payout_ref: Mapped[str | None] = mapped_column(String(100))
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DriverSettlement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "driver_settlements"
    __table_args__ = (
        UniqueConstraint("driver_id", "shipment_id", name="uq_driver_settlements"),
    )

    driver_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    shipment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shipments.id"), index=True)
    amount_paise: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    status: Mapped[SettlementStatus] = mapped_column(
        _enum(SettlementStatus, "settlement_status"),
        default=SettlementStatus.PENDING,
        index=True,
    )
    payout_ref: Mapped[str | None] = mapped_column(String(100))
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Refund(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "refunds"

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    payment_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payment_transactions.id")
    )
    amount_paise: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[RefundStatus] = mapped_column(
        _enum(RefundStatus, "refund_status"),
        default=RefundStatus.REQUESTED,
        index=True,
    )
    requested_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_ref: Mapped[str | None] = mapped_column(String(100))
