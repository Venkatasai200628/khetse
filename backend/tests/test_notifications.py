"""Notification centre tests: create, list mine, mark read."""

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.enums import RoleEnum
from app.models.ops import Notification
from app.models.user import User
from tests.helpers import create_user_direct, login_existing, register_user

ADMIN_PHONE = "+919750000010"
USER_PHONE = "+919750000011"


def _admin(client) -> dict:
    create_user_direct(ADMIN_PHONE, "Admin A", [RoleEnum.ADMIN])
    return login_existing(client, ADMIN_PHONE)


def _user_id_by_phone(phone: str) -> str:
    db = SessionLocal()
    try:
        return str(db.scalar(select(User).where(User.phone == phone)).id)
    finally:
        db.close()


def _create(client, headers, **overrides) -> dict:
    payload = {"category": "order", "title": "Order confirmed", "body": "Your order was confirmed."}
    payload.update(overrides)
    r = client.post("/api/v1/notifications", headers=headers, json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def test_create_for_self_and_list_mine(client):
    user = register_user(client, USER_PHONE, "Naveen", "buyer")

    created = _create(client, user["headers"])
    assert created["category"] == "order"
    assert created["user_id"] == _user_id_by_phone(USER_PHONE)
    assert created["status"] == "sent"  # in-app delivery is the write itself
    assert created["read_at"] is None

    r = client.get("/api/v1/notifications/mine", headers=user["headers"])
    assert r.status_code == 200, r.text
    page = r.json()
    assert page["total"] == 1
    assert page["unread"] == 1
    assert page["items"][0]["title"] == "Order confirmed"


def test_cannot_create_for_another_user(client):
    user = register_user(client, USER_PHONE, "Naveen", "buyer")
    register_user(client, "+919750000012", "Kiran", "farmer")

    r = client.post(
        "/api/v1/notifications",
        headers=user["headers"],
        json={
            "category": "spam",
            "title": "Hi",
            "body": "into your inbox",
            "user_id": _user_id_by_phone("+919750000012"),
        },
    )
    assert r.status_code == 403, r.text


def test_admin_can_create_for_any_user(client):
    admin = _admin(client)
    user = register_user(client, USER_PHONE, "Naveen", "buyer")

    created = _create(
        client,
        admin["headers"],
        category="grievance",
        title="Grievance acknowledged",
        body="Our team is on it.",
        user_id=_user_id_by_phone(USER_PHONE),
    )
    assert created["user_id"] == _user_id_by_phone(USER_PHONE)

    r = client.get("/api/v1/notifications/mine", headers=user["headers"])
    assert r.json()["total"] == 1


def test_mark_read_sets_status_and_is_idempotent(client):
    user = register_user(client, USER_PHONE, "Naveen", "buyer")
    nid = _create(client, user["headers"])["id"]

    r = client.post(f"/api/v1/notifications/{nid}/read", headers=user["headers"])
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "read"
    assert r.json()["read_at"] is not None
    first_read_at = r.json()["read_at"]

    # Idempotent: reading twice neither errors nor moves read_at.
    r = client.post(f"/api/v1/notifications/{nid}/read", headers=user["headers"])
    assert r.status_code == 200, r.text
    assert r.json()["read_at"] == first_read_at

    r = client.get(
        "/api/v1/notifications/mine", headers=user["headers"], params={"unread_only": True}
    )
    assert r.json()["total"] == 0


def test_cannot_mark_read_someone_elses_notification(client):
    user = register_user(client, USER_PHONE, "Naveen", "buyer")
    other = register_user(client, "+919750000013", "Priya", "buyer")
    nid = _create(client, user["headers"])["id"]

    r = client.post(f"/api/v1/notifications/{nid}/read", headers=other["headers"])
    assert r.status_code == 404, r.text  # foreign id ≡ missing id


def test_requires_authentication(client):
    assert client.get("/api/v1/notifications/mine").status_code == 401
    r = client.post("/api/v1/notifications", json={"category": "c", "title": "t", "body": "b"})
    assert r.status_code == 401


def test_rows_live_in_notifications_table(client):
    user = register_user(client, USER_PHONE, "Naveen", "buyer")
    _create(client, user["headers"])

    db = SessionLocal()
    try:
        rows = db.scalars(select(Notification)).all()
        assert len(rows) == 1
        assert rows[0].channel.value == "in_app"
    finally:
        db.close()
