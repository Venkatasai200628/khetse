"""Shared-logistics lifecycle: consolidation, routing, driver hand-off and
QR-verified stop completion.

Invariants:
- Every order status change goes through order_state.apply_transition — an
  illegal move raises and the whole request rolls back.
- Driver-visible structures carry privacy-safe labels only: buyer names,
  phones and addresses never enter stops, manifests or shipment payloads.
- A crate's qr_token is a secret used to verify scans; it is never returned
  by any API response.
- Stop completion, crate status, order transitions and shipment completion
  happen in ONE transaction; every verification attempt (including failures
  and replays) is logged to QrVerificationEvent.
"""

import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.routing.route_optimizer import RouteStop, solve_route
from app.core.errors import (
    AppError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from app.models.catalog import ProduceListing
from app.models.commerce import Order
from app.models.enums import (
    CrateStatus,
    OrderStatus,
    QrMethod,
    QrPurpose,
    RoleEnum,
    ShipmentStatus,
    StopStatus,
    StopType,
)
from app.models.logistics import (
    CrateLabel,
    DeliveryManifest,
    QrVerificationEvent,
    Shipment,
    ShipmentStop,
)
from app.models.profiles import (
    CollectionCentre,
    DriverProfile,
    FarmerProfile,
    Vehicle,
)
from app.models.user import User, UserRole
from app.services import order_state
from app.services.order_service import consume_reservations


def _member_farmer_ids(db: Session, user: User) -> set[uuid.UUID]:
    """Farmer ids belonging to the FPO the operator account is tied to."""
    if not (user.has_role(RoleEnum.FPO_OPERATOR) and user.fpo_id is not None):
        return set()
    return set(
        db.scalars(
            select(FarmerProfile.user_id).where(FarmerProfile.fpo_id == user.fpo_id)
        )
    )


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------


def create_shipment_from_orders(
    db: Session,
    operator: User,
    *,
    order_ids: list[uuid.UUID],
    collection_centre_id: uuid.UUID | None = None,
    driver_id: uuid.UUID | None = None,
    vehicle_id: uuid.UUID | None = None,
) -> Shipment:
    """Consolidate confirmed orders into one routed shipment run.

    One pickup stop per distinct farmer + one delivery stop per order, a
    nearest-neighbour route, one crate label per order and a delivery
    manifest. Orders move CONFIRMED → PICKUP_SCHEDULED; with a driver given
    the shipment is born ASSIGNED.
    """
    unique_ids = list(dict.fromkeys(order_ids))  # de-dupe, keep client order
    if not unique_ids:
        raise ValidationAppError("Provide at least one order id.")

    centre: CollectionCentre | None = None
    if collection_centre_id is not None:
        centre = db.get(CollectionCentre, collection_centre_id)
        if centre is None:
            raise NotFoundError("Collection centre not found.")
    if vehicle_id is not None and db.get(Vehicle, vehicle_id) is None:
        raise NotFoundError("Vehicle not found.")

    is_admin = operator.has_role(RoleEnum.ADMIN)
    member_ids = set() if is_admin else _member_farmer_ids(db, operator)

    orders: list[Order] = []
    for oid in unique_ids:
        order = db.get(Order, oid)
        if order is None:
            raise NotFoundError("Order not found.", details={"order_id": str(oid)})
        if order.status != OrderStatus.CONFIRMED:
            raise ConflictError(
                "Shipments can only be planned for confirmed orders.",
                details={"order_id": str(oid), "status": order.status.value},
            )
        farmer_ids = {item.farmer_id for item in order.items}
        if not is_admin and not farmer_ids <= member_ids:
            raise AuthorizationError(
                "This order includes produce from farmers outside your FPO.",
                details={"order_id": str(oid)},
            )
        orders.append(order)

    # ---- Pickup points: one stop per distinct farmer ---------------------
    points: dict[uuid.UUID, dict] = {}
    for order in orders:
        for item in order.items:
            entry = points.setdefault(item.farmer_id, {"lat": None, "lng": None})
            listing = db.get(ProduceListing, item.listing_id)
            if entry["lat"] is None and listing is not None:
                entry["lat"] = listing.farm_lat
                entry["lng"] = listing.farm_lng

    shipment = Shipment(
        collection_centre_id=collection_centre_id,
        status=ShipmentStatus.PLANNED,
    )
    db.add(shipment)
    db.flush()  # ids for stops / crates / manifest

    stops: list[ShipmentStop] = []
    for farmer_id, coords in points.items():
        profile = db.scalar(
            select(FarmerProfile).where(FarmerProfile.user_id == farmer_id)
        )
        lat, lng = coords["lat"], coords["lng"]
        if lat is None and profile is not None:
            lat, lng = profile.farm_lat, profile.farm_lng
        label = (
            f"{profile.village}, {profile.district}"
            if profile is not None
            else "Farm pickup"
        )
        stops.append(
            ShipmentStop(
                id=uuid.uuid4(),
                shipment_id=shipment.id,
                stop_type=StopType.PICKUP,
                lat=lat,
                lng=lng,
                label=label,
            )
        )

    # ---- Delivery stops: one per order, privacy-safe labels --------------
    for order in orders:
        district = order.delivery_district or "Unknown"
        stops.append(
            ShipmentStop(
                id=uuid.uuid4(),
                shipment_id=shipment.id,
                stop_type=StopType.DELIVERY,
                order_id=order.id,
                lat=order.delivery_lat,
                lng=order.delivery_lng,
                # Never the buyer's name or phone — drivers see districts only.
                label=f"Buyer · {district}",
            )
        )
    for stop in stops:
        db.add(stop)

    # ---- Route: nearest-neighbour from the collection centre -------------
    # Stop ids are generated client-side, so the solver can reference them
    # before any INSERT happens.
    start_point = None
    if centre is not None and centre.lat is not None and centre.lng is not None:
        start_point = (centre.lat, centre.lng)
    solved = solve_route(
        [RouteStop(s.id, s.lat, s.lng) for s in stops], start_point
    )
    sequence_by_stop = {sid: i + 1 for i, sid in enumerate(solved.order)}
    for stop in stops:
        stop.sequence = sequence_by_stop[stop.id]
    shipment.solver = solved.solver
    # Stops without coordinates (e.g. buyer drop-offs from a form that did not
    # collect GPS) make the solver return 0 — store NULL so the UI shows an
    # honest "unknown" instead of a fake 0 km.
    shipment.route_distance_km = solved.total_distance_km or None
    shipment.route_data = {
        "stop_order": [str(sid) for sid in solved.order],
        "total_distance_km": solved.total_distance_km,
    }

    # ---- One crate label per order ---------------------------------------
    crates: list[CrateLabel] = []
    for order in orders:
        item = order.items[0]
        crate = CrateLabel(
            shipment_id=shipment.id,
            order_id=order.id,
            listing_id=item.listing_id,
            commodity_id=item.commodity_id,
            quantity=item.quantity,
            unit=item.unit.value if item.unit is not None else None,
            grade=item.quality_grade.value if item.quality_grade is not None else None,
            code=f"KS-{secrets.token_hex(5)}",
            qr_token=secrets.token_urlsafe(32),
            status=CrateStatus.CREATED,
        )
        crates.append(crate)
        db.add(crate)

    now = datetime.now(timezone.utc)
    db.add(
        DeliveryManifest(
            shipment_id=shipment.id,
            manifest_number=f"MAN-{now:%Y%m%d}-{secrets.token_hex(3)}",
            content={
                "stops": [
                    {
                        "id": str(s.id),
                        "type": s.stop_type.value,
                        "sequence": s.sequence,
                        "label": s.label,
                    }
                    for s in sorted(stops, key=lambda s: s.sequence)
                ],
                "orders": [str(o.id) for o in orders],
                "crates": [
                    {"code": c.code, "order_id": str(c.order_id)} for c in crates
                ],
            },
            generated_at=now,
        )
    )

    for order in orders:
        order_state.apply_transition(
            db, order, OrderStatus.PICKUP_SCHEDULED, user=operator,
            reason="Pickup scheduled by shipment plan",
        )

    if driver_id is not None:
        _attach_driver(db, shipment, driver_id, vehicle_id)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(shipment)
    return shipment


def _attach_driver(
    db: Session,
    shipment: Shipment,
    driver_id: uuid.UUID,
    vehicle_id: uuid.UUID | None,
) -> None:
    """Validate the driver role and availability, then assign."""
    driver = db.get(User, driver_id)
    if driver is None:
        raise NotFoundError("Driver not found.")
    if not driver.has_role(RoleEnum.DRIVER):
        raise ValidationAppError("The selected user does not have the driver role.")
    profile = db.scalar(
        select(DriverProfile).where(DriverProfile.user_id == driver_id)
    )
    if profile is None or not profile.is_available:
        raise ConflictError("Driver is not available.")
    shipment.driver_id = driver_id
    if vehicle_id is not None:
        shipment.vehicle_id = vehicle_id
    shipment.status = ShipmentStatus.ASSIGNED


# ---------------------------------------------------------------------------
# Driver directory / driver views
# ---------------------------------------------------------------------------


def list_drivers(db: Session) -> list[dict]:
    """Directory for operators/admins: drivers with availability + vehicle."""
    drivers = db.scalars(
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .where(UserRole.role == RoleEnum.DRIVER)
        .order_by(User.created_at)
    ).all()
    result: list[dict] = []
    for driver in drivers:
        profile = db.scalar(
            select(DriverProfile).where(DriverProfile.user_id == driver.id)
        )
        vehicle = db.scalar(
            select(Vehicle)
            .where(Vehicle.driver_id == driver.id)
            .order_by(Vehicle.created_at)
        )
        result.append(
            {
                "user_id": driver.id,
                "full_name": driver.full_name,
                "is_available": bool(profile.is_available) if profile else False,
                "vehicle": (
                    {
                        "plate": vehicle.plate_number,
                        "type": vehicle.vehicle_type.value,
                        "capacity_kg": vehicle.capacity_kg,
                    }
                    if vehicle is not None
                    else None
                ),
            }
        )
    return result


def list_driver_shipments(db: Session, driver: User) -> list[Shipment]:
    """Shipments assigned to a driver, newest first."""
    return list(
        db.scalars(
            select(Shipment)
            .where(Shipment.driver_id == driver.id)
            .order_by(Shipment.created_at.desc())
        )
    )


def get_shipment_for_view(
    db: Session, shipment_id: uuid.UUID, user: User
) -> tuple[Shipment, str]:
    """Load a shipment the user may see; returns (shipment, viewer kind).

    viewer is "staff" (assigned driver, involved FPO operator, admin) or
    "buyer" (a buyer/business user with an order in the run — they only get
    their own order's summary).
    """
    shipment = db.get(Shipment, shipment_id)
    if shipment is None:
        raise NotFoundError("Shipment not found.")
    if user.has_role(RoleEnum.ADMIN):
        return shipment, "staff"
    if shipment.driver_id == user.id:
        return shipment, "staff"

    order_ids = {s.order_id for s in shipment.stops if s.order_id is not None}
    order_ids |= {c.order_id for c in shipment.crates if c.order_id is not None}
    orders = (
        list(db.scalars(select(Order).where(Order.id.in_(order_ids))))
        if order_ids
        else []
    )

    if user.has_role(RoleEnum.FPO_OPERATOR) and user.fpo_id is not None:
        member_ids = _member_farmer_ids(db, user)
        if any(
            item.farmer_id in member_ids for order in orders for item in order.items
        ):
            return shipment, "staff"

    if any(order.buyer_id == user.id for order in orders):
        return shipment, "buyer"

    raise AuthorizationError("You do not have access to this shipment.")


# ---------------------------------------------------------------------------
# Driver actions
# ---------------------------------------------------------------------------


def assign_driver(
    db: Session,
    actor: User,
    shipment_id: uuid.UUID,
    *,
    driver_id: uuid.UUID,
    vehicle_id: uuid.UUID | None = None,
) -> Shipment:
    """PLANNED → ASSIGNED hand-off to an available driver."""
    shipment = db.get(Shipment, shipment_id)
    if shipment is None:
        raise NotFoundError("Shipment not found.")
    if shipment.status != ShipmentStatus.PLANNED:
        raise ConflictError(
            "Only a planned shipment can be assigned a driver.",
            details={"status": shipment.status.value},
        )
    _attach_driver(db, shipment, driver_id, vehicle_id)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(shipment)
    return shipment


def start_shipment(db: Session, driver: User, shipment_id: uuid.UUID) -> Shipment:
    """ASSIGNED → IN_PROGRESS; stamps started_at."""
    shipment = db.get(Shipment, shipment_id)
    if shipment is None:
        raise NotFoundError("Shipment not found.")
    if shipment.driver_id != driver.id:
        raise AuthorizationError("Only the assigned driver can start this shipment.")
    if shipment.status != ShipmentStatus.ASSIGNED:
        raise ConflictError(
            "Only an assigned shipment can be started.",
            details={"status": shipment.status.value},
        )
    shipment.status = ShipmentStatus.IN_PROGRESS
    shipment.started_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(shipment)
    return shipment


def _log_verification(
    db: Session,
    *,
    code: str,
    purpose: QrPurpose,
    method: QrMethod,
    shipment_id: uuid.UUID | None,
    stop_id: uuid.UUID | None,
    order_id: uuid.UUID | None,
    actor: User | None,
    success: bool,
    reason: str | None,
) -> None:
    db.add(
        QrVerificationEvent(
            qr_code=code[:64],
            purpose=purpose,
            method=method,
            shipment_id=shipment_id,
            stop_id=stop_id,
            order_id=order_id,
            actor_user_id=actor.id if actor is not None else None,
            success=success,
            reason=reason,
        )
    )


def _all_crates_scanned(db: Session, order: Order) -> bool:
    crates = db.scalars(
        select(CrateLabel).where(CrateLabel.order_id == order.id)
    ).all()
    return bool(crates) and all(
        c.status != CrateStatus.CREATED for c in crates
    )


def complete_stop(
    db: Session,
    driver: User,
    stop_id: uuid.UUID,
    *,
    method: QrMethod,
    code: str,
) -> Shipment:
    """Verify a crate at a stop and advance stop, crate, order and shipment.

    - qr_scan matches the crate's secret qr_token; manual_code its public
      "KS-…" code. Either way the crate must belong to THIS shipment.
    - Pickup scan: crate → scanned_pickup, order PICKUP_SCHEDULED →
      PICKED_UP; when all of the order's crates are scanned it auto-advances
      to OUT_FOR_DELIVERY.
    - Delivery scan: crate → scanned_delivered, order OUT_FOR_DELIVERY →
      DELIVERED. Once every delivery stop is complete the shipment completes
      and each delivered order closes (DELIVERED → COMPLETED, reservations
      consumed).
    - Wrong codes log a failed verification event and answer 400; crates
      already scanned at that stage answer 409 (replay protection).
    """
    stop = db.get(ShipmentStop, stop_id)
    if stop is None:
        raise NotFoundError("Stop not found.")
    shipment = db.get(Shipment, stop.shipment_id)
    if shipment.driver_id != driver.id:
        raise AuthorizationError("Only the assigned driver can complete stops.")
    if shipment.status != ShipmentStatus.IN_PROGRESS:
        raise ConflictError(
            "Start the shipment before completing stops.",
            details={"status": shipment.status.value},
        )
    is_pickup = stop.stop_type == StopType.PICKUP
    purpose = QrPurpose.PICKUP_VERIFICATION if is_pickup else QrPurpose.DELIVERY_VERIFICATION

    if stop.status in (StopStatus.COMPLETED, StopStatus.FAILED):
        _log_verification(
            db,
            code=code,
            purpose=purpose,
            method=method,
            shipment_id=shipment.id,
            stop_id=stop.id,
            order_id=None,
            actor=driver,
            success=False,
            reason="Stop already closed",
        )
        db.commit()
        raise ConflictError("This stop has already been closed.")

    match_column = CrateLabel.qr_token if method == QrMethod.QR_SCAN else CrateLabel.code
    crate = db.scalar(
        select(CrateLabel).where(
            CrateLabel.shipment_id == shipment.id,
            match_column == code,
        )
    )
    if crate is None:
        _log_verification(
            db,
            code=code,
            purpose=purpose,
            method=method,
            shipment_id=shipment.id,
            stop_id=stop.id,
            order_id=None,
            actor=driver,
            success=False,
            reason="Code does not match any crate in this shipment",
        )
        db.commit()
        raise AppError("The scanned code does not match any crate in this shipment.")

    if is_pickup and crate.status != CrateStatus.CREATED:
        _log_verification(
            db,
            code=code,
            purpose=purpose,
            method=method,
            shipment_id=shipment.id,
            stop_id=stop.id,
            order_id=crate.order_id,
            actor=driver,
            success=False,
            reason="Crate already scanned at pickup",
        )
        db.commit()
        raise ConflictError("This crate has already been scanned at pickup.")
    if not is_pickup and crate.status == CrateStatus.SCANNED_DELIVERY:
        _log_verification(
            db,
            code=code,
            purpose=purpose,
            method=method,
            shipment_id=shipment.id,
            stop_id=stop.id,
            order_id=crate.order_id,
            actor=driver,
            success=False,
            reason="Crate already scanned at delivery",
        )
        db.commit()
        raise ConflictError("This crate has already been scanned at delivery.")
    if not is_pickup and crate.status == CrateStatus.CREATED:
        _log_verification(
            db,
            code=code,
            purpose=purpose,
            method=method,
            shipment_id=shipment.id,
            stop_id=stop.id,
            order_id=crate.order_id,
            actor=driver,
            success=False,
            reason="Crate has not been picked up yet",
        )
        db.commit()
        raise ConflictError("This crate has not been picked up yet.")

    now = datetime.now(timezone.utc)
    order = db.get(Order, crate.order_id) if crate.order_id is not None else None

    stop.arrived_at = stop.arrived_at or now
    stop.completed_at = now
    stop.status = StopStatus.COMPLETED
    if is_pickup:
        crate.status = CrateStatus.SCANNED_PICKUP
        crate.picked_up_at = now
    else:
        crate.status = CrateStatus.SCANNED_DELIVERY
        crate.delivered_at = now
    _log_verification(
        db,
        code=code,
        purpose=purpose,
        method=method,
        shipment_id=shipment.id,
        stop_id=stop.id,
        order_id=crate.order_id,
        actor=driver,
        success=True,
        reason=None,
    )

    if order is not None:
        if is_pickup:
            if order.status == OrderStatus.PICKUP_SCHEDULED:
                order_state.apply_transition(
                    db, order, OrderStatus.PICKED_UP, user=driver,
                    reason="Crate scanned at pickup",
                )
            # Auto-advance once every crate of the order is scanned. The
            # state machine reserves PICKED_UP → OUT_FOR_DELIVERY for the
            # driver role, so the transition rides on the scanning driver.
            if order.status == OrderStatus.PICKED_UP and _all_crates_scanned(db, order):
                order_state.apply_transition(
                    db, order, OrderStatus.OUT_FOR_DELIVERY, user=driver,
                    reason="picked up, en route",
                )
        elif order.status == OrderStatus.OUT_FOR_DELIVERY:
            order_state.apply_transition(
                db, order, OrderStatus.DELIVERED, user=driver,
                reason="Crate scanned at delivery",
            )
            order.delivered_at = now

    delivery_stops = [s for s in shipment.stops if s.stop_type == StopType.DELIVERY]
    if delivery_stops and all(s.status == StopStatus.COMPLETED for s in delivery_stops):
        shipment.status = ShipmentStatus.COMPLETED
        shipment.completed_at = now
        for delivery in delivery_stops:
            if delivery.order_id is None:
                continue
            delivered = db.get(Order, delivery.order_id)
            if delivered is not None and delivered.status == OrderStatus.DELIVERED:
                order_state.apply_transition(
                    db, delivered, OrderStatus.COMPLETED,
                    role_override="system",
                    reason="All delivery stops completed",
                )
                consume_reservations(db, delivered)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(shipment)
    return shipment


def fail_stop(
    db: Session, driver: User, stop_id: uuid.UUID, *, reason: str
) -> Shipment:
    """Mark a stop FAILED; its delivery order becomes DELIVERY_FAILED.

    The shipment itself flips to FAILED only when every one of its stops
    failed. Orders that never reached OUT_FOR_DELIVERY (a failed pickup
    leaves them PICKUP_SCHEDULED) have no legal path to DELIVERY_FAILED and
    are left untouched for operator follow-up.
    """
    stop = db.get(ShipmentStop, stop_id)
    if stop is None:
        raise NotFoundError("Stop not found.")
    shipment = db.get(Shipment, stop.shipment_id)
    if shipment.driver_id != driver.id:
        raise AuthorizationError("Only the assigned driver can fail stops.")
    if shipment.status != ShipmentStatus.IN_PROGRESS:
        raise ConflictError(
            "Start the shipment before marking stops failed.",
            details={"status": shipment.status.value},
        )
    if stop.status in (StopStatus.COMPLETED, StopStatus.FAILED):
        raise ConflictError("This stop has already been closed.")

    now = datetime.now(timezone.utc)
    stop.status = StopStatus.FAILED
    stop.failure_reason = reason
    stop.completed_at = now

    if stop.order_id is not None:
        order = db.get(Order, stop.order_id)
        if order is not None and order.status == OrderStatus.OUT_FOR_DELIVERY:
            order_state.apply_transition(
                db, order, OrderStatus.DELIVERY_FAILED, user=driver, reason=reason
            )

    if shipment.stops and all(s.status == StopStatus.FAILED for s in shipment.stops):
        shipment.status = ShipmentStatus.FAILED

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(shipment)
    return shipment
