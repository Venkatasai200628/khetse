"""Demo data seeding: accounts, FPO, catalogue, listings, market data, orders.

Run from the backend directory after applying migrations:

    ../.venv/Scripts/python -m app.db.seed   # Windows
    ../.venv/bin/python -m app.db.seed       # Linux/macOS

Idempotent: every entity is matched by its natural key (phone, demo_code,
commodity name, farmer+commodity+grade, idempotency key, market+day), so
re-running never duplicates and always converges to the same predictable
demo state. Every seeded listing, order and market observation carries
``is_synthetic=True`` so the UI can label them as demo data, and the demo
accounts carry ``demo_code``s usable with POST /auth/demo-login while
DEMO_MODE is on:

    farmer1  buyer1  driver1  fpo1  admin1

Seeded demo orders intentionally span the order lifecycle — payment_pending,
confirmed, out_for_delivery, completed and cancelled — by driving the real
order services and state machine (never by poking status columns), so the
demo exercises exactly the transitions production allows.
"""

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

import app.models  # noqa: F401 — registers every model on Base.metadata
from app.db.session import SessionLocal
from app.models.catalog import Commodity, ProduceListing
from app.models.commerce import Order
from app.models.enums import (
    CommodityCategory,
    OrderStatus,
    PaymentStatus,
    PriceSourceType,
    RoleEnum,
    UnitEnum,
    UserStatus,
)
from app.models.market import MarketPriceObservation
from app.models.profiles import (
    BuyerProfile,
    CollectionCentre,
    DriverProfile,
    FarmerProfile,
    FpoProfile,
)
from app.models.user import User, UserRole
from app.services import (
    cart_service,
    listing_service,
    order_service,
    order_state,
)

logger = logging.getLogger("khetse.seed")

FARM_LOCATION = {
    "village": "Kothur",
    "district": "Ranga Reddy",
    "state": "Telangana",
    "farm_lat": 17.3606,
    "farm_lng": 78.2854,
}

FPO_REG_NUMBER = "FPO-TG-RANGA-001"
FPO_NAME = "Kothur Farmer Producer Organisation"
CENTRE_NAME = "Kothur Collection Centre"

# (demo_code, phone, full_name, roles) — demo codes double as login handles.
DEMO_USERS = [
    ("farmer1", "+919600000001", "Ramesh Reddy", [RoleEnum.FARMER]),
    ("buyer1", "+919600000002", "Anita Sharma", [RoleEnum.BUYER]),
    ("admin1", "+919600000003", "KhetSe Admin", [RoleEnum.ADMIN]),
    ("driver1", "+919600000004", "Suresh Yadav", [RoleEnum.DRIVER]),
    ("fpo1", "+919600000005", "Lakshmi Devi", [RoleEnum.FPO_OPERATOR]),
]

# (name_en, name_te, category, default_unit)
COMMODITIES = [
    ("Tomato", "టమాటా", CommodityCategory.VEGETABLE, UnitEnum.KG),
    ("Onion", "ఉల్లి", CommodityCategory.VEGETABLE, UnitEnum.KG),
    ("Potato", "బంగాళదుంప", CommodityCategory.VEGETABLE, UnitEnum.KG),
    ("Green Chilli", "పచ్చిమిర్చి", CommodityCategory.VEGETABLE, UnitEnum.KG),
    ("Mango", "మామిడి", CommodityCategory.FRUIT, UnitEnum.DOZEN),
    ("Banana", "అరటి", CommodityCategory.FRUIT, UnitEnum.DOZEN),
    ("Rice", "వరి", CommodityCategory.GRAIN, UnitEnum.QUINTAL),
    ("Turmeric", "పసుపు", CommodityCategory.OTHER, UnitEnum.KG),
]

