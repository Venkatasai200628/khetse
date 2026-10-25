"""Health and readiness endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db

router = APIRouter(tags=["health"])


def _health_payload(db: Session) -> dict:
    settings = get_settings()
    try:
        db.execute(text("SELECT 1"))
        database = "connected"
        status = "ok"
    except Exception:
        database = "unavailable"
        status = "degraded"
    return {
        "status": status,
        "app": settings.APP_NAME,
        "env": settings.ENV,
        "demo_mode": settings.demo_mode,
        "database": database,
    }


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    return _health_payload(db)
