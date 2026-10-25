"""Shared-logistics tests: shipment planning, driver hand-off, QR-verified
stop completion, replay protection, failure paths and privacy rules.

Covers the invariants the logistics contract demands: one pickup stop per
distinct farmer, one crate per order, nearest-neighbour routing, driver
views free of buyer PII, secret qr_tokens never in responses, legal-only
order transitions (via the shared state machine) and reservation consumption
on completion.
"""

import json
import re
import uuid

from sqlalchemy import select

from app.api.v1 import shipments as shipments_api
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.db.session import SessionLocal
from app.main import app
from app.models.enums import RoleEnum, VehicleType
from app.models.logistics import CrateLabel, QrVerificationEvent
from app.models.profiles import (
    CollectionCentre,
    DriverProfile,
    FarmerProfile,
    FpoProfile,
    Vehicle,
)
from app.models.user import User
from app.utils.geo import haversine_km
from tests.helpers import (
    create_user_direct,
    login_existing,
    register_user,
    seed_commodity,
)

# The logistics router is registered by app.api.v1; while that one-line
# wiring lands, include it here (guarded so double registration is
# impossible once app.api.v1 takes over).
if not any(
    getattr(route, "path", "").startswith("/api/v1/shipments")
    for route in app.routes
):
    app.include_router(shipments_api.router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _make_farmer(
    client,
    phone,
    name,
    *,
    village="Kothur",
    district="Ranga Reddy",
    lat=17.3606,
    lng=78.2854,
    fpo_id=None,
):
    farmer = register_user(client, phone, name, "farmer")
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.phone == phone))
        db.add(
            FarmerProfile(
                user_id=user.id,
                village=village,
                district=district,
                state="Telangana",
                farm_lat=lat,
                farm_lng=lng,
                fpo_id=fpo_id,
            )
        )
        db.commit()
    finally:
        db.close()
    return farmer


def _make_operator(phone="+919710000003", name="FPO Operator"):
    db = SessionLocal()
    try:
        fpo = FpoProfile(name="Kothur FPO", district="Ranga Reddy", state="Telangana")
        db.add(fpo)
        db.commit()
        fpo_id = fpo.id
    finally:
        db.close()
    create_user_direct(phone, name, [RoleEnum.FPO_OPERATOR], fpo_id=fpo_id)
    return fpo_id


def _make_driver(client, phone, name, *, available=True, plate="TS09AB1234"):
    driver = register_user(client, phone, name, "driver")
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.phone == phone))
        db.add(
            DriverProfile(
                user_id=user.id,
                license_number="DL0120220001234",
                service_district="Ranga Reddy",
                is_available=available,
            )
        )
        db.add(
            Vehicle(
                driver_id=user.id,
                plate_number=plate,
                vehicle_type=VehicleType.TEMPO,
                capacity_kg=750,
                service_district="Ranga Reddy",
            )
        )
        db.commit()
    finally:
        db.close()
    return driver


def _make_collection_centre(lat=17.3850, lng=78.4867):
    db = SessionLocal()
    try:
        centre = CollectionCentre(
            name="Kothur Collection Centre",
            district="Ranga Reddy",
            state="Telangana",
            lat=lat,
            lng=lng,
        )
        db.add(centre)
        db.commit()
        return centre.id
    finally:
        db.close()


