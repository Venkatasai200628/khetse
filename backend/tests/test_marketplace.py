"""Marketplace flow tests: listing → cart → checkout → acceptance.

Covers the business invariants the spec demands: no overselling, idempotent
checkout, ownership enforcement, reservation release on reject/cancel, and
legal-only state transitions.
"""

import uuid

from app.db.session import SessionLocal
from app.models.enums import RoleEnum
from tests.helpers import login_existing, register_user, seed_commodity


def _setup(client):
    """Farmer + buyer + commodity → returns ids and auth headers."""
    commodity_id = seed_commodity()
    farmer = register_user(client, "+919700000001", "Farmer Reddy", "farmer")
    buyer = register_user(client, "+919700000002", "Sita Rao", "buyer")
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
            "quality_grade": "A",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _add_to_cart(client, buyer_headers, listing_id, quantity):
    return client.post(
        "/api/v1/cart/items",
        headers=buyer_headers,
        json={"listing_id": listing_id, "quantity": quantity},
    )


def _checkout(client, buyer_headers, idempotency_key=None):
    return client.post(
        "/api/v1/orders/checkout",
        headers=buyer_headers,
        json={
            "idempotency_key": idempotency_key,
            "fulfilment": "delivery",
            "delivery_name": "Sita Rao",
            "delivery_phone": "+919700000002",
            "delivery_address": "12-34, MG Road",
            "delivery_district": "Kurnool",
        },
    )


