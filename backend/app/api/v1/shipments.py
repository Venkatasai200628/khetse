"""Shipment + shared-logistics endpoints, including the driver directory.

Route registration: `router` at the bottom of this module aggregates every
endpoint here — shipment routes live under /shipments (via
`shipment_routes`), the driver directory under /drivers (via
`driver_routes`, which sits outside the /shipments prefix). app.api.v1
includes `router` once.
"""

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.commerce import Order
from app.models.enums import QrMethod, RoleEnum
from app.models.logistics import DeliveryManifest, Shipment
from app.models.user import User
from app.services import shipment_service

shipment_routes = APIRouter(prefix="/shipments", tags=["shipments"])
driver_routes = APIRouter(prefix="/drivers", tags=["drivers"])


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class CreateShipmentRequest(BaseModel):
    order_ids: list[uuid.UUID] = Field(min_length=1)
    collection_centre_id: uuid.UUID | None = None
    driver_id: uuid.UUID | None = None
    vehicle_id: uuid.UUID | None = None


class AssignDriverRequest(BaseModel):
    driver_id: uuid.UUID
    vehicle_id: uuid.UUID | None = None


class CompleteStopRequest(BaseModel):
    method: Literal["qr_scan", "manual_code"]
    code: str = Field(max_length=200)


class FailStopRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


# ---------------------------------------------------------------------------
# Serialisation — privacy-safe by construction
# ---------------------------------------------------------------------------


def _dt(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _stop_payload(stop) -> dict:
    return {
        "id": stop.id,
        "stop_type": stop.stop_type.value,
        "sequence": stop.sequence,
        "status": stop.status.value,
        "label": stop.label,
        "lat": stop.lat,
        "lng": stop.lng,
        "order_id": stop.order_id,
        "arrived_at": _dt(stop.arrived_at),
        "completed_at": _dt(stop.completed_at),
        "failure_reason": stop.failure_reason,
    }


def _crate_payload(crate) -> dict:
    # The secret qr_token is deliberately absent — it verifies scans and is
    # never returned by any endpoint.
    return {
        "id": crate.id,
        "code": crate.code,
        "status": crate.status.value,
        "order_id": crate.order_id,
        "quantity": crate.quantity,
        "unit": crate.unit,
        "grade": crate.grade,
    }


def _order_summary(order: Order) -> dict:
    """Privacy-safe order summary: no buyer name, phone or street address."""
    return {
        "id": order.id,
        "status": order.status.value,
        "delivery_district": order.delivery_district,
        "total_paise": order.total_paise,
        "currency": order.currency,
        "delivered_at": _dt(order.delivered_at),
        "items": [
            {
                "quantity": item.quantity,
                "unit": item.unit.value if item.unit is not None else None,
                "quality_grade": (
                    item.quality_grade.value
                    if item.quality_grade is not None
                    else None
                ),
            }
            for item in order.items
        ],
    }


def _shipment_orders(db: Session, shipment: Shipment) -> list[Order]:
    order_ids = {s.order_id for s in shipment.stops if s.order_id is not None}
    order_ids |= {c.order_id for c in shipment.crates if c.order_id is not None}
    if not order_ids:
        return []
    return list(db.scalars(select(Order).where(Order.id.in_(order_ids))))


def _manifest_payload(manifest: DeliveryManifest | None, include_content: bool) -> dict | None:
    if manifest is None:
        return None
    payload = {
        "id": manifest.id,
        "manifest_number": manifest.manifest_number,
        "generated_at": _dt(manifest.generated_at),
    }
    if include_content:
        # Content carries only stop labels, order ids and crate codes —
        # already privacy-safe. Buyers still don't need other orders' slice.
        payload["content"] = manifest.content
    return payload


def _shipment_payload(
    db: Session,
    shipment: Shipment,
    viewer: str,
    user: User,
    manifest: DeliveryManifest | None = None,
) -> dict:
    """Build the shipment response; buyers get a narrowed view."""
    is_buyer = viewer == "buyer"
    buyer_order_ids: set[uuid.UUID] = set()
    orders = _shipment_orders(db, shipment)
    if is_buyer:
        buyer_order_ids = {o.id for o in orders if o.buyer_id == user.id}
        # Buyers see their own order's slice only — their delivery stop,
        # their crates and their order summaries.
        orders = [o for o in orders if o.buyer_id == user.id]

    stops = sorted(shipment.stops, key=lambda s: s.sequence)
    if is_buyer:
        stops = [s for s in stops if s.order_id in buyer_order_ids]
    crates = shipment.crates
    if is_buyer:
        crates = [c for c in crates if c.order_id in buyer_order_ids]

    return {
        "id": shipment.id,
        "status": shipment.status.value,
        "driver_id": shipment.driver_id,
        "vehicle_id": shipment.vehicle_id,
        "collection_centre_id": shipment.collection_centre_id,
        "route_distance_km": shipment.route_distance_km,
        "route_duration_min": shipment.route_duration_min,
        "route_data": shipment.route_data,
        "solver": shipment.solver,
        "planned_start_at": _dt(shipment.planned_start_at),
        "started_at": _dt(shipment.started_at),
        "completed_at": _dt(shipment.completed_at),
        "created_at": _dt(shipment.created_at),
        "stops": [_stop_payload(s) for s in stops],
        "crates": [_crate_payload(c) for c in crates],
        "orders": [_order_summary(o) for o in orders],
        "manifest": _manifest_payload(manifest, include_content=not is_buyer),
    }


def _shipment_manifest(db: Session, shipment: Shipment) -> DeliveryManifest | None:
    return db.scalar(
        select(DeliveryManifest).where(DeliveryManifest.shipment_id == shipment.id)
    )


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------


@shipment_routes.post("", status_code=201)
def create_shipment(
    body: CreateShipmentRequest,
    db: Session = Depends(get_db),
    operator: User = Depends(require_roles(RoleEnum.FPO_OPERATOR, RoleEnum.ADMIN)),
):
    """Consolidate confirmed orders into one routed, crated shipment run."""
    shipment = shipment_service.create_shipment_from_orders(
        db,
        operator,
        order_ids=body.order_ids,
        collection_centre_id=body.collection_centre_id,
        driver_id=body.driver_id,
        vehicle_id=body.vehicle_id,
    )
    return _shipment_payload(
        db, shipment, "staff", operator,
        manifest=_shipment_manifest(db, shipment),
    )


@shipment_routes.get("/mine")
def my_shipments(
    db: Session = Depends(get_db),
    driver: User = Depends(require_roles(RoleEnum.DRIVER)),
):
    """Shipments assigned to the driver, newest first (privacy-safe labels)."""
    shipments = shipment_service.list_driver_shipments(db, driver)
    return [
        _shipment_payload(
            db, s, "staff", driver, manifest=_shipment_manifest(db, s)
        )
        for s in shipments
    ]


@shipment_routes.post("/stops/{stop_id}/complete")
def complete_stop(
    stop_id: uuid.UUID,
    body: CompleteStopRequest,
    db: Session = Depends(get_db),
    driver: User = Depends(require_roles(RoleEnum.DRIVER)),
):
    """QR/manual verification at a stop: completes the stop, scans the crate
    and drives the order state machine forward."""
    shipment = shipment_service.complete_stop(
        db,
        driver,
        stop_id,
        method=QrMethod(body.method),
        code=body.code.strip(),
    )
    return _shipment_payload(
        db, shipment, "staff", driver, manifest=_shipment_manifest(db, shipment)
    )


@shipment_routes.post("/stops/{stop_id}/fail")
def fail_stop(
    stop_id: uuid.UUID,
    body: FailStopRequest,
    db: Session = Depends(get_db),
    driver: User = Depends(require_roles(RoleEnum.DRIVER)),
):
    """Mark a stop failed with a reason; delivery orders become DELIVERY_FAILED."""
    shipment = shipment_service.fail_stop(db, driver, stop_id, reason=body.reason)
    return _shipment_payload(
        db, shipment, "staff", driver, manifest=_shipment_manifest(db, shipment)
    )


@shipment_routes.get("/{shipment_id}")
def get_shipment(
    shipment_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            RoleEnum.BUYER,
            RoleEnum.BUSINESS,
            RoleEnum.DRIVER,
            RoleEnum.FPO_OPERATOR,
            RoleEnum.ADMIN,
        )
    ),
):
    """Shipment detail for its driver, involved FPO operator, admin — or a
    buyer with an order in the run (buyer sees only their own order)."""
    shipment, viewer = shipment_service.get_shipment_for_view(db, shipment_id, user)
    return _shipment_payload(
        db, shipment, viewer, user, manifest=_shipment_manifest(db, shipment)
    )


