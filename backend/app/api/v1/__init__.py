"""Aggregates all v1 route groups."""

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    cart,
    commodities,
    grievances,
    health,
    listings,
    market,
    meta,
    notifications,
    orders,
    payments,
    reviews,
)

router = APIRouter()
router.include_router(health.router)
router.include_router(meta.router)
router.include_router(auth.router)
router.include_router(commodities.router)
router.include_router(listings.router)
router.include_router(cart.router)
router.include_router(orders.router)
router.include_router(payments.router)
router.include_router(market.router)
router.include_router(market.forecasts_router)
router.include_router(notifications.router)
router.include_router(grievances.router)
router.include_router(reviews.router)

# Root-level health for container orchestrators, sharing the same handler.
root_health_router = APIRouter(tags=["health"])
root_health_router.include_router(health.router)
