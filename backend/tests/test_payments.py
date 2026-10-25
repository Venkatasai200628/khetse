"""Payment tests for all three capture paths.

1. Sandbox transaction flow (this ask):
   - POST /payments/orders/{id}/initiate — owning buyer/business only,
     provider=mock, is_sandbox=true, amount_paise=order.total_paise.
   - POST /payments/transactions/{id}/confirm — the simulated provider
     webhook: idempotent (double confirm → single ledger write, order stays
     CONFIRMED), amount-mismatch rejected, ledger amounts exact in paise.
   - GET /payments/orders/{id} — owner or admin only.
2. Demo-mode one-tap capture: POST /orders/{id}/pay.
3. Signed webhook (razorpay-path stub): POST /payments/webhook.
"""

import hashlib
import hmac
import json
import uuid

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.commerce import Order
from app.models.enums import LedgerEntryType, RoleEnum
from app.models.finance import LedgerEntry, PaymentTransaction
from tests.helpers import (
    create_user_direct,
    login_existing,
    register_user,
    seed_commodity,
)


def _setup(client):
    commodity_id = seed_commodity()
    farmer = register_user(client, "+919700200001", "Pay Farmer", "farmer")
    buyer = register_user(client, "+919700200002", "Pay Buyer", "buyer")
    return commodity_id, farmer, buyer