# (commodity, quantity, unit, min ₹, listed ₹, grade) — 10 labelled listings.
LISTINGS = [
    ("Tomato", 200.0, UnitEnum.KG, 12, 18, "A"),
    ("Tomato", 100.0, UnitEnum.KG, 10, 15, "B"),
    ("Onion", 500.0, UnitEnum.KG, 20, 26, "A"),
    ("Onion", 300.0, UnitEnum.KG, 18, 23, "B"),
    ("Potato", 400.0, UnitEnum.KG, 15, 21, "A"),
    ("Green Chilli", 80.0, UnitEnum.KG, 30, 38, "A"),
    ("Mango", 120.0, UnitEnum.DOZEN, 250, 320, "A"),
    ("Banana", 60.0, UnitEnum.DOZEN, 40, 52, "B"),
    ("Rice", 40.0, UnitEnum.QUINTAL, 3500, 4200, "A"),
    ("Turmeric", 150.0, UnitEnum.KG, 80, 95, "A"),
]

# Synthetic mandi observations: Bowenpally market, N days back per commodity.
MARKET_NAME = "Bowenpally"
MARKET_DAYS = 14
# commodity -> modal price in paise per default unit (₹16/kg tomato, …)
OBSERVATION_BASE_PAISE = {
    "Tomato": 1600,
    "Onion": 2300,
    "Potato": 1800,
    "Green Chilli": 3400,
    "Mango": 28000,
    "Banana": 4500,
    "Rice": 380000,
    "Turmeric": 8800,
}

# (idempotency key, commodity, grade, quantity, target lifecycle stage)
ORDERS = [
    ("demo-order-1-payment-pending", "Tomato", "A", 10.0, OrderStatus.PAYMENT_PENDING),
    ("demo-order-2-confirmed", "Onion", "A", 20.0, OrderStatus.CONFIRMED),
    ("demo-order-3-out-for-delivery", "Potato", "A", 15.0, OrderStatus.OUT_FOR_DELIVERY),
    ("demo-order-4-completed", "Mango", "A", 2.0, OrderStatus.COMPLETED),
    ("demo-order-5-cancelled", "Banana", "B", 5.0, OrderStatus.CANCELLED),
]


