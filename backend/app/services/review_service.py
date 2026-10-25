"""Post-delivery reviews.

Rules enforced here, not in the UI:
- only the buyer of an order may review it,
- only COMPLETED orders may be reviewed (delivered ≠ settled, and an open
  order can still be cancelled),
- one review per order (DB unique constraint is the backstop).
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AuthorizationError, ConflictError, NotFoundError
from app.models.commerce import Order, OrderItem
from app.models.enums import OrderStatus
from app.models.ops import Review
from app.models.user import User


def create_review(
    db: Session,
    reviewer: User,
    *,
    order_id: uuid.UUID,
    rating: int,
    comment: str | None = None,
) -> Review:
    order = db.get(Order, order_id)
    if order is None:
        raise NotFoundError("Order not found.")
    if order.buyer_id != reviewer.id:
        raise AuthorizationError("Only the buyer of this order can review it.")
    if order.status != OrderStatus.COMPLETED:
        raise ConflictError(
            "Reviews can only be left for completed orders.",
            details={"current_status": order.status.value},
        )
    if db.scalar(select(Review).where(Review.order_id == order_id)) is not None:
        raise ConflictError("This order has already been reviewed.")

    # Attribute the review to the farmer when every line came from one farm;
    # mixed multi-farmer orders review the overall experience only.
    farmer_ids = {item.farmer_id for item in order.items}
    farmer_id = farmer_ids.pop() if len(farmer_ids) == 1 else None

    review = Review(
        order_id=order_id,
        reviewer_id=reviewer.id,
        farmer_id=farmer_id,
        rating=rating,
        comment=comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def list_for_farmer(db: Session, farmer_id: uuid.UUID) -> list[Review]:
    """All reviews attributed to a farmer, newest first. Public read."""
    return list(
        db.scalars(
            select(Review)
            .where(Review.farmer_id == farmer_id)
            .order_by(Review.created_at.desc())
        ).all()
    )


def reviewer_name(db: Session, review: Review) -> str | None:
    user = db.get(User, review.reviewer_id)
    return user.full_name if user else None


def order_farmer_ids(db: Session, order: Order) -> set[uuid.UUID]:  # pragma: no cover
    """Utility kept for admin tooling; not used on the hot path."""
    return {
        row for row in db.scalars(
            select(OrderItem.farmer_id).where(OrderItem.order_id == order.id)
        )
    }
