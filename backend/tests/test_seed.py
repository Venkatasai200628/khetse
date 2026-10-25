"""Seed tests: completeness of the demo dataset and idempotency.

Runs app.db.seed.seed() against the throwaway test database twice and
asserts the second run converges to the same predictable state.
"""

from sqlalchemy import func, select

from app.db.seed import seed
from app.db.session import SessionLocal
from app.models.catalog import Commodity, ProduceListing
from app.models.commerce import Order
from app.models.enums import OrderStatus, PriceSourceType
from app.models.market import MarketPriceObservation
from app.models.ops import Grievance  # noqa: F401 — ops models importable
from app.models.profiles import (
    CollectionCentre,
    DriverProfile,
    FarmerProfile,
    FpoProfile,
)
from app.models.user import User

DEMO_CODES = {"farmer1", "buyer1", "driver1", "fpo1", "admin1"}


def _counts() -> dict:
    db = SessionLocal()
    try:
        return {
            "demo_users": len(
                db.scalars(select(User).where(User.demo_code.in_(DEMO_CODES))).all()
            ),
            "commodities": db.scalar(select(func.count()).select_from(Commodity)) or 0,
            "synthetic_listings": db.scalar(
                select(func.count())
                .select_from(ProduceListing)
                .where(ProduceListing.is_synthetic.is_(True))
            )
            or 0,
            "observations": db.scalar(
                select(func.count()).select_from(MarketPriceObservation)
            )
            or 0,
            "synthetic_orders": db.scalar(
                select(func.count())
                .select_from(Order)
                .where(Order.is_synthetic.is_(True))
            )
            or 0,
        }
    finally:
        db.close()


def test_seed_creates_demo_accounts_fpo_and_profiles(db):
    seed()

    db = SessionLocal()
    try:
        users = {
            u.demo_code: u
            for u in db.scalars(select(User).where(User.demo_code.in_(DEMO_CODES)))
        }
        assert set(users) == DEMO_CODES

        fpo = db.scalar(select(FpoProfile))
        assert fpo is not None and fpo.registration_number

        centre = db.scalar(select(CollectionCentre))
        assert centre is not None and centre.fpo_id == fpo.id

        # fpo1 operator is tied to the FPO; farmer1 is a member of it.
        assert users["fpo1"].fpo_id == fpo.id
        farmer_profile = db.scalar(
            select(FarmerProfile).where(FarmerProfile.user_id == users["farmer1"].id)
        )
        assert farmer_profile is not None
        assert farmer_profile.fpo_id == fpo.id

        driver_profile = db.scalar(
            select(DriverProfile).where(DriverProfile.user_id == users["driver1"].id)
        )
        assert driver_profile is not None
    finally:
        db.close()


def test_seed_catalogue_and_market_data(db):
    seed()

    db = SessionLocal()
    try:
        commodities = db.scalars(select(Commodity)).all()
        assert len(commodities) == 8
        assert all(c.name_te for c in commodities), "every commodity carries a Telugu name"

        listings = db.scalars(select(ProduceListing)).all()
        assert len(listings) == 10
        assert all(l.is_synthetic for l in listings), "every seeded listing is labelled"

        observations = db.scalars(select(MarketPriceObservation)).all()
        assert len(observations) > 0
        assert all(o.is_synthetic for o in observations)
        assert {o.source for o in observations} == {PriceSourceType.SYNTHETIC}
    finally:
        db.close()


def test_seed_orders_span_lifecycle_stages(db):
    seed()

    db = SessionLocal()
    try:
        orders = db.scalars(select(Order)).all()
        assert len(orders) == 5
        assert all(o.is_synthetic for o in orders)
        statuses = {o.status for o in orders}
        assert {
            OrderStatus.PAYMENT_PENDING,
            OrderStatus.CONFIRMED,
            OrderStatus.OUT_FOR_DELIVERY,
            OrderStatus.COMPLETED,
            OrderStatus.CANCELLED,
        } <= statuses
        # The completed order went through the real state machine, so every
        # hop is auditable and payment was marked success on the way.
        completed = next(o for o in orders if o.status == OrderStatus.COMPLETED)
        assert completed.delivered_at is not None
        assert completed.completed_at is not None
    finally:
        db.close()


def test_seed_is_idempotent(db):
    seed()
    first = _counts()
    assert first["demo_users"] == 5
    assert first["commodities"] == 8
    assert first["synthetic_listings"] == 10
    assert first["observations"] == 8 * 14  # 8 commodities × 14 days
    assert first["synthetic_orders"] == 5

    seed()
    second = _counts()
    assert second == first, "re-running the seed must not duplicate anything"


def test_welcome_serves_seeded_codes_and_everyone_logs_in(client, db):
    """Regression: the app's one-tap demo buttons must use the SAME handles
    the backend seeds — GET /welcome is the authoritative source and every
    listed code must actually log in via POST /auth/demo-login."""
    seed()

    r = client.get("/api/v1/welcome")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["demo_mode"] is True
    assert set(body["demo_codes"]) == DEMO_CODES

    for code in body["demo_codes"]:
        r = client.post("/api/v1/auth/demo-login", json={"demo_code": code})
        assert r.status_code == 200, f"demo login failed for {code!r}: {r.text}"
        assert "access_token" in r.json()
