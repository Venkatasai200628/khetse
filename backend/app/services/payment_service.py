"""Sandbox payment flow: initiate, confirm (simulated provider webhook) and
the per-order payment/ledger view.

Invariants enforced here:
- Money is integer paise only; every amount is copied from the order row,
  never recomputed from floats.
- Sandbox transactions are ALWAYS provider=mock and is_sandbox=True —
  visibly labelled end-to-end, never dressed up as a real payment.
- Only the order's own buyer (or an admin) may initiate, confirm or view;
  roles are gated at the route, ownership here.
- A transaction is created only while the order is PAYMENT_PENDING, so a
  paid, cancelled or rejected order can never be paid again.
- Confirmation behaves like the provider's webhook: idempotent per
  transaction (a replay is acknowledged without re-applying), verifies the
  amount still matches order.total_paise, moves the order through the state
  machine (PAYMENT_PENDING → CONFIRMED as role 'system') and settles exactly
  once.
- Settlement ledger rows carry deterministic idempotency keys derived from
  the transaction id; the UNIQUE constraint on ledger_entries.idempotency_key
  makes a double write physically impossible, even under a concurrent retry.
"""

from collections import defaultdict
from datetime import datetime, timezone
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AuthorizationError, ConflictError, NotFoundError
from app.models.commerce import Order
from app.models.enums import (
    LedgerEntryType,
    OrderStatus,
    PaymentProviderKind,
    PaymentStatus,
    RoleEnum,
)
from app.models.finance import LedgerEntry, PaymentTransaction
from app.models.user import User
from app.services import order_state

ESCROW_ACCOUNT = "platform_escrow"
PLATFORM_REVENUE_ACCOUNT = "platform_revenue"
DELIVERY_REVENUE_ACCOUNT = "delivery_revenue"


def _get_order(db: Session, order_id: uuid.UUID) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise NotFoundError("Order not found.")
    return order


def _ensure_owner_or_admin(order: Order, user: User, action: str) -> None:
    if order.buyer_id != user.id and not user.has_role(RoleEnum.ADMIN):
        raise AuthorizationError(
            f"You can only {action} payments for your own orders."
        )


