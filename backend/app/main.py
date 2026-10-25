"""KhetSe API entrypoint."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import root_health_router
from app.api.v1 import router as api_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers

settings = get_settings()

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("khetse")

app = FastAPI(
    title="KhetSe API",
    version="0.1.0",
    description="Seedha Khet Se Ghar Tak — direct farm-to-buyer marketplace "
    "(SIH26033, Team HexaScrapers)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(root_health_router)  # /health at root for container checks

logger.info(
    "KhetSe API starting | env=%s demo_mode=%s", settings.ENV, settings.demo_mode
)
