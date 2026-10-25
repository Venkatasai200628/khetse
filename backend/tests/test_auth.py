"""Authentication flow tests: OTP request/verify, registration, demo login."""

from app.db.session import SessionLocal
from app.models.user import RoleEnum, User, UserRole


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_registration_flow_farmer(client):
    # 1. Request OTP (phone auto-normalised to +91…)
    r = client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "sent"
    assert body["dev_otp"] and len(body["dev_otp"]) == 6  # mock SMS provider

    # 2. Verify — unknown phone means registration required
    r = client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": "+919876543210", "code": body["dev_otp"]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["outcome"] == "registration_required"
    reg_token = r.json()["registration_token"]

    # 3. Register as farmer
    r = client.post(
        "/api/v1/auth/register",
        json={
            "registration_token": reg_token,
            "full_name": "Ravi Kumar",
            "role": "farmer",
            "preferred_language": "te",
        },
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]

    # 4. Profile reflects the farmer role
    r = client.get("/api/v1/auth/me", headers=_auth_headers(token))
    assert r.status_code == 200
    me = r.json()
    assert me["full_name"] == "Ravi Kumar"
    assert RoleEnum.FARMER.value in me["roles"]


def test_existing_user_login(client):
    r = client.post("/api/v1/auth/otp/request", json={"phone": "+919812345678"})
    code = r.json()["dev_otp"]

    r = client.post(
        "/api/v1/auth/otp/verify", json={"phone": "+919812345678", "code": code}
    )
    assert r.json()["outcome"] == "registration_required"
    reg_token = r.json()["registration_token"]
    client.post(
        "/api/v1/auth/register",
        json={"registration_token": reg_token, "full_name": "Lakshmi", "role": "buyer"},
    )

    # Second login: OTP verify now returns an access token directly
    r = client.post("/api/v1/auth/otp/request", json={"phone": "+919812345678"})
    code = r.json()["dev_otp"]
    r = client.post(
        "/api/v1/auth/otp/verify", json={"phone": "+919812345678", "code": code}
    )
    assert r.json()["outcome"] == "authenticated"
    assert r.json()["access_token"]


def test_wrong_otp_rejected(client):
    client.post("/api/v1/auth/otp/request", json={"phone": "+919811111111"})
    r = client.post(
        "/api/v1/auth/otp/verify", json={"phone": "+919811111111", "code": "000000"}
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthenticated"


def test_failed_attempt_counted(client):
    client.post("/api/v1/auth/otp/request", json={"phone": "+919822222222"})

    r = client.post(
        "/api/v1/auth/otp/verify", json={"phone": "+919822222222", "code": "123456"}
    )
    assert r.status_code == 401

    session = SessionLocal()
    from app.models.otp import OtpCode

    otp = (
        session.query(OtpCode)
        .filter(OtpCode.phone == "+919822222222")
        .order_by(OtpCode.created_at.desc())
        .first()
    )
    session.close()
    assert otp.attempts == 1


def test_otp_rate_limited(client):
    for _ in range(5):
        r = client.post("/api/v1/auth/otp/request", json={"phone": "+919833333333"})
        assert r.status_code == 200
    r = client.post("/api/v1/auth/otp/request", json={"phone": "+919833333333"})
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "rate_limited"


def test_admin_role_cannot_be_self_registered(client):
    r = client.post("/api/v1/auth/otp/request", json={"phone": "+919844444444"})
    code = r.json()["dev_otp"]
    r = client.post(
        "/api/v1/auth/otp/verify", json={"phone": "+919844444444", "code": code}
    )
    reg_token = r.json()["registration_token"]

    r = client.post(
        "/api/v1/auth/register",
        json={
            "registration_token": reg_token,
            "full_name": "Mallory",
            "role": "admin",
        },
    )
    assert r.status_code == 422


def test_invalid_phone_rejected(client):
    r = client.post("/api/v1/auth/otp/request", json={"phone": "123"})
    assert r.status_code == 422


def test_me_requires_token(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_demo_login(client):
    session = SessionLocal()
    user = User(
        phone="+919800000001",
        full_name="Demo Farmer",
        demo_code="farmer1",
        roles=[UserRole(role=RoleEnum.FARMER)],
    )
    session.add(user)
    session.commit()
    session.close()

    r = client.post("/api/v1/auth/demo-login", json={"demo_code": "farmer1"})
    assert r.status_code == 200
    assert r.json()["user"]["full_name"] == "Demo Farmer"

    r = client.post("/api/v1/auth/demo-login", json={"demo_code": "unknown"})
    assert r.status_code == 404