def _create_listing(client, farmer_headers, commodity_id, qty=100.0, price=2000):
    r = client.post(
        "/api/v1/listings",
        headers=farmer_headers,
        json={
            "commodity_id": commodity_id,
            "quantity_total": qty,
            "unit": "kg",
            "min_price_paise": 1500,
            "listed_price_paise": price,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _add_to_cart(client, buyer_headers, listing_id, quantity=5):
    r = client.post(
        "/api/v1/cart/items",
        headers=buyer_headers,
        json={"listing_id": listing_id, "quantity": quantity},
    )
    assert r.status_code == 200, r.text


def _checkout(client, buyer_headers, listing_id, key, quantity=5):
    _add_to_cart(client, buyer_headers, listing_id, quantity)
    r = client.post(
        "/api/v1/orders/checkout",
        headers=buyer_headers,
        json={
            "idempotency_key": key,
            "fulfilment": "delivery",
            "delivery_name": "Pay Buyer",
            "delivery_phone": "+919700200002",
            "delivery_address": "1 Pay Street",
            "delivery_district": "Kurnool",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _accept(client, farmer_headers, order_id):
    r = client.post(
        f"/api/v1/orders/{order_id}/farmer-response",
        headers=farmer_headers,
        json={"accept": True},
    )
    assert r.status_code == 200, r.text
    return r.json()


def _order_pending_payment(client, key="sandbox"):
    """Listing + accepted order sitting at PAYMENT_PENDING."""
    commodity_id, farmer, buyer = _setup(client)
    listing = _create_listing(client, farmer["headers"], commodity_id)
    order = _checkout(client, buyer["headers"], listing["id"], key)
    assert _accept(client, farmer["headers"], order["id"])["status"] == "payment_pending"
    return farmer, buyer, listing, order


def _initiate(client, buyer_headers, order_id):
    return client.post(
        f"/api/v1/payments/orders/{order_id}/initiate", headers=buyer_headers
    )


def _confirm(client, headers, transaction_id):
    return client.post(
        f"/api/v1/payments/transactions/{transaction_id}/confirm", headers=headers
    )


# ---------------------------------------------------------------------------
# Sandbox flow: initiate
# ---------------------------------------------------------------------------


def test_initiate_creates_sandbox_transaction(client):
    farmer, buyer, listing, order = _order_pending_payment(client, "sb-init")

    r = _initiate(client, buyer["headers"], order["id"])
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["already_initiated"] is False
    assert body["provider"] == "mock"
    assert body["is_sandbox"] is True
    assert body["status"] == "initiated"
    assert body["amount_paise"] == order["total_paise"]  # exact paise copy
    assert body["order_id"] == order["id"]

    # A second initiation while the first is open is a safe retry — same
    # transaction, not a duplicate.
    r = _initiate(client, buyer["headers"], order["id"])
    assert r.status_code == 200, r.text
    assert r.json()["id"] == body["id"]
    assert r.json()["already_initiated"] is True


def test_initiate_requires_the_owning_buyer(client):
    farmer, buyer, listing, order = _order_pending_payment(client, "sb-owner")

    intruder = register_user(client, "+919700200003", "Pay Intruder", "buyer")
    r = _initiate(client, intruder["headers"], order["id"])
    assert r.status_code == 403, r.text
    assert r.json()["error"]["code"] == "forbidden"

    # The farmer is neither the buyer nor a payer-role owner.
    r = _initiate(client, farmer["headers"], order["id"])
    assert r.status_code == 403, r.text


def test_initiate_rejects_orders_not_awaiting_payment(client):
    commodity_id, farmer, buyer = _setup(client)
    listing = _create_listing(client, farmer["headers"], commodity_id)
    order = _checkout(client, buyer["headers"], listing["id"], "sb-state")

    # Still awaiting farmer confirmation — nothing to pay for yet.
    r = _initiate(client, buyer["headers"], order["id"])
    assert r.status_code == 409, r.text

    # Once paid, a re-initiation must also be refused.
    _accept(client, farmer["headers"], order["id"])
    r = _initiate(client, buyer["headers"], order["id"])
    assert r.status_code == 201, r.text
    _confirm(client, buyer["headers"], r.json()["id"])
    r = _initiate(client, buyer["headers"], order["id"])
    assert r.status_code == 409, r.text


# ---------------------------------------------------------------------------
# Sandbox flow: confirm (simulated provider webhook)
# ---------------------------------------------------------------------------


def test_confirm_moves_order_to_confirmed_and_writes_ledger(client):
    farmer, buyer, listing, order = _order_pending_payment(client, "sb-confirm")

    r = _initiate(client, buyer["headers"], order["id"])
    txn_id = r.json()["id"]
    r = _confirm(client, buyer["headers"], txn_id)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["already_confirmed"] is False
    assert body["transaction"]["status"] == "success"
    assert body["transaction"]["is_sandbox"] is True
    assert body["order_status"] == "confirmed"
    assert body["order_payment_status"] == "success"

    entry_types = {e["entry_type"] for e in body["ledger_entries"]}
    assert entry_types == {
        "payment_in",
        "farmer_proceeds",
        "platform_fee",
        "delivery_fee_in",
    }

    # The buyer's own order view reflects the settlement.
    r = client.get(f"/api/v1/orders/{order['id']}", headers=buyer["headers"])
    assert r.json()["status"] == "confirmed"
    assert r.json()["payment_status"] == "success"

    # The reservation is still held on a confirmed (not yet delivered) order.
    r = client.get(f"/api/v1/listings/{listing['id']}", headers=buyer["headers"])
    assert r.json()["quantity_available"] == 95


def test_confirm_is_idempotent_single_ledger_write(client):
    farmer, buyer, listing, order = _order_pending_payment(client, "sb-idem")

    txn_id = _initiate(client, buyer["headers"], order["id"]).json()["id"]
    assert _confirm(client, buyer["headers"], txn_id).status_code == 200

    # Double confirm: acknowledged, not re-applied.
    r = _confirm(client, buyer["headers"], txn_id)
    assert r.status_code == 200, r.text
    assert r.json()["already_confirmed"] is True
    assert r.json()["order_status"] == "confirmed"

    db = SessionLocal()
    try:
        oid = uuid.UUID(order["id"])
        db_rows = (
            db.query(LedgerEntry)
            .filter(LedgerEntry.payment_transaction_id == uuid.UUID(txn_id))
            .all()
        )
        # Exactly one settlement: 4 lines for a single-farmer order, all with
        # unique idempotency keys.
        assert len(db_rows) == 4
        assert len({e.idempotency_key for e in db_rows}) == 4
        assert sum(1 for e in db_rows if e.entry_type == LedgerEntryType.PAYMENT_IN) == 1

        o = db.get(Order, oid)
        assert o.status.value == "confirmed"
        assert o.payment_status.value == "success"
        txn = db.get(PaymentTransaction, uuid.UUID(txn_id))
        assert txn.status.value == "success"
    finally:
        db.close()


def test_confirm_rejects_amount_mismatch(client):
    farmer, buyer, listing, order = _order_pending_payment(client, "sb-amount")

    txn_id = _initiate(client, buyer["headers"], order["id"]).json()["id"]

    # Simulate a tampered / stale provider amount before the webhook lands.
    db = SessionLocal()
    try:
        txn = db.get(PaymentTransaction, uuid.UUID(txn_id))
        txn.amount_paise = order["total_paise"] + 1
        db.commit()
    finally:
        db.close()

    r = _confirm(client, buyer["headers"], txn_id)
    assert r.status_code == 409, r.text
    assert "amount" in r.json()["error"]["message"].lower()

    # Nothing moved: transaction still open, order still awaiting payment.
    db = SessionLocal()
    try:
        txn = db.get(PaymentTransaction, uuid.UUID(txn_id))
        assert txn.status.value == "initiated"
        o = db.get(Order, uuid.UUID(order["id"]))
        assert o.status.value == "payment_pending"
        assert (
            db.query(LedgerEntry).filter(LedgerEntry.order_id == o.id).count() == 0
        )
    finally:
        db.close()


def test_confirm_forbidden_for_other_users(client):
    farmer, buyer, listing, order = _order_pending_payment(client, "sb-403")

    txn_id = _initiate(client, buyer["headers"], order["id"]).json()["id"]

    intruder = register_user(client, "+919700200003", "Pay Intruder", "buyer")
    r = _confirm(client, intruder["headers"], txn_id)
    assert r.status_code == 403, r.text
    assert r.json()["error"]["code"] == "forbidden"

    # Confirming must be the buyer's (or an admin's) act — not the farmer's.
    r = _confirm(client, farmer["headers"], txn_id)
    assert r.status_code == 403, r.text

    # The untouched transaction still confirms cleanly for the real buyer.
    r = _confirm(client, buyer["headers"], txn_id)
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------------------
# Sandbox flow: ledger amounts
# ---------------------------------------------------------------------------


def test_ledger_amounts_are_exact_in_paise(client):
    farmer, buyer, listing, order = _order_pending_payment(client, "sb-ledger")

    txn_id = _initiate(client, buyer["headers"], order["id"]).json()["id"]
    assert _confirm(client, buyer["headers"], txn_id).status_code == 200

    r = client.get(f"/api/v1/payments/orders/{order['id']}", headers=buyer["headers"])
    assert r.status_code == 200, r.text
    view = r.json()
    assert view["payment_status"] == "success"

    by_type = {}
    for e in view["ledger_entries"]:
        by_type.setdefault(e["entry_type"], []).append(e)

    payment_in = by_type["payment_in"][0]
    proceeds = by_type["farmer_proceeds"][0]
    platform_fee = by_type["platform_fee"][0]
    delivery_fee = by_type["delivery_fee_in"][0]

    # Exact paise, copied from the order row.
    assert payment_in["amount_paise"] == order["total_paise"]
    assert proceeds["amount_paise"] == order["subtotal_paise"]
    assert platform_fee["amount_paise"] == order["platform_fee_paise"]
    assert delivery_fee["amount_paise"] == order["delivery_fee_paise"]

    # Double-entry balance: escrow out == money in.
    assert (
        proceeds["amount_paise"]
        + platform_fee["amount_paise"]
        + delivery_fee["amount_paise"]
        == payment_in["amount_paise"]
    )

    # Account labels trace every rupee to its counterpart.
    assert payment_in["debit_account"] == f"buyer:{order['buyer_id']}"
    assert payment_in["credit_account"] == "platform_escrow"
    assert proceeds["debit_account"] == "platform_escrow"
    assert proceeds["credit_account"] == f"farmer:{order['items'][0]['farmer_id']}"
    assert platform_fee["credit_account"] == "platform_revenue"
    assert delivery_fee["credit_account"] == "delivery_revenue"


def test_ledger_splits_farmer_proceeds_per_farmer(client):
    commodity_id, farmer, buyer = _setup(client)
    farmer2 = register_user(client, "+919700200004", "Pay Farmer 2", "farmer")
    l1 = _create_listing(client, farmer["headers"], commodity_id, qty=100, price=2000)
    l2 = _create_listing(client, farmer2["headers"], commodity_id, qty=100, price=2500)
    _add_to_cart(client, buyer["headers"], l1["id"], 5)
    _add_to_cart(client, buyer["headers"], l2["id"], 3)
    r = client.post(
        "/api/v1/orders/checkout",
        headers=buyer["headers"],
        json={
            "idempotency_key": "sb-multi",
            "fulfilment": "delivery",
            "delivery_name": "Pay Buyer",
            "delivery_phone": "+919700200002",
            "delivery_address": "1 Pay Street",
            "delivery_district": "Kurnool",
        },
    )
    assert r.status_code == 201, r.text
    order = r.json()
    # Multi-farmer orders only move forward once EVERY farmer has answered.
    assert (
        _accept(client, farmer["headers"], order["id"])["status"]
        == "awaiting_farmer_confirmation"
    )
    assert _accept(client, farmer2["headers"], order["id"])["status"] == "payment_pending"

    txn_id = _initiate(client, buyer["headers"], order["id"]).json()["id"]
    body = _confirm(client, buyer["headers"], txn_id).json()
    assert body["order_status"] == "confirmed"

    proceeds = [
        e for e in body["ledger_entries"] if e["entry_type"] == "farmer_proceeds"
    ]
    amounts = sorted(e["amount_paise"] for e in proceeds)
    assert amounts == sorted([5 * 2000, 3 * 2500])  # 10000 and 7500, exact paise
    assert sum(amounts) == order["subtotal_paise"]

    keys = [e["idempotency_key"] for e in body["ledger_entries"]]
    assert len(keys) == len(set(keys))  # all unique


# ---------------------------------------------------------------------------
# Sandbox flow: GET /payments/orders/{order_id}
# ---------------------------------------------------------------------------


def test_payment_view_is_owner_or_admin_only(client):
    farmer, buyer, listing, order = _order_pending_payment(client, "sb-view")
    txn_id = _initiate(client, buyer["headers"], order["id"]).json()["id"]
    _confirm(client, buyer["headers"], txn_id)

    url = f"/api/v1/payments/orders/{order['id']}"

    # Owner sees the full payment view.
    r = client.get(url, headers=buyer["headers"])
    assert r.status_code == 200, r.text
    view = r.json()
    assert view["order_id"] == order["id"]
    assert view["order_status"] == "confirmed"
    assert view["payment_status"] == "success"
    assert view["subtotal_paise"] == order["subtotal_paise"]
    assert view["total_paise"] == order["total_paise"]
    assert len(view["transactions"]) == 1
    assert view["transactions"][0]["is_sandbox"] is True
    assert view["ledger_entries"]

    # Admin may inspect any order's payments.
    create_user_direct("+919700200009", "Pay Admin", [RoleEnum.ADMIN])
    admin_login = login_existing(client, "+919700200009")
    r = client.get(url, headers=admin_login["headers"])
    assert r.status_code == 200, r.text
    assert r.json()["payment_status"] == "success"

    # Everyone else — 403.
    intruder = register_user(client, "+919700200003", "Pay Intruder", "buyer")
    r = client.get(url, headers=intruder["headers"])
    assert r.status_code == 403, r.text
    r = client.get(url, headers=farmer["headers"])
    assert r.status_code == 403, r.text


# ---------------------------------------------------------------------------
# Demo-mode capture endpoint
# ---------------------------------------------------------------------------


def test_pay_moves_order_to_confirmed(client):
    commodity_id, farmer, buyer = _setup(client)
    listing = _create_listing(client, farmer["headers"], commodity_id)
    order = _checkout(client, buyer["headers"], listing["id"], "pay-ok")
    assert _accept(client, farmer["headers"], order["id"])["status"] == "payment_pending"

    r = client.post(f"/api/v1/orders/{order['id']}/pay", headers=buyer["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "confirmed"
    assert body["payment_status"] == "success"

    # The reservation is still held on a confirmed (not yet delivered) order.
    r = client.get(f"/api/v1/listings/{listing['id']}", headers=buyer["headers"])
    assert r.json()["quantity_available"] == 95


def test_pay_rejects_a_non_pending_order(client):
    commodity_id, farmer, buyer = _setup(client)
    listing = _create_listing(client, farmer["headers"], commodity_id)
    order = _checkout(client, buyer["headers"], listing["id"], "pay-state")

    # Still awaiting farmer confirmation — nothing to capture yet.
    r = client.post(f"/api/v1/orders/{order['id']}/pay", headers=buyer["headers"])
    assert r.status_code == 409, r.text


def test_pay_is_buyer_only(client):
    commodity_id, farmer, buyer = _setup(client)
    listing = _create_listing(client, farmer["headers"], commodity_id)
    order = _checkout(client, buyer["headers"], listing["id"], "pay-owner")
    _accept(client, farmer["headers"], order["id"])

    intruder = register_user(client, "+919700200003", "Pay Intruder", "buyer")
    r = client.post(f"/api/v1/orders/{order['id']}/pay", headers=intruder["headers"])
    assert r.status_code == 409, r.text
    assert "own" in r.json()["error"]["message"]


def test_pay_disabled_outside_demo_mode(client, monkeypatch):
    commodity_id, farmer, buyer = _setup(client)
    listing = _create_listing(client, farmer["headers"], commodity_id)
    order = _checkout(client, buyer["headers"], listing["id"], "pay-gate")
    _accept(client, farmer["headers"], order["id"])

    # get_settings() is lru_cached — the app and the endpoint share this
    # instance, so flipping DEMO_MODE on it flips settings.demo_mode.
    # (Flipped after setup: without demo mode the OTP flow can't register.)
    monkeypatch.setattr(get_settings(), "DEMO_MODE", False)

    r = client.post(f"/api/v1/orders/{order['id']}/pay", headers=buyer["headers"])
    assert r.status_code == 403, r.text
    assert r.json()["error"]["code"] == "forbidden"

    # Untouched: still awaiting payment under the original flag.
    monkeypatch.setattr(get_settings(), "DEMO_MODE", True)
    r = client.get(f"/api/v1/orders/{order['id']}", headers=buyer["headers"])
    assert r.json()["status"] == "payment_pending"


# ---------------------------------------------------------------------------
# Signed webhook (razorpay-path stub)
# ---------------------------------------------------------------------------

WEBHOOK_SECRET = "whsec_test_secret"


def _signed_body(payload: dict, secret: str = WEBHOOK_SECRET) -> tuple[bytes, dict]:
    raw = json.dumps(payload).encode()
    sig = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return raw, {"X-Razorpay-Signature": sig, "Content-Type": "application/json"}


def test_webhook_requires_configuration(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "RAZORPAY_WEBHOOK_SECRET", "")
    r = client.post("/api/v1/payments/webhook", content=b"{}", headers={})
    assert r.status_code == 503, r.text


def test_webhook_captures_payment_and_is_idempotent(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
    commodity_id, farmer, buyer = _setup(client)
    listing = _create_listing(client, farmer["headers"], commodity_id)
    order = _checkout(client, buyer["headers"], listing["id"], "wh-ok")
    _accept(client, farmer["headers"], order["id"])

    raw, headers = _signed_body({"event": "payment.captured", "order_id": order["id"]})
    r = client.post("/api/v1/payments/webhook", content=raw, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "captured"

    db = SessionLocal()
    try:
        o = db.get(Order, uuid.UUID(order["id"]))
        assert o.status.value == "confirmed"
        assert o.payment_status.value == "success"
    finally:
        db.close()

    # Razorpay retries deliveries — a replay must not re-apply or 409.
    r = client.post("/api/v1/payments/webhook", content=raw, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "already_captured"


def test_webhook_accepts_razorpay_notes_shape(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
    commodity_id, farmer, buyer = _setup(client)
    listing = _create_listing(client, farmer["headers"], commodity_id)
    order = _checkout(client, buyer["headers"], listing["id"], "wh-notes")
    _accept(client, farmer["headers"], order["id"])

    payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {"notes": {"order_id": order["id"]}},
            }
        },
    }
    raw, headers = _signed_body(payload)
    r = client.post("/api/v1/payments/webhook", content=raw, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "captured"


def test_webhook_rejects_bad_signature(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
    raw, headers = _signed_body(
        {"event": "payment.captured", "order_id": "00000000-0000-0000-0000-000000000000"},
        secret="attacker-secret",
    )
    r = client.post("/api/v1/payments/webhook", content=raw, headers=headers)
    assert r.status_code == 401, r.text


def test_webhook_ignores_other_events(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
    raw, headers = _signed_body({"event": "refund.processed", "order_id": "x"})
    r = client.post("/api/v1/payments/webhook", content=raw, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ignored"


def test_webhook_unknown_order_is_404(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
    raw, headers = _signed_body(
        {"event": "payment.captured", "order_id": "00000000-0000-0000-0000-000000000000"}
    )
    r = client.post("/api/v1/payments/webhook", content=raw, headers=headers)
    assert r.status_code == 404, r.text
