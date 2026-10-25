"""Payment endpoints.

Sandbox flow (this ask):
- POST /payments/orders/{order_id}/initiate       — buyer opens a mock sandbox
  transaction for the order total (provider=mock, is_sandbox=true).
- POST /payments/transactions/{transaction_id}/confirm — the simulated
  provider webhook: idempotent, amount-verified, settles the order
  (PAYMENT_PENDING → CONFIRMED) and writes the ledger.
- GET  /payments/orders/{order_id}                — payment status + ledger
  lines for the order, owner or admin only.

Real-provider path (kept from the razorpay stub):
- POST /payments/webhook — HMAC-signed capture; the order only moves after
  the signature verifies with RAZORPAY_WEBHOOK_SECRET.

A payment only becomes 'success' on the confirm/webhook call — never because
a button was clicked — and every sandbox row is flagged is_sandbox.
"""

import hashlib
import hmac
import json
import uuid

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_current_user, require_roles
from app.core.errors import (
    AppError,
    AuthenticationError,
    NotFoundError,
    ValidationAppError,
)
from app.db.session import get_db
from app.models.commerce import Order
from app.models.enums import OrderStatus, PaymentStatus, RoleEnum
from app.models.user import User
from app.schemas.payment import (
    ConfirmPaymentResponse,
    InitiatePaymentResponse,
    LedgerEntryPublic,
    OrderPaymentResponse,
    PaymentTransactionPublic,
)
from app.services import order_service, payment_service

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post(
    "/orders/{order_id}/initiate",
    response_model=InitiatePaymentResponse,
    status_code=201,
    summary="Open a sandbox (mock) payment for an order",
)
def initiate_payment(
    order_id: uuid.UUID,
    response: Response,
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(RoleEnum.BUYER, RoleEnum.BUSINESS)),
):
    """Buyer or business role, must own the order. Creates a PaymentTransaction
    with provider=mock, is_sandbox=true and amount_paise=order.total_paise.
    A retry while a transaction is still open returns it with 200 instead of
    creating a duplicate."""
    txn, created = payment_service.initiate_payment(db, buyer, order_id)
    if not created:
        response.status_code = 200
    return InitiatePaymentResponse(
        **PaymentTransactionPublic.model_validate(txn).model_dump(),
        already_initiated=not created,
    )


@router.post(
    "/transactions/{transaction_id}/confirm",
    response_model=ConfirmPaymentResponse,
    summary="Simulated provider webhook: confirm a sandbox payment",
)
def confirm_payment(
    transaction_id: uuid.UUID,
    db: Session = Depends(get_db),
    caller: User = Depends(get_current_user),
):
    """The sandbox counterpart of the provider's signed webhook. Idempotent
    per transaction, verifies the amount against order.total_paise, sets the
    transaction SUCCESS, moves the order PAYMENT_PENDING → CONFIRMED through
    the state machine (role_override='system') and writes the settlement
    ledger lines exactly once. Only the order's buyer (or an admin) may call
    it; anyone else gets 403."""
    txn, order, entries, already = payment_service.confirm_payment(
        db, caller, transaction_id
    )
    return ConfirmPaymentResponse(
        transaction=PaymentTransactionPublic.model_validate(txn),
        order_status=order.status,
        order_payment_status=order.payment_status,
        ledger_entries=[LedgerEntryPublic.model_validate(e) for e in entries],
        already_confirmed=already,
    )


@router.get(
    "/orders/{order_id}",
    response_model=OrderPaymentResponse,
    summary="Payment status and ledger lines for an order",
)
def order_payment(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Owner or admin only — everyone else gets 403."""
    order, transactions, ledger = payment_service.get_order_payment(
        db, user, order_id
    )
    return OrderPaymentResponse(
        order_id=order.id,
        order_status=order.status,
        payment_status=order.payment_status,
        subtotal_paise=order.subtotal_paise,
        delivery_fee_paise=order.delivery_fee_paise,
        platform_fee_paise=order.platform_fee_paise,
        total_paise=order.total_paise,
        currency=order.currency,
        transactions=[PaymentTransactionPublic.model_validate(t) for t in transactions],
        ledger_entries=[LedgerEntryPublic.model_validate(e) for e in ledger],
    )


# ---------------------------------------------------------------------------
# Real-provider path (razorpay stub) — unchanged behaviour
# ---------------------------------------------------------------------------


def _extract_order_id(payload: dict) -> str | None:
    """Accepts our simplified shape and razorpay's nested event shape
    (`payload.payment.entity.notes.order_id`)."""
    if not isinstance(payload, dict):
        return None
    direct = payload.get("order_id")
    if direct:
        return str(direct)
    entity = payload.get("payload", {})
    if isinstance(entity, dict):
        payment = entity.get("payment", {})
        if isinstance(payment, dict):
            payment_entity = payment.get("entity", {})
            if isinstance(payment_entity, dict):
                notes = payment_entity.get("notes", {})
                if isinstance(notes, dict) and notes.get("order_id"):
                    return str(notes["order_id"])
    return None


@router.post("/webhook", include_in_schema=True)
async def payment_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_razorpay_signature: str | None = Header(default=None),
) -> dict:
    settings = get_settings()
    secret = settings.RAZORPAY_WEBHOOK_SECRET
    if not secret:
        raise AppError(
            "Payment webhook is not configured on this deployment.",
            status_code=503,
        )

    raw = await request.body()
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    if not x_razorpay_signature or not hmac.compare_digest(
        x_razorpay_signature, expected
    ):
        raise AuthenticationError("Invalid webhook signature.")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValidationAppError("Webhook body is not valid JSON.") from exc

    event = payload.get("event") if isinstance(payload, dict) else None
    if event != "payment.captured":
        # Acknowledge other events without acting on them.
        return {"status": "ignored", "event": event}

    order_ref = _extract_order_id(payload)
    if not order_ref:
        raise ValidationAppError("Webhook payload carries no order reference.")
    try:
        order_id = uuid.UUID(order_ref)
    except ValueError:
        raise ValidationAppError("Order reference is not a valid UUID.") from None

    order = db.get(Order, order_id)
    if order is None:
        raise NotFoundError("Order not found for webhook reference.")

    # Replayed deliveries are acknowledged, not re-applied.
    if (
        order.status == OrderStatus.CONFIRMED
        and order.payment_status == PaymentStatus.SUCCESS
    ):
        return {"status": "already_captured", "order_id": str(order.id)}

    order_service.capture_payment(db, order)
    return {"status": "captured", "order_id": str(order.id)}
