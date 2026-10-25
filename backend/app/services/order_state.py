"""Explicit order state machine.

Every transition is validated against this graph, executed inside the same
transaction as the business change, and recorded as an OrderStatusEvent with
actor, timestamp, previous state, new state and reason. Illegal transitions
are rejected — never silently coerced.
"""

from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.models.commerce import Order, OrderStatusEvent
from app.models.enums import OrderStatus, RoleEnum
from app.models.user import User

# from_status -> {to_status: roles allowed to trigger the transition}
TRANSITIONS: dict[OrderStatus, dict[OrderStatus, frozenset[str]]] = {
    OrderStatus.CREATED: {
        OrderStatus.AWAITING_FARMER_CONFIRMATION: frozenset({"system"}),
        OrderStatus.CANCELLED: frozenset({"buyer", "admin"}),
    },
    OrderStatus.AWAITING_FARMER_CONFIRMATION: {
        OrderStatus.ACCEPTED: frozenset({"farmer", "fpo_operator", "admin"}),
        OrderStatus.REJECTED: frozenset({"farmer", "fpo_operator", "admin"}),
        OrderStatus.CANCELLED: frozenset({"buyer", "admin"}),
    },
    OrderStatus.ACCEPTED: {
        OrderStatus.PAYMENT_PENDING: frozenset({"system"}),
        OrderStatus.CANCELLED: frozenset({"buyer", "admin"}),
    },
    OrderStatus.PAYMENT_PENDING: {
        OrderStatus.CONFIRMED: frozenset({"system"}),  # payment success webhook
        OrderStatus.PAYMENT_FAILED: frozenset({"system"}),
        OrderStatus.CANCELLED: frozenset({"buyer", "admin"}),
    },
    OrderStatus.PAYMENT_FAILED: {
        OrderStatus.PAYMENT_PENDING: frozenset({"system"}),  # buyer retry
        OrderStatus.CANCELLED: frozenset({"buyer", "admin"}),
    },
    OrderStatus.CONFIRMED: {
        OrderStatus.PICKUP_SCHEDULED: frozenset({"fpo_operator", "admin", "system"}),
        OrderStatus.CANCELLED: frozenset({"admin"}),
        OrderStatus.DISPUTED: frozenset({"buyer", "farmer", "admin"}),
    },
    OrderStatus.PICKUP_SCHEDULED: {
        OrderStatus.PICKED_UP: frozenset({"driver", "fpo_operator", "admin"}),
        OrderStatus.CANCELLED: frozenset({"admin"}),
        OrderStatus.DISPUTED: frozenset({"buyer", "farmer", "admin"}),
    },
    OrderStatus.PICKED_UP: {
        OrderStatus.OUT_FOR_DELIVERY: frozenset({"driver", "fpo_operator", "admin"}),
        OrderStatus.DISPUTED: frozenset({"buyer", "farmer", "admin"}),
    },
    OrderStatus.OUT_FOR_DELIVERY: {
        OrderStatus.DELIVERED: frozenset({"driver", "admin"}),
        OrderStatus.DELIVERY_FAILED: frozenset({"driver", "admin"}),
        OrderStatus.DISPUTED: frozenset({"buyer", "farmer", "admin"}),
    },
    OrderStatus.DELIVERED: {
        OrderStatus.COMPLETED: frozenset({"system", "admin"}),
        OrderStatus.DISPUTED: frozenset({"buyer", "farmer", "admin"}),
    },
    OrderStatus.DELIVERY_FAILED: {
        OrderStatus.REFUND_PENDING: frozenset({"system", "admin"}),
        OrderStatus.DISPUTED: frozenset({"buyer", "farmer", "admin"}),
    },
    OrderStatus.REFUND_PENDING: {
        OrderStatus.REFUNDED: frozenset({"system", "admin"}),
    },
    OrderStatus.DISPUTED: {
        OrderStatus.COMPLETED: frozenset({"admin"}),
        OrderStatus.REFUND_PENDING: frozenset({"admin"}),
        OrderStatus.CANCELLED: frozenset({"admin"}),
    },
    # Terminal states: ACCEPTED→? no. REJECTED, CANCELLED, COMPLETED, REFUNDED
    # have no outgoing edges by design.
}

TERMINAL_STATES = frozenset(
    {OrderStatus.REJECTED, OrderStatus.CANCELLED, OrderStatus.COMPLETED, OrderStatus.REFUNDED}
)


def can_transition(frm: OrderStatus, to: OrderStatus) -> bool:
    return to in TRANSITIONS.get(frm, {})


def actor_role(user: User) -> str:
    """Primary role used for transition permission checks."""
    if user.has_role(RoleEnum.ADMIN):
        return "admin"
    if user.has_role(RoleEnum.FPO_OPERATOR):
        return "fpo_operator"
    if user.has_role(RoleEnum.DRIVER):
        return "driver"
    if user.has_role(RoleEnum.FARMER):
        return "farmer"
    return "buyer"


def apply_transition(
    db: Session,
    order: Order,
    to_status: OrderStatus,
    *,
    user: User | None = None,
    role_override: str | None = None,
    reason: str | None = None,
) -> Order:
    """Validate and apply a state transition, recording the audit event.

    The caller is responsible for committing (or rolling back) the enclosing
    transaction so business changes and the event stay atomic.
    """
    frm = order.status
    allowed_targets = TRANSITIONS.get(frm, {})
    if to_status not in allowed_targets:
        raise ConflictError(
            f"Order cannot move from '{frm.value}' to '{to_status.value}'.",
            details={"current_status": frm.value, "requested_status": to_status.value},
        )

    role = role_override or (actor_role(user) if user else "system")
    if role not in allowed_targets[to_status]:
        raise ConflictError(
            f"Role '{role}' is not allowed to move this order to '{to_status.value}'.",
            details={"role": role, "requested_status": to_status.value},
        )

    order.status = to_status
    db.add(
        OrderStatusEvent(
            order_id=order.id,
            from_status=frm,
            to_status=to_status,
            actor_user_id=user.id if user else None,
            actor_role=role,
            reason=reason,
        )
    )
    return order