def _make_confirmed_order(
    client,
    farmer,
    buyer,
    commodity_id,
    *,
    idempotency_key,
    qty=10,
    district="Kurnool",
    farm_lat=17.3606,
    farm_lng=78.2854,
):
    """listing → cart → checkout → farmer accept → demo payment → CONFIRMED."""
    r = client.post(
        "/api/v1/listings",
        headers=farmer["headers"],
        json={
            "commodity_id": commodity_id,
            "quantity_total": 100,
            "unit": "kg",
            "min_price_paise": 1500,
            "listed_price_paise": 2000,
            "quality_grade": "A",
            "farm_lat": farm_lat,
            "farm_lng": farm_lng,
        },
    )
    assert r.status_code == 201, r.text
    listing = r.json()

    r = client.post(
        "/api/v1/cart/items",
        headers=buyer["headers"],
        json={"listing_id": listing["id"], "quantity": qty},
    )
    assert r.status_code == 200, r.text

    r = client.post(
        "/api/v1/orders/checkout",
        headers=buyer["headers"],
        json={
            "idempotency_key": idempotency_key,
            "fulfilment": "delivery",
            "delivery_name": "Sita Rao",
            "delivery_phone": "+919888777666",
            "delivery_address": "12-34, MG Road",
            "delivery_district": district,
        },
    )
    assert r.status_code == 201, r.text
    order = r.json()

    r = client.post(
        f"/api/v1/orders/{order['id']}/farmer-response",
        headers=farmer["headers"],
        json={"accept": True},
    )
    assert r.json()["status"] == "payment_pending", r.text

    r = client.post(f"/api/v1/orders/{order['id']}/pay", headers=buyer["headers"])
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "confirmed"
    return order, listing