def initiate_payment(
    db: Session, buyer: User, order_id: uuid.UUID
) -> tuple[PaymentTransaction, bool]:
    """Open a mock sandbox transaction for the order's full total.

    Returns (transaction, created). A client retry while the previous
    transaction is still INITIATED returns the existing row (created=False)
    instead of stacking duplicate transactions. A settled order is rejected
    by the status gate below — already-paid shows up as a 409, and the
    GET /payments/orders/{id} view is the source of truth for the UI.
    """
    order = _get_order(db, order_id)
    _ensure_owner_or_admin(order, buyer, "initiate")

    if order.status != OrderStatus.PAYMENT_PENDING:
        raise ConflictError(
            "This order is not awaiting payment.",
            details={
                "current_status": order.status.value,
                "payment_status": order.payment_status.value,
            },
        )

    open_txn = db.scalar(
        select(PaymentTransaction)
        .where(
            PaymentTransaction.order_id == order.id,
            PaymentTransaction.status == PaymentStatus.INITIATED,
        )
        .order_by(PaymentTransaction.created_at.desc())
        .limit(1)
    )
    if open_txn is not None:
        return open_txn, False

    txn = PaymentTransaction(
        order_id=order.id,
        provider=PaymentProviderKind.MOCK,
        provider_ref=f"mock_{uuid.uuid4().hex}",
        amount_paise=order.total_paise,
        currency=order.currency,
        status=PaymentStatus.INITIATED,
        is_sandbox=True,  # sandbox is the only path here — always labelled
        initiated_by=buyer.id,
        initiated_at=datetime.now(timezone.utc),
        provider_payload={
            "sandbox": True,
            "note": "KhetSe mock provider — no real money moves.",
        },
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn, True


def confirm_payment(
    db: Session, caller: User, transaction_id: uuid.UUID
) -> tuple[PaymentTransaction, Order, list[LedgerEntry], bool]:
    """Simulated provider webhook for a sandbox transaction.

    Idempotent per transaction: a second call on a SUCCESS transaction
    returns the original settlement (already_confirmed=True) and writes
    nothing further. Otherwise the amount is verified against
    order.total_paise, the order moves PAYMENT_PENDING → CONFIRMED through
    the state machine (role 'system'), the payment is marked SUCCESS and the
    ledger settlement is written.

    Returns (transaction, order, ledger_entries, already_confirmed).
    """
    txn = db.get(PaymentTransaction, transaction_id)
    if txn is None:
        raise NotFoundError("Payment transaction not found.")
    order = _get_order(db, txn.order_id)
    _ensure_owner_or_admin(order, caller, "confirm")

    if txn.status == PaymentStatus.SUCCESS:
        # Replayed webhook delivery: acknowledge, never re-apply.
        return txn, order, _ledger_for_transaction(db, txn.id), True
    if txn.status != PaymentStatus.INITIATED:
        raise ConflictError(
            "This transaction can no longer be confirmed.",
            details={"status": txn.status.value},
        )

    # Amount integrity: the (simulated) provider callback must match what
    # the order charges. A mismatch means tampering or a stale total.
    if txn.amount_paise != order.total_paise:
        raise ConflictError(
            "Transaction amount does not match the order total.",
            details={
                "transaction_amount_paise": txn.amount_paise,
                "order_total_paise": order.total_paise,
            },
        )
    if txn.provider != PaymentProviderKind.MOCK or not txn.is_sandbox:
        raise ConflictError(
            "Only sandbox (mock) transactions are confirmed on this endpoint."
        )

    entries = build_settlement_entries(order, txn)
    db.add_all(entries)
    order_state.apply_transition(
        db,
        order,
        OrderStatus.CONFIRMED,
        role_override="system",
        reason="Sandbox payment confirmed (mock provider)",
    )
    order.payment_status = PaymentStatus.SUCCESS
    txn.status = PaymentStatus.SUCCESS
    txn.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(txn)
    db.refresh(order)
    return txn, order, entries, False


def build_settlement_entries(
    order: Order, txn: PaymentTransaction
) -> list[LedgerEntry]:
    """The four settlement lines for one confirmed payment.

    money_in (buyer → escrow) is balanced by farmer proceeds + platform fee
    + delivery fee out of escrow; the sums equal order.total_paise exactly.
    Farmer proceeds are split per farmer from the order lines so multi-farmer
    orders owe each farmer their own gross.

    Idempotency keys are deterministic (`<txn_id>:<type>[:farmer]`) so the
    UNIQUE constraint on ledger_entries.idempotency_key rejects any repeat.
    """
    key_base = str(txn.id)

    def entry(
        entry_type: LedgerEntryType,
        debit: str,
        credit: str,
        amount: int,
        memo: str,
        idempotency_key: str,
    ) -> LedgerEntry:
        return LedgerEntry(
            entry_type=entry_type,
            order_id=order.id,
            payment_transaction_id=txn.id,
            debit_account=debit,
            credit_account=credit,
            amount_paise=amount,
            currency=order.currency,
            memo=memo,
            idempotency_key=idempotency_key,
        )

    entries = [
        entry(
            LedgerEntryType.PAYMENT_IN,
            debit=f"buyer:{order.buyer_id}",
            credit=ESCROW_ACCOUNT,
            amount=order.total_paise,
            memo=f"Sandbox payment received for order {order.id}",
            idempotency_key=f"{key_base}:payment_in",
        )
    ]

    proceeds: dict[uuid.UUID, int] = defaultdict(int)
    for item in order.items:
        proceeds[item.farmer_id] += item.line_total_paise
    for farmer_id in sorted(proceeds):
        entries.append(
            entry(
                LedgerEntryType.FARMER_PROCEEDS,
                debit=ESCROW_ACCOUNT,
                credit=f"farmer:{farmer_id}",
                amount=proceeds[farmer_id],
                memo=f"Farmer proceeds for order {order.id}",
                idempotency_key=f"{key_base}:farmer_proceeds:{farmer_id}",
            )
        )

    entries.append(
        entry(
            LedgerEntryType.PLATFORM_FEE,
            debit=ESCROW_ACCOUNT,
            credit=PLATFORM_REVENUE_ACCOUNT,
            amount=order.platform_fee_paise,
            memo=f"Platform fee for order {order.id}",
            idempotency_key=f"{key_base}:platform_fee",
        )
    )
    entries.append(
        entry(
            LedgerEntryType.DELIVERY_FEE_IN,
            debit=ESCROW_ACCOUNT,
            credit=DELIVERY_REVENUE_ACCOUNT,
            amount=order.delivery_fee_paise,
            memo=f"Delivery fee for order {order.id}",
            idempotency_key=f"{key_base}:delivery_fee_in",
        )
    )
    return entries


def _ledger_for_transaction(db: Session, txn_id: uuid.UUID) -> list[LedgerEntry]:
    return list(
        db.scalars(
            select(LedgerEntry)
            .where(LedgerEntry.payment_transaction_id == txn_id)
            .order_by(LedgerEntry.created_at, LedgerEntry.id)
        )
    )


def get_order_payment(
    db: Session, user: User, order_id: uuid.UUID
) -> tuple[Order, list[PaymentTransaction], list[LedgerEntry]]:
    """Payment status + ledger lines for an order — owner or admin only."""
    order = _get_order(db, order_id)
    _ensure_owner_or_admin(order, user, "view")
    transactions = list(
        db.scalars(
            select(PaymentTransaction)
            .where(PaymentTransaction.order_id == order.id)
            .order_by(PaymentTransaction.created_at, PaymentTransaction.id)
        )
    )
    ledger = list(
        db.scalars(
            select(LedgerEntry)
            .where(LedgerEntry.order_id == order.id)
            .order_by(LedgerEntry.created_at, LedgerEntry.id)
        )
    )
    return order, transactions, ledger
