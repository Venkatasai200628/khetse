"""Notification centre: creation, per-user listing, read marking.

An in-app notification is 'delivered' by the write itself (status SENT);
SMS/voice rows stay QUEUED until a provider adapter drains them — no
external provider is wired in this build, so they remain visible as
queued rather than pretending to have been sent.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.enums import NotificationChannel, NotificationStatus
from app.models.ops import Notification


def create_notification(
    db: Session,
    *,
    user_id: uuid.UUID,
    category: str,
    title: str,
    body: str,
    channel: NotificationChannel = NotificationChannel.IN_APP,
    language: str = "en",
    related_order_id: uuid.UUID | None = None,
    related_shipment_id: uuid.UUID | None = None,
    meta: dict | None = None,
) -> Notification:
    """Persist one notification row and return it.

    In-app channels are immediately SENT; every other channel is QUEUED
    for the (future) provider workers.
    """
    notification = Notification(
        user_id=user_id,
        channel=channel,
        category=category,
        title=title,
        body=body,
        language=language,
        status=(
            NotificationStatus.SENT
            if channel == NotificationChannel.IN_APP
            else NotificationStatus.QUEUED
        ),
        related_order_id=related_order_id,
        related_shipment_id=related_shipment_id,
        meta=meta,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def list_for_user(
    db: Session,
    user_id: uuid.UUID,
    *,
    unread_only: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Notification], int, int]:
    """(rows, total_matching, unread_total) for the notification centre."""
    base = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        base = base.where(Notification.status != NotificationStatus.READ)

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    unread = db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.status != NotificationStatus.READ,
        )
    ) or 0
    rows = db.scalars(
        base.order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), int(total), int(unread)


def mark_read(db: Session, user_id: uuid.UUID, notification_id: uuid.UUID) -> Notification:
    """Mark one of *user_id*'s notifications as read. Idempotent."""
    notification = db.get(Notification, notification_id)
    if notification is None or notification.user_id != user_id:
        # A foreign id is indistinguishable from a missing one.
        raise NotFoundError("Notification not found.")
    if notification.status != NotificationStatus.READ:
        notification.status = NotificationStatus.READ
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notification)
    return notification