def test_full_order_flow_to_payment_pending(client):
    commodity_id, farmer, buyer = _setup(client)
    listing = _create_listing(client, farmer["headers"], commodity_id)

    r = _add_to_cart(client, buyer["headers"], listing["id"], 10)
    assert r.status_code == 200, r.text
    assert r.json()["subtotal_paise"] == 10 * 2000

    r = _checkout(client, buyer["headers"], idempotency_key="order-key-1")
    assert r.status_code == 201, r.text
    order = r.json()
    # 10 kg × ₹20 = ₹200 subtotal (20_000 paise) + ₹30 delivery + 2.5% fee
    assert order["subtotal_paise"] == 20_000
    assert order["delivery_fee_paise"] == 3000
    assert order["platform_fee_paise"] == 500  # 2.5% of 20000
    assert order["total_paise"] == 23_500
    assert order["status"] == "awaiting_farmer_confirmation"
    assert order["items"][0]["quantity"] == 10

    # Inventory reserved: available drops from 100 to 90
    r = client.get(f"/api/v1/listings/{listing['id']}", headers=buyer["headers"])
    assert r.json()["quantity_available"] == 90

    # Farmer accepts → payment_pending
    r = client.post(
        f"/api/v1/orders/{order['id']}/farmer-response",
        headers=farmer["headers"],
        json={"accept": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "payment_pending"

    # Cart is emptied after checkout
    r = client.get("/api/v1/cart", headers=buyer["headers"])
    assert r.json()["items"] == []


def test_checkout_is_idempotent(client):
    commodity_id, farmer, buyer = _setup(client)
    listing = _create_listing(client, farmer["headers"], commodity_id)
    _add_to_cart(client, buyer["headers"], listing["id"], 5)

    r1 = _checkout(client, buyer["headers"], idempotency_key="same-key")
    r2 = _checkout(client, buyer["headers"], idempotency_key="same-key")
    assert r1.json()["id"] == r2.json()["id"]

    # Second attempt without key → cart is empty → validation error
    r3 = _checkout(client, buyer["headers"])
    assert r3.status_code == 422


def test_overselling_prevented(client):
    commodity_id, farmer, buyer = _setup(client)
    listing = _create_listing(client, farmer["headers"], commodity_id, qty=10)

    # Try to cart more than available
    r = _add_to_cart(client, buyer["headers"], listing["id"], 11)
    assert r.status_code == 422

    # Cart exactly available, then another buyer's checkout must fail
    _add_to_cart(client, buyer["headers"], listing["id"], 10)
    r = _checkout(client, buyer["headers"], idempotency_key="k1")
    assert r.status_code == 201

    buyer2 = register_user(client, "+919700000003", "Gita", "buyer")
    r = _add_to_cart(client, buyer2["headers"], listing["id"], 1)
    assert r.status_code == 422  # nothing left unreserved


def test_farmer_reject_releases_inventory(client):
    commodity_id, farmer, buyer = _setup(client)
    listing = _create_listing(client, farmer["headers"], commodity_id, qty=50)
    _add_to_cart(client, buyer["headers"], listing["id"], 20)
    order = _checkout(client, buyer["headers"], idempotency_key="k-rej").json()

    r = client.post(
        f"/api/v1/orders/{order['id']}/farmer-response",
        headers=farmer["headers"],
        json={"accept": False, "reason": "Quality spoiled in rain"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"

    r = client.get(f"/api/v1/listings/{listing['id']}", headers=buyer["headers"])
    assert r.json()["quantity_available"] == 50  # fully released


def test_buyer_cancel_releases_inventory(client):
    commodity_id, farmer, buyer = _setup(client)
    listing = _create_listing(client, farmer["headers"], commodity_id, qty=50)
    _add_to_cart(client, buyer["headers"], listing["id"], 15)
    order = _checkout(client, buyer["headers"], idempotency_key="k-can").json()

    r = client.post(
        f"/api/v1/orders/{order['id']}/cancel",
        headers=buyer["headers"],
        json={"reason": "Changed mind"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"

    r = client.get(f"/api/v1/listings/{listing['id']}", headers=buyer["headers"])
    assert r.json()["quantity_available"] == 50


def test_farmer_cannot_withdraw_listing_with_reservations(client):
    commodity_id, farmer, buyer = _setup(client)
    listing = _create_listing(client, farmer["headers"], commodity_id, qty=30)
    _add_to_cart(client, buyer["headers"], listing["id"], 10)
    _checkout(client, buyer["headers"], idempotency_key="k-w")

    r = client.patch(
        f"/api/v1/listings/{listing['id']}/status",
        headers=farmer["headers"],
        json={"status": "withdrawn"},
    )
    assert r.status_code == 409

    # After buyer cancels, withdrawal succeeds
    orders = client.get("/api/v1/orders/mine", headers=buyer["headers"]).json()
    client.post(
        f"/api/v1/orders/{orders['items'][0]['id']}/cancel",
        headers=buyer["headers"],
        json={"reason": "x"},
    )
    r = client.patch(
        f"/api/v1/listings/{listing['id']}/status",
        headers=farmer["headers"],
        json={"status": "withdrawn"},
    )
    assert r.status_code == 200


def test_wrong_farmer_cannot_respond(client):
    commodity_id, farmer, buyer = _setup(client)
    listing = _create_listing(client, farmer["headers"], commodity_id)
    _add_to_cart(client, buyer["headers"], listing["id"], 5)
    order = _checkout(client, buyer["headers"], idempotency_key="k-x").json()

    other_farmer = register_user(client, "+919700000009", "Other Farmer", "farmer")
    r = client.post(
        f"/api/v1/orders/{order['id']}/farmer-response",
        headers=other_farmer["headers"],
        json={"accept": True},
    )
    assert r.status_code == 409


def test_buyer_cannot_access_other_buyer_order(client):
    commodity_id, farmer, buyer = _setup(client)
    listing = _create_listing(client, farmer["headers"], commodity_id)
    _add_to_cart(client, buyer["headers"], listing["id"], 5)
    order = _checkout(client, buyer["headers"], idempotency_key="k-sec").json()

    intruder = register_user(client, "+919700000010", "Intruder", "buyer")
    r = client.get(f"/api/v1/orders/{order['id']}", headers=intruder["headers"])
    assert r.status_code == 403


def test_farmer_cannot_create_listing_without_role(client):
    buyer = register_user(client, "+919700000011", "Not A Farmer", "buyer")
    commodity_id = seed_commodity("Onion", "ఉల్లి")
    r = client.post(
        "/api/v1/listings",
        headers=buyer["headers"],
        json={
            "commodity_id": commodity_id,
            "quantity_total": 10,
            "unit": "kg",
            "min_price_paise": 1000,
            "listed_price_paise": 1200,
        },
    )
    assert r.status_code == 403


# --------------------------------------------------------------------------
# Idempotency is scoped to the buyer
# --------------------------------------------------------------------------


def test_idempotency_key_of_another_buyer_is_rejected(client):
    commodity_id, farmer, buyer = _setup(client)
    listing = _create_listing(client, farmer["headers"], commodity_id)
    _add_to_cart(client, buyer["headers"], listing["id"], 5)
    r1 = _checkout(client, buyer["headers"], idempotency_key="shared-key")
    assert r1.status_code == 201, r1.text

    buyer2 = register_user(client, "+919700000012", "Gita", "buyer")
    _add_to_cart(client, buyer2["headers"], listing["id"], 3)
    r2 = _checkout(client, buyer2["headers"], idempotency_key="shared-key")
    assert r2.status_code == 409, r2.text
    # Buyer A's order details must never be returned to buyer B.
    assert "12-34, MG Road" not in r2.text
    assert r2.json()["error"]["code"] == "conflict"


# --------------------------------------------------------------------------
# Farmer privacy: exact farm coordinates stay owner-scoped
# --------------------------------------------------------------------------


def _create_listing_with_coords(client, farmer_headers, commodity_id):
    r = client.post(
        "/api/v1/listings",
        headers=farmer_headers,
        json={
            "commodity_id": commodity_id,
            "quantity_total": 50,
            "unit": "kg",
            "min_price_paise": 1500,
            "listed_price_paise": 2000,
            "farm_lat": 17.3606,
            "farm_lng": 78.2854,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_farm_coordinates_not_exposed_to_buyers(client):
    from sqlalchemy import select

    from app.models.profiles import FarmerProfile
    from app.models.user import User

    commodity_id, farmer, buyer = _setup(client)
    # Give the farmer a profile so village/district are populated — that is
    # the location context buyers get INSTEAD of the exact coordinates.
    db = SessionLocal()
    try:
        farmer_user = db.scalar(
            select(User).where(User.phone == "+919700000001")
        )
        db.add(
            FarmerProfile(
                user_id=farmer_user.id,
                village="Kothur",
                district="Ranga Reddy",
                state="Telangana",
            )
        )
        db.commit()
    finally:
        db.close()

    listing = _create_listing_with_coords(client, farmer["headers"], commodity_id)

    # The owner sees their own coordinates back on create and /mine.
    assert listing["farm_lat"] == 17.3606
    mine = client.get("/api/v1/listings/mine", headers=farmer["headers"]).json()
    assert mine[0]["farm_lat"] == 17.3606
    assert mine[0]["farm_lng"] == 78.2854

    # Buyers never see them — browse or detail.
    page = client.get("/api/v1/listings", headers=buyer["headers"]).json()
    item = next(i for i in page["items"] if i["id"] == listing["id"])
    assert "farm_lat" not in item and "farm_lng" not in item
    # Village/district context IS provided instead.
    assert item["farmer_district"] == "Ranga Reddy"
    assert item["farmer_village"] == "Kothur"

    detail = client.get(
        f"/api/v1/listings/{listing['id']}", headers=buyer["headers"]
    ).json()
    assert "farm_lat" not in detail and "farm_lng" not in detail


# --------------------------------------------------------------------------
# Multi-farmer orders: every farmer responds before the order moves
# --------------------------------------------------------------------------


def _multi_farmer_setup(client, key_suffix):
    commodity_id = seed_commodity()
    farmer_a = register_user(client, "+919700000021", "Farmer A", "farmer")
    farmer_b = register_user(client, "+919700000022", "Farmer B", "farmer")
    buyer = register_user(client, "+919700000023", "Multi Buyer", "buyer")
    listing_a = _create_listing(client, farmer_a["headers"], commodity_id, qty=100)
    listing_b = _create_listing(client, farmer_b["headers"], commodity_id, qty=100)
    _add_to_cart(client, buyer["headers"], listing_a["id"], 5)
    _add_to_cart(client, buyer["headers"], listing_b["id"], 4)
    order = _checkout(
        client, buyer["headers"], idempotency_key=f"multi-{key_suffix}"
    ).json()
    return farmer_a, farmer_b, buyer, listing_a, listing_b, order


def _respond(client, headers, order_id, accept, reason=None):
    return client.post(
        f"/api/v1/orders/{order_id}/farmer-response",
        headers=headers,
        json={"accept": accept, "reason": reason},
    )


def test_multi_farmer_order_waits_for_all_farmers(client):
    farmer_a, farmer_b, buyer, listing_a, listing_b, order = _multi_farmer_setup(
        client, "accept"
    )

    # First farmer accepts — the order must NOT move forward on their own.
    r = _respond(client, farmer_a["headers"], order["id"], accept=True)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "awaiting_farmer_confirmation"
    responses = {i["farmer_id"]: i["farmer_response"] for i in body["items"]}
    assert responses[listing_a["farmer_id"]] == "accepted"
    assert responses[listing_b["farmer_id"]] == "pending"

    # Same farmer cannot respond twice.
    r = _respond(client, farmer_a["headers"], order["id"], accept=True)
    assert r.status_code == 409

    # Second farmer accepts — now the order proceeds to payment.
    r = _respond(client, farmer_b["headers"], order["id"], accept=True)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "payment_pending"
    assert r.json()["payment_status"] == "pending"


def test_multi_farmer_reject_releases_only_that_farmer(client):
    farmer_a, farmer_b, buyer, listing_a, listing_b, order = _multi_farmer_setup(
        client, "reject"
    )

    # Farmer A rejects: only A's stock is freed; B's stays reserved.
    r = _respond(
        client, farmer_a["headers"], order["id"], accept=False, reason="spoiled"
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "awaiting_farmer_confirmation"
    assert client.get(
        f"/api/v1/listings/{listing_a['id']}", headers=buyer["headers"]
    ).json()["quantity_available"] == 100
    assert client.get(
        f"/api/v1/listings/{listing_b['id']}", headers=buyer["headers"]
    ).json()["quantity_available"] == 96

    # B accepts: everyone has responded and one rejected — the order dies
    # and B's reservation is released too.
    r = _respond(client, farmer_b["headers"], order["id"], accept=True)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "rejected"
    assert client.get(
        f"/api/v1/listings/{listing_b['id']}", headers=buyer["headers"]
    ).json()["quantity_available"] == 100


# --------------------------------------------------------------------------
# Cart validates the cumulative line, not just the increment
# --------------------------------------------------------------------------


def test_cart_add_checks_cumulative_quantity(client):
    commodity_id, farmer, buyer = _setup(client)
    listing = _create_listing(client, farmer["headers"], commodity_id, qty=10)

    r = _add_to_cart(client, buyer["headers"], listing["id"], 8)
    assert r.status_code == 200, r.text
    # 8 in cart + 5 more = 13 > 10 available — must be rejected now,
    # not at checkout.
    r = _add_to_cart(client, buyer["headers"], listing["id"], 5)
    assert r.status_code == 422, r.text
    cart = client.get("/api/v1/cart", headers=buyer["headers"]).json()
    assert cart["items"][0]["quantity"] == 8


# --------------------------------------------------------------------------
# Delivery fee reflects the real distance to the farthest farm
# --------------------------------------------------------------------------


def test_delivery_fee_uses_farm_distance(client):
    from app.utils.geo import haversine_km

    commodity_id, farmer, buyer = _setup(client)
    listing = _create_listing_with_coords(client, farmer["headers"], commodity_id)
    _add_to_cart(client, buyer["headers"], listing["id"], 5)
    r = client.post(
        "/api/v1/orders/checkout",
        headers=buyer["headers"],
        json={
            "idempotency_key": "k-dist",
            "fulfilment": "delivery",
            "delivery_name": "Sita Rao",
            "delivery_phone": "+919700000002",
            "delivery_address": "12-34, MG Road",
            "delivery_district": "Hyderabad",
            "delivery_lat": 17.3850,
            "delivery_lng": 78.4867,
        },
    )
    assert r.status_code == 201, r.text
    fee = r.json()["delivery_fee_paise"]
    dist = haversine_km(17.3850, 78.4867, 17.3606, 78.2854)
    assert fee == 3000 + int(dist * 500)  # base + per-km
    assert fee > 3000


# --------------------------------------------------------------------------
# Admin completion endpoint consumes the inventory reservations
# --------------------------------------------------------------------------


def test_admin_complete_order_consumes_reservations(client):
    from app.models.commerce import Order
    from app.models.enums import OrderStatus
    from app.services import order_state
    from tests.helpers import create_user_direct

    commodity_id, farmer, buyer = _setup(client)
    listing = _create_listing(client, farmer["headers"], commodity_id, qty=50)
    _add_to_cart(client, buyer["headers"], listing["id"], 10)
    order = _checkout(client, buyer["headers"], idempotency_key="k-comp").json()
    r = _respond(client, farmer["headers"], order["id"], accept=True)
    assert r.json()["status"] == "payment_pending"

    # Drive the order through the legal transitions to DELIVERED
    # (payment confirmation is system-only; the physical steps are admin-
    # driven here since no driver flow exists yet).
    db = SessionLocal()
    try:
        o = db.get(Order, uuid.UUID(order["id"]))
        for target, role in (
            (OrderStatus.CONFIRMED, "system"),
            (OrderStatus.PICKUP_SCHEDULED, "admin"),
            (OrderStatus.PICKED_UP, "admin"),
            (OrderStatus.OUT_FOR_DELIVERY, "admin"),
            (OrderStatus.DELIVERED, "admin"),
        ):
            order_state.apply_transition(
                db, o, target, role_override=role, reason="test drive"
            )
        db.commit()
    finally:
        db.close()

    create_user_direct("+919700000041", "Admin", [RoleEnum.ADMIN])
    admin_auth = login_existing(client, "+919700000041")
    r = client.post(f"/api/v1/orders/{order['id']}/complete", headers=admin_auth["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "completed"
    assert body["completed_at"] is not None

    # The reserved 10 units leave the listing for good.
    listing_after = client.get(
        f"/api/v1/listings/{listing['id']}", headers=buyer["headers"]
    ).json()
    assert listing_after["quantity_total"] == 40
    assert listing_after["quantity_available"] == 40

    # Completion is a one-shot transition.
    r = client.post(f"/api/v1/orders/{order['id']}/complete", headers=admin_auth["headers"])
    assert r.status_code == 409


# --------------------------------------------------------------------------
# FPO operators: involvement via their members' listings
# --------------------------------------------------------------------------


def test_fpo_operator_handles_member_orders(client):
    from sqlalchemy import select

    from app.models.profiles import FarmerProfile, FpoProfile
    from app.models.user import User
    from tests.helpers import create_user_direct

    commodity_id = seed_commodity()

    # Two FPOs; the operators belong to them, the member farmer to one.
    db = SessionLocal()
    try:
        fpo = FpoProfile(name="Kothur FPO", district="Ranga Reddy", state="Telangana")
        other_fpo = FpoProfile(name="Far FPO", district="Adilabad", state="Telangana")
        db.add_all([fpo, other_fpo])
        db.commit()
        fpo_id, other_fpo_id = fpo.id, other_fpo.id
    finally:
        db.close()
    create_user_direct(
        "+919700000031", "FPO Operator", [RoleEnum.FPO_OPERATOR], fpo_id=fpo_id
    )
    create_user_direct(
        "+919700000032",
        "Outsider Operator",
        [RoleEnum.FPO_OPERATOR],
        fpo_id=other_fpo_id,
    )

    member = register_user(client, "+919700000033", "Member Farmer", "farmer")
    db = SessionLocal()
    try:
        member_user = db.scalar(
            select(User).where(User.phone == "+919700000033")
        )
        db.add(
            FarmerProfile(
                user_id=member_user.id,
                village="Kothur",
                district="Ranga Reddy",
                state="Telangana",
                fpo_id=fpo_id,
            )
        )
        db.commit()
    finally:
        db.close()

    operator_auth = login_existing(client, "+919700000031")
    outsider_auth = login_existing(client, "+919700000032")

    buyer = register_user(client, "+919700000034", "FPO Buyer", "buyer")
    listing = _create_listing(client, member["headers"], commodity_id)
    _add_to_cart(client, buyer["headers"], listing["id"], 5)
    order = _checkout(client, buyer["headers"], idempotency_key="k-fpo").json()

    # The operator SEES the member's order...
    r = client.get("/api/v1/orders/farmer", headers=operator_auth["headers"])
    assert r.status_code == 200
    assert any(o["id"] == order["id"] for o in r.json()["items"])
    # ...and can open it...
    r = client.get(f"/api/v1/orders/{order['id']}", headers=operator_auth["headers"])
    assert r.status_code == 200
    # ...while an operator of an unrelated FPO cannot.
    r = client.get(
        f"/api/v1/orders/{order['id']}", headers=outsider_auth["headers"]
    )
    assert r.status_code == 403
    r = _respond(client, outsider_auth["headers"], order["id"], accept=True)
    assert r.status_code == 409

    # The operator accepts on behalf of their member farmer.
    r = _respond(client, operator_auth["headers"], order["id"], accept=True)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "payment_pending"
