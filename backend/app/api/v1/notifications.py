"""Notification endpoints: create, list mine, mark read."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.errors import AuthorizationError
from app.db.session import get_db
from app.models.enums import RoleEnum
from app.models.user import User
from app.schemas.notification import (
    NotificationCreate,
    NotificationPage,
    NotificationPublic,
)
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("", response_model=NotificationPublic, status_code=201)
def create_notification(
    body: NotificationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a notification. Targets the caller unless an admin names
    another user — users can never write into someone else's inbox."""
    target_id = body.user_id if body.user_id is not None else user.id
    if target_id != user.id and not user.has_role(RoleEnum.ADMIN):
        raise AuthorizationError("You can only create notifications for yourself.")
    return notification_service.create_notification(
        db,
        user_id=target_id,
        category=body.category,
        title=body.title,
        body=body.body,
        channel=body.channel,
        language=body.language,
        related_order_id=body.related_order_id,
        related_shipment_id=body.related_shipment_id,
        meta=body.meta,
    )


@router.get("/mine", response_model=NotificationPage)
def my_notifications(
    unread_only: bool = Query(default=False, description="Only unread notifications"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows, total, unread = notification_service.list_for_user(
        db, user.id, unread_only=unread_only, page=page, page_size=page_size
    )
    return NotificationPage(
        items=[NotificationPublic.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        unread=unread,
    )


@router.post("/{notification_id}/read", response_model=NotificationPublic)
def mark_notification_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    notification = notification_service.mark_read(db, user.id, notification_id)
    return NotificationPublic.model_validate(notification)
