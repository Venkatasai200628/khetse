"""Review tests: COMPLETED-order-only rule, buyer-only, one per order,
public farmer listing."""

import uuid

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.enums import OrderStatus
from app.models.commerce import Order
from app.services import order_state
from tests.helpers import register_user, seed_commodity

FARMER_PHONE = "+919740000010"
BUYER_PHONE = "+919740000011"
OTHER_PHONE = "+919740000012"


def _farmer_user_id() -> str:
    from app.models.user import User

    db = SessionLocal()
    try:
        return str(db.scalar(select(User).where(User.phone == FARMER_PHONE)).id)
    finally:
        db.close()


def _create_listing(client, farmer_headers, commodity_id):
    r = client.post(
        "/api/v1/listings",
        headers=farmer_headers,
        json={
            "commodity_id": commodity_id,
            "quantity_total": 100.0,
            "unit": "kg",
            "min_price_paise": 1500,
            "listed_price_paise": 2000,
            "quality_grade": "A",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _order_to_payment_pending(client):
    """Farmer + buyer + listing → checkout → accepted → payment_pending."""
    commodity_id = seed_commodity()
    farmer = register_user(client, FARMER_PHONE, "Farmer F", "farmer")
    buyer = register_user(client, BUYER_PHONE, "Buyer B", "buyer")
    listing = _create_listing(client, farmer["headers"], commodity_id)

    r = client.post(
        "/api/v1/cart/items",
        headers=buyer["headers"],
        json={"listing_id": listing["id"], "quantity": 5},
    )
    assert r.status_code == 200, r.text
    r = client.post(
        "/api/v1/orders/checkout",
        headers=buyer["headers"],
        json={
            "idempotency_key": f"review-{uuid.uuid4()}",
            "fulfilment": "delivery",
            "delivery_name": "Buyer B",
            "delivery_phone": BUYER_PHONE,
            "delivery_address": "12-34, MG Road",
            "delivery_district": "Kurnool",
        },
    )
    assert r.status_code == 201, r.text
    order = r.json()

    r = client.post(
        f"/api/v1/orders/{order['id']}/farmer-response",
        headers=farmer["headers"],
        json={"accept": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "payment_pending"
    return farmer, buyer, order["id"]


def _drive(db_order_id: str, to: OrderStatus) -> None:
    """Advance the order with legal system transitions up to `to`."""
    chain = [
        OrderStatus.CONFIRMED,
        OrderStatus.PICKUP_SCHEDULED,
        OrderStatus.PICKED_UP,
        OrderStatus.OUT_FOR_DELIVERY,
        OrderStatus.DELIVERED,
    ]
    db = SessionLocal()
    try:
        order = db.get(Order, uuid.UUID(db_order_id))
        for status in chain:
            role = "driver" if status in (
                OrderStatus.PICKED_UP,
                OrderStatus.OUT_FOR_DELIVERY,
                OrderStatus.DELIVERED,
            ) else "system"
            order_state.apply_transition(
                db, order, status, role_override=role, reason="test drive"
            )
            if order.status == to:
                db.commit()
                return
        db.commit()
    finally:
        db.close()


def _completed_order(client):
    farmer, buyer, order_id = _order_to_payment_pending(client)
    _drive(order_id, OrderStatus.DELIVERED)
    # Admin close-out — the real endpoint, which flips DELIVERED → COMPLETED.
    from app.models.enums import RoleEnum
    from tests.helpers import create_user_direct, login_existing

    create_user_direct("+919740000019", "Admin R", [RoleEnum.ADMIN])
    admin = login_existing(client, "+919740000019")
    r = client.post(f"/api/v1/orders/{order_id}/complete", headers=admin["headers"])
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "completed"
    return farmer, buyer, order_id


def test_review_requires_completed_order(client):
    farmer, buyer, order_id = _order_to_payment_pending(client)

    r = client.post(
        "/api/v1/reviews",
        headers=buyer["headers"],
        json={"order_id": order_id, "rating": 5, "comment": "Great produce!"},
    )
    assert r.status_code == 409, r.text  # order is still payment_pending
    assert "completed" in r.json()["error"]["message"].lower()


def test_review_after_completion_succeeds_and_attributes_farmer(client):
    farmer, buyer, order_id = _completed_order(client)

    r = client.post(
        "/api/v1/reviews",
        headers=buyer["headers"],
        json={"order_id": order_id, "rating": 5, "comment": "Great produce!"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["rating"] == 5
    assert body["order_id"] == order_id
    assert body["farmer_id"] is not None  # single-farmer order → attributed
    assert body["reviewer_name"] == "Buyer B"


def test_only_the_buyer_can_review(client):
    farmer, buyer, order_id = _completed_order(client)
    other = register_user(client, OTHER_PHONE, "Other Buyer", "buyer")

    r = client.post(
        "/api/v1/reviews",
        headers=other["headers"],
        json={"order_id": order_id, "rating": 1, "comment": "Not mine."},
    )
    assert r.status_code == 403, r.text


def test_one_review_per_order(client):
    farmer, buyer, order_id = _completed_order(client)

    r = client.post(
        "/api/v1/reviews",
        headers=buyer["headers"],
        json={"order_id": order_id, "rating": 5},
    )
    assert r.status_code == 201, r.text
    r = client.post(
        "/api/v1/reviews",
        headers=buyer["headers"],
        json={"order_id": order_id, "rating": 2, "comment": "changed my mind"},
    )
    assert r.status_code == 409, r.text


def test_rating_bounds_are_enforced(client):
    farmer, buyer, order_id = _completed_order(client)
    for rating in (0, 6):
        r = client.post(
            "/api/v1/reviews",
            headers=buyer["headers"],
            json={"order_id": order_id, "rating": rating},
        )
        assert r.status_code == 422, r.text


def test_farmer_reviews_are_publicly_listed(client):
    farmer, buyer, order_id = _completed_order(client)
    client.post(
        "/api/v1/reviews",
        headers=buyer["headers"],
        json={"order_id": order_id, "rating": 4, "comment": "Fresh tomatoes"},
    )
    farmer_id = _farmer_user_id()

    r = client.get(f"/api/v1/reviews/farmer/{farmer_id}")  # no auth header
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) == 1
    assert items[0]["rating"] == 4
    assert items[0]["comment"] == "Fresh tomatoes"


def test_unknown_farmer_has_empty_reviews(client):
    r = client.get(f"/api/v1/reviews/farmer/{uuid.uuid4()}")
    assert r.status_code == 200, r.text
    assert r.json() == []