@shipment_routes.post("/{shipment_id}/assign")
def assign_driver(
    shipment_id: uuid.UUID,
    body: AssignDriverRequest,
    db: Session = Depends(get_db),
    operator: User = Depends(require_roles(RoleEnum.FPO_OPERATOR, RoleEnum.ADMIN)),
):
    shipment = shipment_service.assign_driver(
        db,
        operator,
        shipment_id,
        driver_id=body.driver_id,
        vehicle_id=body.vehicle_id,
    )
    return _shipment_payload(
        db, shipment, "staff", operator, manifest=_shipment_manifest(db, shipment)
    )


@shipment_routes.post("/{shipment_id}/start")
def start_shipment(
    shipment_id: uuid.UUID,
    db: Session = Depends(get_db),
    driver: User = Depends(require_roles(RoleEnum.DRIVER)),
):
    shipment = shipment_service.start_shipment(db, driver, shipment_id)
    return _shipment_payload(
        db, shipment, "staff", driver, manifest=_shipment_manifest(db, shipment)
    )


@driver_routes.get("")
def list_drivers(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(RoleEnum.FPO_OPERATOR, RoleEnum.ADMIN)),
):
    """Driver directory with availability and vehicle summary."""
    return shipment_service.list_drivers(db)


# Single registration point for app.api.v1: /shipments/* plus /drivers.
router = APIRouter()
router.include_router(shipment_routes)
router.include_router(driver_routes)
