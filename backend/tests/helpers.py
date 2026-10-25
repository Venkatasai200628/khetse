"""Shared test helpers: API-level user registration and data factories."""

from app.db.session import SessionLocal
from app.models.catalog import Commodity
from app.models.enums import CommodityCategory, RoleEnum, UnitEnum, UserStatus
from app.models.user import User, UserRole


def register_user(client, phone: str, name: str, role: str) -> dict:
    """Full OTP registration flow; returns dict with token + headers."""
    r = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    code = r.json()["dev_otp"]
    r = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "code": code})
    assert r.json()["outcome"] == "registration_required", r.text
    reg_token = r.json()["registration_token"]
    r = client.post(
        "/api/v1/auth/register",
        json={
            "registration_token": reg_token,
            "full_name": name,
            "role": role,
        },
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"token": token, "headers": {"Authorization": f"Bearer {token}"}}


def login_existing(client, phone: str) -> dict:
    r = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    code = r.json()["dev_otp"]
    r = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "code": code})
    token = r.json()["access_token"]
    return {"token": token, "headers": {"Authorization": f"Bearer {token}"}}


def create_user_direct(phone: str, full_name: str, roles, **kwargs) -> User:
    """Insert a user straight into the DB for roles that cannot
    self-register (admin, FPO operator); pair with login_existing."""
    db = SessionLocal()
    try:
        user = User(
            phone=phone,
            full_name=full_name,
            status=UserStatus.ACTIVE,
            roles=[UserRole(role=role) for role in roles],
            **kwargs,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def seed_commodity(name_en="Tomato", name_te="టమాటా", category=CommodityCategory.VEGETABLE):
    session = SessionLocal()
    commodity = Commodity(
        name_en=name_en,
        name_te=name_te,
        category=category,
        default_unit=UnitEnum.KG,
    )
    session.add(commodity)
    session.commit()
    session.refresh(commodity)
    commodity_id = str(commodity.id)
    session.close()
    return commodity_id
