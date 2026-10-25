"""Order endpoints: checkout, farmer responses, buyer cancellation, views."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.core.errors import AuthorizationError, NotFoundError
from app.db.session import get_db
from app.models.catalog import Commodity
from app.models.commerce import Order, OrderItem
from app.models.enums import RoleEnum
from app.models.profiles import FarmerProfile
from app.models.user import User
from app.schemas.order import (
    CancelRequest,
    CheckoutRequest,
    FarmerResponse,
    OrderPage,
    OrderPublic,
)
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


def _to_public(order: Order, db: Session) -> OrderPublic:
    data = OrderPublic.model_validate(order)
    for item_dto, item_row in zip(data.items, order.items):
        if item_row.commodity_id is not None:
            commodity = db.get(Commodity, item_row.commodity_id)
            if commodity is not None:
                item_dto.commodity_name = commodity.name_en
    data.status_events = sorted(
        data.status_events, key=lambda e: e.created_at, reverse=True
    )
    return data


def _paginated(q, db: Session, page: int, page_size: int) -> OrderPage:
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(
        q.order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return OrderPage(
        items=[_to_public(r, db) for r in rows],
        total=int(total),
        page=page,
        page_size=page_size,
    )


@router.post("/checkout", response_model=OrderPublic, status_code=201)
def checkout(
    body: CheckoutRequest,
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(RoleEnum.BUYER, RoleEnum.BUSINESS)),
):
    order = order_service.create_order_from_cart(
        db,
        buyer,
        idempotency_key=body.idempotency_key,
        fulfilment=body.fulfilment.value,
        delivery_name=body.delivery_name,
        delivery_phone=body.delivery_phone,
        delivery_address=body.delivery_address,
        delivery_district=body.delivery_district,
        delivery_lat=body.delivery_lat,
        delivery_lng=body.delivery_lng,
        notes=body.notes,
    )
    return _to_public(order, db)


@router.get("/mine", response_model=OrderPage)
def my_orders(
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(RoleEnum.BUYER, RoleEnum.BUSINESS)),
):
    q = select(Order).where(Order.buyer_id == buyer.id)
    if status:
        q = q.where(Order.status == status)
    return _paginated(q, db, page, page_size)


@router.get("/farmer", response_model=OrderPage)
def farmer_orders(
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    farmer: User = Depends(require_roles(RoleEnum.FARMER, RoleEnum.FPO_OPERATOR)),
):
    # An FPO operator also sees orders containing their member farmers'
    # listings — the involvement rule the route's role check advertises.
    farmer_filter = OrderItem.farmer_id == farmer.id
    if farmer.has_role(RoleEnum.FPO_OPERATOR) and farmer.fpo_id is not None:
        member_ids = select(FarmerProfile.user_id).where(
            FarmerProfile.fpo_id == farmer.fpo_id
        )
        farmer_filter = or_(farmer_filter, OrderItem.farmer_id.in_(member_ids))
    q = (
        select(Order)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .where(farmer_filter)
        .distinct()
    )
    if status:
        q = q.where(Order.status == status)
    return _paginated(q, db, page, page_size)


@router.get("/{order_id}", response_model=OrderPublic)
def get_order(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(RoleEnum.BUYER, RoleEnum.BUSINESS, RoleEnum.FARMER, RoleEnum.FPO_OPERATOR, RoleEnum.ADMIN)),
):
    order = db.get(Order, order_id)
    if order is None:
        raise NotFoundError("Order not found.")

    # Ownership / involvement check — enforced server-side. The buyer, any
    # farmer with lines in the order and that farmer's FPO operator may view.
    if not order_service.is_order_participant(db, order, user) and not user.has_role(
        RoleEnum.ADMIN
    ):
        raise AuthorizationError("You do not have access to this order.")
    return _to_public(order, db)


@router.post("/{order_id}/farmer-response", response_model=OrderPublic)
def farmer_response(
    order_id: uuid.UUID,
    body: FarmerResponse,
    db: Session = Depends(get_db),
    farmer: User = Depends(require_roles(RoleEnum.FARMER, RoleEnum.FPO_OPERATOR)),
):
    order = order_service.farmer_respond(db, farmer, order_id, body.accept, body.reason)
    return _to_public(order, db)


@router.post("/{order_id}/cancel", response_model=OrderPublic)
def cancel_order(
    order_id: uuid.UUID,
    body: CancelRequest,
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(RoleEnum.BUYER, RoleEnum.BUSINESS)),
):
    order = order_service.buyer_cancel(db, buyer, order_id, body.reason)
    return _to_public(order, db)


@router.post("/{order_id}/pay", response_model=OrderPublic)
def pay_order(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(RoleEnum.BUYER, RoleEnum.BUSINESS)),
):
    """One-tap mock payment capture — only available while demo mode is on.

    A live order would otherwise dead-end at payment_pending (no real
    provider is wired yet); in production the provider's signed webhook
    (POST /payments/webhook) drives the same capture instead."""
    order = order_service.pay_order(db, buyer, order_id)
    return _to_public(order, db)


@router.post("/{order_id}/complete", response_model=OrderPublic)
def complete_order(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(RoleEnum.ADMIN)),
):
    """Admin close-out after delivery: consumes the inventory reservations
    (stock leaves the listings) and records completion timestamps."""
    order = order_service.complete_order(db, admin, order_id)
    return _to_public(order, db)
