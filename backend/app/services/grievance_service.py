"""Grievance intake: creation with the admin SLA clock, listing.

The acknowledgement deadline comes from the runtime platform setting
``grievance_ack_hours`` (settings_service) so support can tune the SLA
without a deploy.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AuthorizationError, NotFoundError
from app.models.commerce import Order
from app.models.enums import GrievanceCategory, GrievanceStatus, RoleEnum
from app.models.logistics import Shipment
from app.models.ops import Grievance
from app.models.user import User
from app.services import order_service, settings_service


def _ack_deadline(db: Session) -> datetime:
    hours = settings_service.get_setting(db, "grievance_ack_hours")
    try:
        hours = float(hours)
    except (TypeError, ValueError):
        hours = 24.0
    return datetime.now(timezone.utc) + timedelta(hours=max(0.0, hours))


def create_grievance(
    db: Session,
    raiser: User,
    *,
    category: GrievanceCategory,
    subject: str,
    description: str,
    order_id: uuid.UUID | None = None,
    shipment_id: uuid.UUID | None = None,
) -> Grievance:
    """Open a grievance and start the acknowledgement SLA clock."""
    if order_id is not None:
        order = db.get(Order, order_id)
        if order is None:
            raise NotFoundError("Order not found.")
        # Only people actually involved in the order can grievance it —
        # this also stops probing for other users' order ids.
        if not order_service.is_order_participant(db, order, raiser) and not raiser.has_role(
            RoleEnum.ADMIN
        ):
            raise AuthorizationError("You are not a participant in this order.")
    if shipment_id is not None and db.get(Shipment, shipment_id) is None:
        raise NotFoundError("Shipment not found.")

    grievance = Grievance(
        raised_by=raiser.id,
        category=category,
        order_id=order_id,
        shipment_id=shipment_id,
        subject=subject,
        description=description,
        status=GrievanceStatus.OPEN,
        ack_deadline_at=_ack_deadline(db),
    )
    db.add(grievance)
    db.commit()
    db.refresh(grievance)
    return grievance


def list_for_user(
    db: Session, user_id: uuid.UUID, *, page: int = 1, page_size: int = 20
) -> tuple[list[Grievance], int]:
    return _paginated(
        select(Grievance).where(Grievance.raised_by == user_id), db, page, page_size
    )


def list_all(
    db: Session,
    *,
    status: GrievanceStatus | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Grievance], int]:
    q = select(Grievance)
    if status is not None:
        q = q.where(Grievance.status == status)
    return _paginated(q, db, page, page_size)


def _paginated(q, db: Session, page: int, page_size: int) -> tuple[list[Grievance], int]:
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(
        q.order_by(Grievance.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), int(total)
