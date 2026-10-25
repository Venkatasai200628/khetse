"""Public metadata endpoints: landing data for the mobile app."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.db.seed import DEMO_USERS

router = APIRouter(tags=["meta"])

TAGLINE = "Seedha Khet Se Ghar Tak"


@router.get("/welcome")
def welcome() -> dict:
    """Public landing endpoint — no auth. Lets the app show its name,
    tagline and whether demo features are enabled before any login.

    When demo mode is on, the seeded demo-login codes travel with it so
    the app has ONE authoritative source (`seed.DEMO_USERS`) instead of
    hardcoding the handles twice."""
    settings = get_settings()
    return {
        "app": settings.APP_NAME,
        "tagline": TAGLINE,
        "demo_mode": settings.demo_mode,
        # The handles POST /auth/demo-login accepts (demo mode only).
        "demo_codes": [code for code, *_ in DEMO_USERS] if settings.demo_mode else [],
    }
