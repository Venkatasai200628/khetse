"""Application configuration.

All settings come from environment variables (see .env.example at the
repository root) with safe development defaults. Production deployments
must override the secrets.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The .env file lives at the repository root (see README quickstart); the
# app is routinely started from backend/, so resolve it absolutely instead
# of relying on the current working directory.
REPO_ROOT = Path(__file__).resolve().parents[3]

# Known placeholder secrets that must never reach a production server.
PLACEHOLDER_JWT_SECRETS = frozenset(
    {
        "change-me-generate-a-long-random-string",
        "dev-only-insecure-secret-change-me",
    }
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", env_ignore_empty=True, extra="ignore"
    )

    # --- Application ---
    APP_NAME: str = "KhetSe"
    ENV: str = "development"  # development | demo | production
    DEMO_MODE: bool = True
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    # --- Database / cache ---
    DATABASE_URL: str = "postgresql+psycopg2://khetse:khetse@localhost:5432/khetse"
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Auth ---
    JWT_SECRET: str = "dev-only-insecure-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    OTP_EXPIRE_SECONDS: int = 300
    OTP_MAX_ATTEMPTS: int = 5
    OTP_RATE_LIMIT_PER_HOUR: int = 5

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"

    # --- External integrations (empty => mock adapter, clearly labelled) ---
    DATA_GOV_IN_API_KEY: str = ""
    BHASHINI_API_KEY: str = ""
    BHASHINI_USER_ID: str = ""
    OSRM_BASE_URL: str = "https://router.project-osrm.org"
    WEATHER_PROVIDER: str = "open_meteo"  # open_meteo | imd
    IMD_API_KEY: str = ""
    PAYMENT_PROVIDER: str = "mock"  # mock | razorpay
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    SMS_PROVIDER: str = "mock"
    VOICE_PROVIDER: str = "mock"

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

    @model_validator(mode="after")
    def _check_jwt_secret(self) -> "Settings":
        weak = (
            self.JWT_SECRET in PLACEHOLDER_JWT_SECRETS
            or len(self.JWT_SECRET) < 32
        )
        if weak and self.is_production:
            raise ValueError(
                "JWT_SECRET is a known placeholder or shorter than 32 chars. "
                "Generate one with: python -c \"import secrets; "
                "print(secrets.token_urlsafe(48))\""
            )
        return self

    @property
    def demo_mode(self) -> bool:
        """Demo features can never be enabled in production."""
        return self.DEMO_MODE and not self.is_production

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
