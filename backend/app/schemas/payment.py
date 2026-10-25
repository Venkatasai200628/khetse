"""Payment schemas: sandbox transaction lifecycle, confirmation result and
the per-order payment + ledger view."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import (
    LedgerEntryType,
    OrderStatus,
    PaymentProviderKind,
    PaymentStatus,
)


class PaymentTransactionPublic(BaseModel):
    """A payment attempt on an order. Sandbox rows are ALWAYS flagged
    `is_sandbox: true` with provider `mock` — visibly labelled end-to-end."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    provider: PaymentProviderKind
    provider_ref: str | None
    amount_paise: int
    currency: str
    status: PaymentStatus
    is_sandbox: bool
    initiated_at: datetime | None
    completed_at: datetime | None


class LedgerEntryPublic(BaseModel):
    """One accounting line (append-only) from the settlement."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entry_type: LedgerEntryType
    order_id: uuid.UUID | None
    payment_transaction_id: uuid.UUID | None
    debit_account: str
    credit_account: str
    amount_paise: int
    currency: str
    memo: str | None
    idempotency_key: str
    created_at: datetime


class InitiatePaymentResponse(PaymentTransactionPublic):
    """Result of POST /payments/orders/{order_id}/initiate.

    `already_initiated` is true when a prior initiation is returned as-is
    (client retry) instead of creating a second transaction.
    """

    already_initiated: bool = False


class ConfirmPaymentResponse(BaseModel):
    """Result of POST /payments/transactions/{transaction_id}/confirm — the
    simulated provider webhook. On a replay (`already_confirmed: true`) the
    settlement is returned as it was applied the first time."""

    transaction: PaymentTransactionPublic
    order_status: OrderStatus
    order_payment_status: PaymentStatus
    ledger_entries: list[LedgerEntryPublic] = []
    already_confirmed: bool = False


class OrderPaymentResponse(BaseModel):
    """GET /payments/orders/{order_id}: payment state + settlement lines."""

    order_id: uuid.UUID
    order_status: OrderStatus
    payment_status: PaymentStatus
    subtotal_paise: int
    delivery_fee_paise: int
    platform_fee_paise: int
    total_paise: int
    currency: str
    transactions: list[PaymentTransactionPublic] = []
    ledger_entries: list[LedgerEntryPublic] = []