def _get_or_create_user(
    db, *, phone: str, full_name: str, roles: list[RoleEnum], demo_code: str
) -> User:
    user = db.scalar(select(User).where(User.phone == phone))
    if user is None:
        user = User(
            phone=phone,
            full_name=full_name,
            status=UserStatus.ACTIVE,
            demo_code=demo_code,
            roles=[UserRole(role=role) for role in roles],
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("created demo user %s (%s)", demo_code, phone)
    return user


def _get_or_create_commodity(
    db, name_en: str, name_te: str, category, unit: UnitEnum
) -> Commodity:
    commodity = db.scalar(select(Commodity).where(Commodity.name_en == name_en))
    if commodity is None:
        commodity = Commodity(name_en=name_en, name_te=name_te, category=category, default_unit=unit)
        db.add(commodity)
        db.commit()
        db.refresh(commodity)
        logger.info("created commodity %s", name_en)
    return commodity


def _seed_fpo_and_centre(db) -> tuple[FpoProfile, CollectionCentre]:
    fpo = db.scalar(select(FpoProfile).where(FpoProfile.registration_number == FPO_REG_NUMBER))
    if fpo is None:
        fpo = FpoProfile(
            name=FPO_NAME,
            registration_number=FPO_REG_NUMBER,
            district=FARM_LOCATION["district"],
            state=FARM_LOCATION["state"],
            address_line="FPO Office, Kothur Main Road",
            lat=FARM_LOCATION["farm_lat"],
            lng=FARM_LOCATION["farm_lng"],
        )
        db.add(fpo)
        db.commit()
        db.refresh(fpo)
        logger.info("created FPO %s", FPO_NAME)

    centre = db.scalar(
        select(CollectionCentre).where(
            CollectionCentre.name == CENTRE_NAME,
            CollectionCentre.district == FARM_LOCATION["district"],
        )
    )
    if centre is None:
        centre = CollectionCentre(
            fpo_id=fpo.id,
            name=CENTRE_NAME,
            district=FARM_LOCATION["district"],
            state=FARM_LOCATION["state"],
            address_line="Agri Market Yard, Kothur",
            lat=FARM_LOCATION["farm_lat"],
            lng=FARM_LOCATION["farm_lng"],
        )
        db.add(centre)
        db.commit()
        db.refresh(centre)
        logger.info("created collection centre %s", CENTRE_NAME)
    return fpo, centre


def _seed_profiles(db, users: dict[str, User], fpo: FpoProfile) -> None:
    farmer, buyer, driver = users["farmer1"], users["buyer1"], users["driver1"]

    if db.scalar(select(FarmerProfile).where(FarmerProfile.user_id == farmer.id)) is None:
        db.add(FarmerProfile(user_id=farmer.id, fpo_id=fpo.id, **FARM_LOCATION))
        logger.info("created farmer profile (FPO member)")

    if db.scalar(select(BuyerProfile).where(BuyerProfile.user_id == buyer.id)) is None:
        db.add(
            BuyerProfile(
                user_id=buyer.id,
                address_line="1-2-3, Demo Street, Kothur",
                city="Kothur",
                district=FARM_LOCATION["district"],
                state=FARM_LOCATION["state"],
                lat=17.3850,
                lng=78.4867,
            )
        )

    if db.scalar(select(DriverProfile).where(DriverProfile.user_id == driver.id)) is None:
        db.add(
            DriverProfile(
                user_id=driver.id,
                license_number="TS09DEMO0001",
                service_district=FARM_LOCATION["district"],
            )
        )
    db.commit()


def _seed_listings(db, farmer: User, centre: CollectionCentre) -> dict[str, ProduceListing]:
    """10 synthetic listings; existing ones matched by farmer+commodity+grade
    so re-running never duplicates."""
    commodities = {
        name: _get_or_create_commodity(db, name, te, cat, unit)
        for name, te, cat, unit in COMMODITIES
    }
    harvest = date.today() - timedelta(days=2)
    created: dict[str, ProduceListing] = {}
    for name, qty, unit, min_rupees, listed_rupees, grade in LISTINGS:
        commodity = commodities[name]
        listing = db.scalar(
            select(ProduceListing).where(
                ProduceListing.farmer_id == farmer.id,
                ProduceListing.commodity_id == commodity.id,
                ProduceListing.quality_grade == grade,
            )
        )
        if listing is None:
            listing = listing_service.create_listing(
                db,
                farmer,
                commodity_id=commodity.id,
                quantity_total=qty,
                unit=unit.value,
                min_price_paise=min_rupees * 100,
                listed_price_paise=listed_rupees * 100,
                description=f"Fresh {name.lower()} from {FARM_LOCATION['village']} — demo data.",
                quality_grade=grade,
                harvest_date=harvest,
                collection_centre_id=centre.id,
                farm_lat=FARM_LOCATION["farm_lat"],
                farm_lng=FARM_LOCATION["farm_lng"],
                is_synthetic=True,
            )
            logger.info("created listing %s grade %s", name, grade)
        created[f"{name}:{grade}"] = listing
    return created


def _seed_market_observations(db, commodities: dict[str, Commodity]) -> int:
    """Deterministic synthetic mandi prices for the last MARKET_DAYS days —
    the data behind the price-recommendation and forecast endpoints."""
    written = 0
    for name, base in OBSERVATION_BASE_PAISE.items():
        commodity = commodities[name]
        step = max(50, base // 20)
        for back in range(MARKET_DAYS):
            observed_on = date.today() - timedelta(days=back)
            exists = db.scalar(
                select(MarketPriceObservation.id).where(
                    MarketPriceObservation.commodity_id == commodity.id,
                    MarketPriceObservation.market_name == MARKET_NAME,
                    MarketPriceObservation.observed_on == observed_on,
                )
            )
            if exists is not None:
                continue
            wobble = ((back * 3) % 5) - 2  # deterministic −2..+2 step wobble
            modal = base + wobble * step
            db.add(
                MarketPriceObservation(
                    commodity_id=commodity.id,
                    market_name=MARKET_NAME,
                    district=FARM_LOCATION["district"],
                    state=FARM_LOCATION["state"],
                    observed_on=observed_on,
                    min_price_paise=modal - 2 * step,
                    modal_price_paise=modal,
                    max_price_paise=modal + 2 * step,
                    unit=commodity.default_unit,
                    arrival_quantity=100.0 + back,
                    source=PriceSourceType.SYNTHETIC,
                    source_ref=f"seed:{name.lower()}:{observed_on.isoformat()}",
                    is_synthetic=True,
                )
            )
            written += 1
    db.commit()
    if written:
        logger.info("created %d synthetic market observations", written)
    return written


def _create_order_at_stage(
    db,
    users: dict[str, User],
    listing: ProduceListing,
    *,
    key: str,
    quantity: float,
    target: OrderStatus,
) -> Order:
    """Create one demo order through the REAL checkout + state machine, then
    advance it to `target`. Existing orders (matched by idempotency key) are
    returned untouched — the whole path only runs once."""
    order = db.scalar(select(Order).where(Order.idempotency_key == key))
    if order is not None:
        return order

    buyer, farmer, admin, driver = (
        users["buyer1"], users["farmer1"], users["admin1"], users["driver1"]
    )
    cart_service.add_item(db, buyer, listing.id, quantity)
    order = order_service.create_order_from_cart(
        db,
        buyer,
        idempotency_key=key,
        fulfilment="delivery",
        delivery_name="Anita Sharma",
        delivery_phone="+919600000002",
        delivery_address="1-2-3, Demo Street, Kothur",
        delivery_district=FARM_LOCATION["district"],
        delivery_lat=17.3850,
        delivery_lng=78.4867,
        notes="Seeded demo order (synthetic).",
    )
    order.is_synthetic = True
    db.commit()
    db.refresh(order)

    order_service.farmer_respond(db, farmer, order.id, accept=True)  # → payment_pending

    if target in (OrderStatus.CONFIRMED, OrderStatus.OUT_FOR_DELIVERY, OrderStatus.COMPLETED):
        # Stands in for the payment-success webhook; money columns were
        # already computed at checkout by the real pricing service.
        order_state.apply_transition(
            db, order, OrderStatus.CONFIRMED,
            role_override="system", reason="Seed: synthetic payment captured",
        )
        order.payment_status = PaymentStatus.SUCCESS
        db.commit()

    if target in (OrderStatus.OUT_FOR_DELIVERY, OrderStatus.COMPLETED):
        order_state.apply_transition(
            db, order, OrderStatus.PICKUP_SCHEDULED,
            role_override="system", reason="Seed: pickup scheduled",
        )
        db.commit()
        order_state.apply_transition(
            db, order, OrderStatus.PICKED_UP, user=driver, reason="Seed: picked up"
        )
        db.commit()
        order_state.apply_transition(
            db, order, OrderStatus.OUT_FOR_DELIVERY, user=driver,
            reason="Seed: out for delivery",
        )
        db.commit()

    if target == OrderStatus.COMPLETED:
        order_state.apply_transition(
            db, order, OrderStatus.DELIVERED, user=driver, reason="Seed: delivered"
        )
        order.delivered_at = datetime.now(timezone.utc)
        db.commit()
        order = order_service.complete_order(db, admin, order.id)

    if target == OrderStatus.CANCELLED:
        order_service.buyer_cancel(db, buyer, order.id, reason="Seed: buyer cancelled")

    logger.info("demo order %s at stage %s", key, target.value)
    return order


def seed() -> None:
    db = SessionLocal()
    try:
        fpo, centre = _seed_fpo_and_centre(db)

        users: dict[str, User] = {}
        for demo_code, phone, full_name, roles in DEMO_USERS:
            users[demo_code] = _get_or_create_user(
                db, phone=phone, full_name=full_name, roles=roles, demo_code=demo_code
            )
        fpo_user = users["fpo1"]
        if fpo_user.fpo_id is None:
            fpo_user.fpo_id = fpo.id
            db.commit()

        _seed_profiles(db, users, fpo)

        commodities = {
            name: _get_or_create_commodity(db, name, te, cat, unit)
            for name, te, cat, unit in COMMODITIES
        }
        listings = _seed_listings(db, users["farmer1"], centre)
        _seed_market_observations(db, commodities)

        for key, commodity_name, grade, quantity, target in ORDERS:
            listing = listings[f"{commodity_name}:{grade}"]
            _create_order_at_stage(
                db, users, listing, key=key, quantity=quantity, target=target
            )

        logger.info("seed complete: demo logins farmer1/buyer1/driver1/fpo1/admin1")
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    seed()