def _plan_shipment(client, operator, order_ids, **extra):
    r = client.post(
        "/api/v1/shipments",
        headers=operator["headers"],
        json={"order_ids": order_ids, **extra},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _get_crate_token(order_id):
    db = SessionLocal()
    try:
        crate = db.scalar(
            select(CrateLabel).where(CrateLabel.order_id == uuid.UUID(order_id))
        )
        return crate.qr_token, crate.code
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------


def test_create_shipment_builds_stops_crates_and_manifest(client):
    commodity_id = seed_commodity()
    fpo_id = _make_operator()
    farmer = _make_farmer(client, "+919710000001", "Member Farmer", fpo_id=fpo_id)
    buyer = register_user(client, "+919710000002", "Sita Rao", "buyer")
    order, _ = _make_confirmed_order(
        client, farmer, buyer, commodity_id, idempotency_key="k-log-1"
    )
    centre_id = _make_collection_centre()

    shipment = _plan_shipment(
        client, login_existing(client, "+919710000003"), [order["id"]],
        collection_centre_id=str(centre_id),
    )

    assert shipment["status"] == "planned"
    assert shipment["solver"] == "nearest_neighbour"
    assert shipment["route_distance_km"] > 0
    assert len(shipment["route_data"]["stop_order"]) == 2

    # One pickup stop + one delivery stop, sequenced 1..n.
    stops = shipment["stops"]
    assert [s["sequence"] for s in stops] == [1, 2]
    pickup = next(s for s in stops if s["stop_type"] == "pickup")
    delivery = next(s for s in stops if s["stop_type"] == "delivery")
    assert pickup["label"] == "Kothur, Ranga Reddy"
    assert pickup["lat"] == 17.3606 and pickup["lng"] == 78.2854
    assert pickup["order_id"] is None
    assert pickup["status"] == "pending"
    assert delivery["label"] == "Buyer · Kurnool"
    assert delivery["order_id"] == order["id"]

    # One crate per order; the secret QR token never appears anywhere.
    assert len(shipment["crates"]) == 1
    crate = shipment["crates"][0]
    assert re.fullmatch(r"KS-[0-9a-f]{10}", crate["code"])
    assert crate["status"] == "created"
    assert crate["quantity"] == 10 and crate["unit"] == "kg"
    assert crate["grade"] == "A"
    assert crate["order_id"] == order["id"]
    token, _ = _get_crate_token(order["id"])
    assert token not in json.dumps(shipment)  # the secret token is never exposed

    # Manifest with the documented number format and content.
    manifest = shipment["manifest"]
    assert re.fullmatch(r"MAN-\d{8}-[0-9a-f]{6}", manifest["manifest_number"])
    assert order["id"] in manifest["content"]["orders"]
    assert crate["code"] in [c["code"] for c in manifest["content"]["crates"]]

    # The order moved through the shared state machine.
    r = client.get(f"/api/v1/orders/{order['id']}", headers=buyer["headers"])
    assert r.json()["status"] == "pickup_scheduled"


def test_nearest_neighbour_visits_nearest_pickup_first(client):
    commodity_id = seed_commodity()
    fpo_id = _make_operator()
    operator = login_existing(client, "+919710000003")
    buyer = register_user(client, "+919710000002", "Sita Rao", "buyer")
    # Two member farms: one ~2 km from the centre, one ~22 km away.
    near = _make_farmer(
        client, "+919710000011", "Near Farmer",
        village="Nearvillage", lat=17.4000, lng=78.4700, fpo_id=fpo_id,
    )
    far = _make_farmer(
        client, "+919710000012", "Far Farmer",
        village="Farvillage", lat=17.3000, lng=78.3000, fpo_id=fpo_id,
    )
    order_near, _ = _make_confirmed_order(
        client, near, buyer, commodity_id, idempotency_key="k-near",
        farm_lat=17.4000, farm_lng=78.4700,
    )
    order_far, _ = _make_confirmed_order(
        client, far, buyer, commodity_id, idempotency_key="k-far",
        farm_lat=17.3000, farm_lng=78.3000,
    )
    centre_id = _make_collection_centre()  # (17.3850, 78.4867)

    shipment = _plan_shipment(
        client, operator,
        [order_far["id"], order_near["id"]],  # client order must not matter
        collection_centre_id=str(centre_id),
    )

    stops = shipment["stops"]
    assert [s["sequence"] for s in stops] == [1, 2, 3, 4]
    # Nearest-neighbour: the pickup closest to the collection centre first.
    assert stops[0]["stop_type"] == "pickup"
    assert stops[0]["label"].startswith("Nearvillage")
    assert stops[1]["label"].startswith("Farvillage")
    # Deliveries carry no coordinates here → they trail the routed pickups.
    assert all(s["stop_type"] == "delivery" for s in stops[2:])

    expected_km = round(
        haversine_km(17.3850, 78.4867, 17.4000, 78.4700)
        + haversine_km(17.4000, 78.4700, 17.3000, 78.3000),
        3,
    )
    assert shipment["route_distance_km"] == expected_km
    assert shipment["route_data"]["stop_order"] == [
        s["id"] for s in stops
    ]


def test_one_pickup_stop_per_distinct_farmer(client):
    commodity_id = seed_commodity()
    fpo_id = _make_operator()
    farmer = _make_farmer(client, "+919710000001", "Member Farmer", fpo_id=fpo_id)
    buyer = register_user(client, "+919710000002", "Sita Rao", "buyer")
    order_a, _ = _make_confirmed_order(
        client, farmer, buyer, commodity_id, idempotency_key="k-a"
    )
    order_b, _ = _make_confirmed_order(
        client, farmer, buyer, commodity_id, idempotency_key="k-b"
    )

    shipment = _plan_shipment(
        client, login_existing(client, "+919710000003"),
        [order_a["id"], order_b["id"]],
    )
    pickups = [s for s in shipment["stops"] if s["stop_type"] == "pickup"]
    deliveries = [s for s in shipment["stops"] if s["stop_type"] == "delivery"]
    assert len(pickups) == 1
    assert len(deliveries) == 2
    assert {d["order_id"] for d in deliveries} == {order_a["id"], order_b["id"]}
    assert len(shipment["crates"]) == 2


def test_fpo_operator_scope_and_confirmed_status_enforced(client):
    commodity_id = seed_commodity()
    fpo_id = _make_operator()
    operator = login_existing(client, "+919710000003")
    buyer = register_user(client, "+919710000002", "Sita Rao", "buyer")

    # An order from a NON-member farmer must be rejected.
    outsider = _make_farmer(
        client, "+919710000007", "Outsider Farmer", fpo_id=None
    )
    order, _ = _make_confirmed_order(
        client, outsider, buyer, commodity_id, idempotency_key="k-out"
    )
    r = client.post(
        "/api/v1/shipments",
        headers=operator["headers"],
        json={"order_ids": [order["id"]]},
    )
    assert r.status_code == 403, r.text

    # A member order that is not CONFIRMED yet cannot be planned.
    member = _make_farmer(client, "+919710000001", "Member Farmer", fpo_id=fpo_id)
    r = client.post(
        "/api/v1/listings",
        headers=member["headers"],
        json={
            "commodity_id": commodity_id,
            "quantity_total": 100,
            "unit": "kg",
            "min_price_paise": 1500,
            "listed_price_paise": 2000,
        },
    )
    assert r.status_code == 201, r.text
    listing = r.json()
    client.post(
        "/api/v1/cart/items",
        headers=buyer["headers"],
        json={"listing_id": listing["id"], "quantity": 5},
    )
    r = client.post(
        "/api/v1/orders/checkout",
        headers=buyer["headers"],
        json={
            "idempotency_key": "k-pending",
            "fulfilment": "delivery",
            "delivery_name": "Sita Rao",
            "delivery_phone": "+919888777666",
            "delivery_address": "12-34, MG Road",
            "delivery_district": "Kurnool",
        },
    )
    pending_order = r.json()
    r = client.post(
        "/api/v1/shipments",
        headers=operator["headers"],
        json={"order_ids": [pending_order["id"]]},
    )
    assert r.status_code == 409, r.text

    # Empty order list is a validation error.
    r = client.post(
        "/api/v1/shipments", headers=operator["headers"], json={"order_ids": []}
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Driver directory
# ---------------------------------------------------------------------------


def test_driver_directory_lists_profiles_and_vehicles(client):
    _make_operator()
    operator = login_existing(client, "+919710000003")
    _make_driver(client, "+919710000004", "Ravi Driver", plate="TS09AB1234")
    # A driver without any profile row yet.
    register_user(client, "+919710000005", "Bare Driver", "driver")

    r = client.get("/api/v1/drivers", headers=operator["headers"])
    assert r.status_code == 200, r.text
    by_name = {d["full_name"]: d for d in r.json()}
    ravi = by_name["Ravi Driver"]
    assert ravi["is_available"] is True
    assert ravi["vehicle"]["plate"] == "TS09AB1234"
    assert ravi["vehicle"]["type"] == "tempo"
    assert ravi["vehicle"]["capacity_kg"] == 750
    bare = by_name["Bare Driver"]
    assert bare["is_available"] is False
    assert bare["vehicle"] is None

    # The directory is operator/admin only.
    buyer = register_user(client, "+919710000002", "Sita Rao", "buyer")
    r = client.get("/api/v1/drivers", headers=buyer["headers"])
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Assign / start / driver views
# ---------------------------------------------------------------------------


def _planned_shipment_with_driver(client, *, available_driver=True):
    commodity_id = seed_commodity()
    fpo_id = _make_operator()
    farmer = _make_farmer(client, "+919710000001", "Member Farmer", fpo_id=fpo_id)
    buyer = register_user(client, "+919710000002", "Sita Rao", "buyer")
    order, _ = _make_confirmed_order(
        client, farmer, buyer, commodity_id, idempotency_key=f"k-{uuid.uuid4().hex[:8]}"
    )
    operator = login_existing(client, "+919710000003")
    shipment = _plan_shipment(client, operator, [order["id"]])
    driver = _make_driver(
        client,
        "+919710000004" if available_driver else "+919710000005",
        "Ravi Driver" if available_driver else "Busy Driver",
        available=available_driver,
        plate="TS09AB1234" if available_driver else "TS09CD5678",
    )
    return operator, driver, buyer, shipment, order


def test_assign_start_and_mine_flow(client):
    operator, driver, buyer, shipment, order = _planned_shipment_with_driver(client)

    # Assigning an unavailable driver is rejected before the state flips.
    busy = register_user(client, "+919710000006", "Busy Driver", "driver")
    db = SessionLocal()
    try:
        busy_user = db.scalar(select(User).where(User.phone == "+919710000006"))
        db.add(DriverProfile(user_id=busy_user.id, is_available=False))
        db.commit()
        busy_id = str(busy_user.id)
    finally:
        db.close()
    r = client.post(
        f"/api/v1/shipments/{shipment['id']}/assign",
        headers=operator["headers"],
        json={"driver_id": busy_id},
    )
    assert r.status_code == 409, r.text

    r = client.post(
        f"/api/v1/shipments/{shipment['id']}/assign",
        headers=operator["headers"],
        json={"driver_id": _user_id_of(client, driver)},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "assigned"
    assert body["driver_id"] == _user_id_of(client, driver)

    # PLANNED → ASSIGNED is a one-shot move.
    r = client.post(
        f"/api/v1/shipments/{shipment['id']}/assign",
        headers=operator["headers"],
        json={"driver_id": _user_id_of(client, driver)},
    )
    assert r.status_code == 409

    # Driver sees the run in /mine with ordered stops and crate codes.
    r = client.get("/api/v1/shipments/mine", headers=driver["headers"])
    assert r.status_code == 200, r.text
    mine = r.json()
    assert any(s["id"] == shipment["id"] for s in mine)
    run = next(s for s in mine if s["id"] == shipment["id"])
    assert [s["sequence"] for s in run["stops"]] == [1, 2]
    assert run["crates"][0]["code"].startswith("KS-")
    assert "Sita Rao" not in r.text and "+919888777666" not in r.text

    # Start: only the assigned driver, only from ASSIGNED.
    other_driver = _make_driver(
        client, "+919710000007", "Other Driver", plate="TS09EF9999"
    )
    r = client.post(
        f"/api/v1/shipments/{shipment['id']}/start", headers=other_driver["headers"]
    )
    assert r.status_code == 403
    r = client.post(
        f"/api/v1/shipments/{shipment['id']}/start", headers=driver["headers"]
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "in_progress"
    assert r.json()["started_at"] is not None
    r = client.post(
        f"/api/v1/shipments/{shipment['id']}/start", headers=driver["headers"]
    )
    assert r.status_code == 409


def _user_id_of(client, auth):
    """Resolve the user id behind an auth dict (JWT `sub` claim)."""
    db = SessionLocal()
    try:
        payload = decode_token(auth["token"], ACCESS_TOKEN_TYPE)
        return str(db.get(User, uuid.UUID(payload["sub"])).id)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# QR-verified stop completion
# ---------------------------------------------------------------------------


def test_qr_stop_completion_drives_orders_to_completion(client):
    commodity_id = seed_commodity()
    fpo_id = _make_operator()
    farmer = _make_farmer(client, "+919710000001", "Member Farmer", fpo_id=fpo_id)
    buyer = register_user(client, "+919710000002", "Sita Rao", "buyer")
    order, listing = _make_confirmed_order(
        client, farmer, buyer, commodity_id, idempotency_key="k-qr"
    )
    operator = login_existing(client, "+919710000003")
    driver = _make_driver(client, "+919710000004", "Ravi Driver")
    shipment = _plan_shipment(client, operator, [order["id"]])
    token, code = _get_crate_token(order["id"])

    client.post(
        f"/api/v1/shipments/{shipment['id']}/assign",
        headers=operator["headers"],
        json={"driver_id": _user_id_of(client, driver)},
    )
    client.post(f"/api/v1/shipments/{shipment['id']}/start", headers=driver["headers"])

    pickup = next(s for s in shipment["stops"] if s["stop_type"] == "pickup")
    delivery = next(s for s in shipment["stops"] if s["stop_type"] == "delivery")

    # A wrong code while the stop is open: 400 + a failed verification event.
    r = client.post(
        f"/api/v1/shipments/stops/{pickup['id']}/complete",
        headers=driver["headers"],
        json={"method": "qr_scan", "code": "not-a-real-token"},
    )
    assert r.status_code == 400, r.text

    # The QR pickup scan succeeds and drives the order forward.
    r = client.post(
        f"/api/v1/shipments/stops/{pickup['id']}/complete",
        headers=driver["headers"],
        json={"method": "qr_scan", "code": token},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    pickup_after = next(s for s in body["stops"] if s["id"] == pickup["id"])
    assert pickup_after["status"] == "completed"
    assert pickup_after["arrived_at"] and pickup_after["completed_at"]
    assert body["crates"][0]["status"] == "scanned_pickup"
    # PICKED_UP auto-advances once all crates are scanned.
    assert body["orders"][0]["status"] == "out_for_delivery"

    # Replay protection: the same scan again is a 409 conflict.
    r = client.post(
        f"/api/v1/shipments/stops/{pickup['id']}/complete",
        headers=driver["headers"],
        json={"method": "qr_scan", "code": token},
    )
    assert r.status_code == 409

    # Manual-code delivery scan completes the whole run.
    r = client.post(
        f"/api/v1/shipments/stops/{delivery['id']}/complete",
        headers=driver["headers"],
        json={"method": "manual_code", "code": code},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "completed"
    assert body["completed_at"] is not None
    assert body["crates"][0]["status"] == "scanned_delivery"
    assert body["orders"][0]["status"] == "completed"

    # Buyer-visible order timeline: delivered → completed.
    r = client.get(f"/api/v1/orders/{order['id']}", headers=buyer["headers"])
    assert r.json()["status"] == "completed"
    assert r.json()["delivered_at"] is not None

    # Reservations consumed: stock leaves the listing for good.
    r = client.get(f"/api/v1/listings/{listing['id']}", headers=farmer["headers"])
    assert r.json()["quantity_total"] == 90
    assert r.json()["quantity_available"] == 90

    # Every attempt was logged: 2 successes + 2 failures (replay, wrong code).
    db = SessionLocal()
    try:
        events = db.scalars(select(QrVerificationEvent)).all()
    finally:
        db.close()
    successes = [e for e in events if e.success]
    failures = [e for e in events if not e.success]
    assert len(successes) == 2
    assert len(failures) == 2
    assert all(e.reason for e in failures)
    assert {e.purpose.value for e in successes} == {
        "pickup_verification",
        "delivery_verification",
    }
    assert all(e.method.value in ("qr_scan", "manual_code") for e in successes)


def test_stop_completion_requires_the_assigned_driver(client):
    operator, driver, buyer, shipment, order = _planned_shipment_with_driver(client)
    another = _make_driver(
        client, "+919710000007", "Second Driver", plate="TS09ZZ0001"
    )

    pickup = next(s for s in shipment["stops"] if s["stop_type"] == "pickup")
    token, _ = _get_crate_token(order["id"])

    # A different driver has no access to the stop at all.
    r = client.post(
        f"/api/v1/shipments/stops/{pickup['id']}/complete",
        headers=another["headers"],
        json={"method": "qr_scan", "code": token},
    )
    assert r.status_code == 403

    # The assigned driver must start the run first.
    client.post(
        f"/api/v1/shipments/{shipment['id']}/assign",
        headers=operator["headers"],
        json={"driver_id": _user_id_of(client, driver)},
    )
    r = client.post(
        f"/api/v1/shipments/stops/{pickup['id']}/complete",
        headers=driver["headers"],
        json={"method": "qr_scan", "code": token},
    )
    assert r.status_code == 409
    client.post(f"/api/v1/shipments/{shipment['id']}/start", headers=driver["headers"])
    r = client.post(
        f"/api/v1/shipments/stops/{pickup['id']}/complete",
        headers=driver["headers"],
        json={"method": "qr_scan", "code": token},
    )
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Failure paths
# ---------------------------------------------------------------------------


def test_fail_stop_marks_order_delivery_failed(client):
    commodity_id = seed_commodity()
    fpo_id = _make_operator()
    farmer = _make_farmer(client, "+919710000001", "Member Farmer", fpo_id=fpo_id)
    buyer = register_user(client, "+919710000002", "Sita Rao", "buyer")
    order, _ = _make_confirmed_order(
        client, farmer, buyer, commodity_id, idempotency_key="k-fail"
    )
    operator = login_existing(client, "+919710000003")
    driver = _make_driver(client, "+919710000004", "Ravi Driver")
    shipment = _plan_shipment(client, operator, [order["id"]])
    token, _ = _get_crate_token(order["id"])
    client.post(
        f"/api/v1/shipments/{shipment['id']}/assign",
        headers=operator["headers"],
        json={"driver_id": _user_id_of(client, driver)},
    )
    client.post(f"/api/v1/shipments/{shipment['id']}/start", headers=driver["headers"])

    pickup = next(s for s in shipment["stops"] if s["stop_type"] == "pickup")
    delivery = next(s for s in shipment["stops"] if s["stop_type"] == "delivery")
    client.post(
        f"/api/v1/shipments/stops/{pickup['id']}/complete",
        headers=driver["headers"],
        json={"method": "qr_scan", "code": token},
    )

    r = client.post(
        f"/api/v1/shipments/stops/{delivery['id']}/fail",
        headers=driver["headers"],
        json={"reason": "Buyer unreachable at drop point"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    delivery_after = next(s for s in body["stops"] if s["id"] == delivery["id"])
    assert delivery_after["status"] == "failed"
    assert delivery_after["failure_reason"] == "Buyer unreachable at drop point"
    assert body["orders"][0]["status"] == "delivery_failed"
    # The completed pickup stop keeps the shipment itself in progress.
    assert body["status"] == "in_progress"

    r = client.get(f"/api/v1/orders/{order['id']}", headers=buyer["headers"])
    assert r.json()["status"] == "delivery_failed"


def test_shipment_fails_only_when_every_stop_failed(client):
    commodity_id = seed_commodity()
    fpo_id = _make_operator()
    farmer = _make_farmer(client, "+919710000001", "Member Farmer", fpo_id=fpo_id)
    buyer = register_user(client, "+919710000002", "Sita Rao", "buyer")
    order, _ = _make_confirmed_order(
        client, farmer, buyer, commodity_id, idempotency_key="k-allfail"
    )
    operator = login_existing(client, "+919710000003")
    driver = _make_driver(client, "+919710000004", "Ravi Driver")
    shipment = _plan_shipment(client, operator, [order["id"]])
    client.post(
        f"/api/v1/shipments/{shipment['id']}/assign",
        headers=operator["headers"],
        json={"driver_id": _user_id_of(client, driver)},
    )
    client.post(f"/api/v1/shipments/{shipment['id']}/start", headers=driver["headers"])

    pickup = next(s for s in shipment["stops"] if s["stop_type"] == "pickup")
    delivery = next(s for s in shipment["stops"] if s["stop_type"] == "delivery")

    r = client.post(
        f"/api/v1/shipments/stops/{pickup['id']}/fail",
        headers=driver["headers"],
        json={"reason": "Farmer produce not ready"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"  # delivery stop still open

    r = client.post(
        f"/api/v1/shipments/stops/{delivery['id']}/fail",
        headers=driver["headers"],
        json={"reason": "Nothing to deliver after failed pickup"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "failed"


# ---------------------------------------------------------------------------
# Visibility rules
# ---------------------------------------------------------------------------


def test_shipment_visibility_and_buyer_narrowed_view(client):
    operator, driver, buyer, shipment, order = _planned_shipment_with_driver(client)
    client.post(
        f"/api/v1/shipments/{shipment['id']}/assign",
        headers=operator["headers"],
        json={"driver_id": _user_id_of(client, driver)},
    )

    # The buyer with an order in the run sees a narrowed view: their own
    # order only, no manifest content, no other buyer's delivery stops.
    r = client.get(f"/api/v1/shipments/{shipment['id']}", headers=buyer["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert [o["id"] for o in body["orders"]] == [order["id"]]
    assert all(s["order_id"] == order["id"] for s in body["stops"])
    assert "content" not in body["manifest"]
    assert "Sita Rao" not in r.text and "+919888777666" not in r.text

    # The assigned driver sees the staff view.
    r = client.get(f"/api/v1/shipments/{shipment['id']}", headers=driver["headers"])
    assert r.status_code == 200
    assert len(r.json()["orders"]) == 1
    assert "content" in r.json()["manifest"]

    # The planning operator sees it too.
    r = client.get(f"/api/v1/shipments/{shipment['id']}", headers=operator["headers"])
    assert r.status_code == 200

    # An unrelated buyer has no access.
    intruder = register_user(client, "+919710000008", "Intruder", "buyer")
    r = client.get(f"/api/v1/shipments/{shipment['id']}", headers=intruder["headers"])
    assert r.status_code == 403

    # Unknown ids 404 cleanly.
    r = client.get(
        f"/api/v1/shipments/{uuid.uuid4()}", headers=operator["headers"]
    )
    assert r.status_code == 404
