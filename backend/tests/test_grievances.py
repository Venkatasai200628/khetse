"""Grievance tests: creation with SLA deadline, listing, admin queue."""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.commerce import Order
from app.models.enums import OrderStatus, RoleEnum
from app.services import settings_service
from tests.helpers import create_user_direct, login_existing, register_user

ADMIN_PHONE = "+919760000010"
A_PHONE = "+919760000011"
B_PHONE = "+919760000012"


def _admin(client) -> dict:
    create_user_direct(ADMIN_PHONE, "Admin A", [RoleEnum.ADMIN])
    return login_existing(client, ADMIN_PHONE)


def _user_id(phone: str) -> str:
    from app.models.user import User

    db = SessionLocal()
    try:
        return str(db.scalar(select(User).where(User.phone == phone)).id)
    finally:
        db.close()


def _iso(value: str) -> datetime:
    """Parse an API timestamp; strip tz so naive/aware never mix."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.replace(tzinfo=None)


def test_create_sets_ack_deadline_from_default_sla(client):
    user = register_user(client, A_PHONE, "Asha", "buyer")
    r = client.post(
        "/api/v1/grievances",
        headers=user["headers"],
        json={"category": "order", "subject": "Wrong item delivered", "description": "Got onions instead of tomatoes."},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "open"
    assert body["ack_deadline_at"] is not None
    delta = _iso(body["ack_deadline_at"]) - _iso(body["created_at"])
    assert timedelta(hours=23, minutes=58) < delta <= timedelta(hours=24, minutes=2)


def test_ack_deadline_follows_platform_setting(client):
    db = SessionLocal()
    try:
        settings_service.set_setting(db, "grievance_ack_hours", 48)
    finally:
        db.close()

    user = register_user(client, A_PHONE, "Asha", "buyer")
    r = client.post(
        "/api/v1/grievances",
        headers=user["headers"],
        json={"category": "payment", "subject": "Refund not received", "description": "Waiting for 2 weeks."},
    )
    body = r.json()
    delta = _iso(body["ack_deadline_at"]) - _iso(body["created_at"])
    assert timedelta(hours=47, minutes=58) < delta <= timedelta(hours=48, minutes=2)


def test_create_with_unknown_order_returns_404(client):
    user = register_user(client, A_PHONE, "Asha", "buyer")
    r = client.post(
        "/api/v1/grievances",
        headers=user["headers"],
        json={
            "category": "order",
            "subject": "Where is my order?",
            "description": "Asking about a missing order.",
            "order_id": "00000000-0000-0000-0000-000000000000",
        },
    )
    assert r.status_code == 404, r.text


def test_only_order_participants_can_grievance_it(client):
    buyer_a = register_user(client, A_PHONE, "Asha", "buyer")
    buyer_b = register_user(client, B_PHONE, "Bhanu", "buyer")

    # A minimal order owned by buyer A, inserted directly.
    db = SessionLocal()
    try:
        order = Order(
            buyer_id=uuid.UUID(_user_id(A_PHONE)), status=OrderStatus.CREATED, notes="test"
        )
        db.add(order)
        db.commit()
        order_id = str(order.id)
    finally:
        db.close()

    r = client.post(
        "/api/v1/grievances",
        headers=buyer_b["headers"],
        json={
            "category": "order",
            "subject": "Not my order",
            "description": "Probing someone else's order id.",
            "order_id": order_id,
        },
    )
    assert r.status_code == 403, r.text

    r = client.post(
        "/api/v1/grievances",
        headers=buyer_a["headers"],
        json={
            "category": "order",
            "subject": "My order issue",
            "description": "The buyer themselves complaining.",
            "order_id": order_id,
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["order_id"] == order_id


def test_list_mine_returns_only_own_grievances(client):
    user_a = register_user(client, A_PHONE, "Asha", "buyer")
    user_b = register_user(client, B_PHONE, "Bhanu", "buyer")

    for subject in ("Late delivery", "Bad packaging"):
        r = client.post(
            "/api/v1/grievances",
            headers=user_a["headers"],
            json={"category": "delivery", "subject": subject, "description": "Details here."},
        )
        assert r.status_code == 201, r.text
    client.post(
        "/api/v1/grievances",
        headers=user_b["headers"],
        json={"category": "other", "subject": "App crash", "description": "It crashed."},
    )

    r = client.get("/api/v1/grievances/mine", headers=user_a["headers"])
    assert r.status_code == 200, r.text
    page = r.json()
    assert page["total"] == 2
    assert {g["subject"] for g in page["items"]} == {"Late delivery", "Bad packaging"}


def test_admin_queue_lists_all_with_status_filter(client):
    admin = _admin(client)
    user_a = register_user(client, A_PHONE, "Asha", "buyer")
    user_b = register_user(client, B_PHONE, "Bhanu", "buyer")
    for headers in (user_a["headers"], user_b["headers"]):
        client.post(
            "/api/v1/grievances",
            headers=headers,
            json={"category": "other", "subject": "Issue", "description": "Something happened."},
        )

    r = client.get("/api/v1/grievances/admin", headers=admin["headers"])
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 2

    r = client.get(
        "/api/v1/grievances/admin", headers=admin["headers"], params={"status": "open"}
    )
    assert r.json()["total"] == 2
    r = client.get(
        "/api/v1/grievances/admin", headers=admin["headers"], params={"status": "resolved"}
    )
    assert r.json()["total"] == 0


def test_admin_queue_is_admin_only(client):
    register_user(client, A_PHONE, "Asha", "buyer")
    user_b = register_user(client, B_PHONE, "Bhanu", "buyer")
    r = client.get("/api/v1/grievances/admin", headers=user_b["headers"])
    assert r.status_code == 403, r.text


def test_subject_and_description_are_required(client):
    user = register_user(client, A_PHONE, "Asha", "buyer")
    r = client.post(
        "/api/v1/grievances",
        headers=user["headers"],
        json={"category": "order", "subject": "ab", "description": "x"},
    )
    assert r.status_code == 422, r.text  # subject shorter than 3 chars
