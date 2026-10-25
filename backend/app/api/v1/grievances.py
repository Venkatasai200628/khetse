"""Grievance endpoints: raise, list mine, admin queue."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import GrievanceStatus, RoleEnum
from app.models.user import User
from app.schemas.grievance import GrievanceCreate, GrievancePage, GrievancePublic
from app.services import grievance_service

router = APIRouter(prefix="/grievances", tags=["grievances"])


@router.post("", response_model=GrievancePublic, status_code=201)
def create_grievance(
    body: GrievanceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Raise a grievance; the admin acknowledgement deadline is set from
    the ``grievance_ack_hours`` platform setting."""
    return grievance_service.create_grievance(
        db,
        user,
        category=body.category,
        subject=body.subject,
        description=body.description,
        order_id=body.order_id,
        shipment_id=body.shipment_id,
    )


@router.get("/mine", response_model=GrievancePage)
def my_grievances(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows, total = grievance_service.list_for_user(
        db, user.id, page=page, page_size=page_size
    )
    return GrievancePage(
        items=[GrievancePublic.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/admin", response_model=GrievancePage)
def admin_grievances(
    status: GrievanceStatus | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(RoleEnum.ADMIN)),
):
    """Support queue: every grievance, optionally filtered by status."""
    rows, total = grievance_service.list_all(
        db, status=status, page=page, page_size=page_size
    )
    return GrievancePage(
        items=[GrievancePublic.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
