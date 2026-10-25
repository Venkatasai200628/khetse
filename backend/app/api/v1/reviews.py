"""Review endpoints: post after a completed order, public farmer reviews."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.enums import RoleEnum
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewPublic
from app.services import review_service

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("", response_model=ReviewPublic, status_code=201)
def create_review(
    body: ReviewCreate,
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(RoleEnum.BUYER, RoleEnum.BUSINESS)),
):
    """Review a COMPLETED order. One review per order; only the buyer may
    write it; the rating must be 1–5."""
    review = review_service.create_review(
        db, buyer, order_id=body.order_id, rating=body.rating, comment=body.comment
    )
    return ReviewPublic(
        id=review.id,
        order_id=review.order_id,
        reviewer_id=review.reviewer_id,
        reviewer_name=review_service.reviewer_name(db, review),
        farmer_id=review.farmer_id,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
    )


@router.get("/farmer/{farmer_id}", response_model=list[ReviewPublic])
def farmer_reviews(
    farmer_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Public read: reviews attributed to a farmer, newest first."""
    reviews = review_service.list_for_farmer(db, farmer_id)
    return [
        ReviewPublic(
            id=r.id,
            order_id=r.order_id,
            reviewer_id=r.reviewer_id,
            reviewer_name=review_service.reviewer_name(db, r),
            farmer_id=r.farmer_id,
            rating=r.rating,
            comment=r.comment,
            created_at=r.created_at,
        )
        for r in reviews
    ]
