"""Runtime-configurable platform settings (fees, limits, toggles).

Values live in the platform_settings table so admins can change business rules
without a deploy. Defaults below are the proposed commercial rules from the
product spec and are NOT immutable facts.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ValidationAppError
from app.models.ops import PlatformSetting

DEFAULTS: dict[str, dict] = {
    # Buyer-side platform fee, % of produce subtotal (spec proposes 2–3%).
    "platform_fee_percent": {"value": 2.5, "description": "Platform fee charged to buyers, % of subtotal"},
    # Flat delivery fee charged to the buyer (paise).
    "delivery_fee_base_paise": {"value": 3000, "description": "Base delivery fee in paise"},
    # Per-km component applied when distance is known (paise/km).
    "delivery_fee_per_km_paise": {"value": 500, "description": "Per-km delivery fee in paise"},
    # Share of the delivery fee paid to the driver (%); remainder is platform.
    "driver_fee_share_percent": {"value": 80.0, "description": "Driver's share of delivery fee, %"},
    # Any seller-side deduction from farmer proceeds (%); default 0 — farmers
    # pay nothing. Can only be changed knowingly via the admin interface.
    "farmer_deduction_percent": {"value": 0.0, "description": "Deduction from farmer proceeds, % (default 0)"},
    # Hours after order confirmation until delivery is considered delayed.
    "grievance_ack_hours": {"value": 24, "description": "Grievance acknowledgement SLA in hours"},
    "max_route_stops": {"value": 12, "description": "Maximum stops per consolidated shipment"},
}


def get_setting(db: Session, key: str):
    row = db.scalar(select(PlatformSetting).where(PlatformSetting.key == key))
    if row is not None and row.value is not None:
        return row.value
    default = DEFAULTS.get(key)
    return default["value"] if default else None


def _coerce_setting_value(key: str, value, default_value) -> object:
    """Coerce `value` to the type of the setting's documented default.

    Settings are stored as JSON, so a typo like `"2,5"` or `True` for a
    percent would otherwise flow straight into fee arithmetic.
    """
    expected = type(default_value)
    if expected is bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip().lower() in ("true", "false"):
            return value.strip().lower() == "true"
        raise _setting_type_error(key, expected)
    if expected is int:
        if isinstance(value, bool) or isinstance(value, float) and not value.is_integer():
            raise _setting_type_error(key, expected)
        try:
            return int(value)
        except (TypeError, ValueError):
            raise _setting_type_error(key, expected) from None
    if expected is float:
        if isinstance(value, bool):
            raise _setting_type_error(key, expected)
        try:
            return float(value)
        except (TypeError, ValueError):
            raise _setting_type_error(key, expected) from None
    if expected is str:
        if isinstance(value, str):
            return value
        raise _setting_type_error(key, expected)
    # Unknown default type: store as-is.
    return value


def _setting_type_error(key: str, expected: type) -> ValidationAppError:
    return ValidationAppError(
        f"Setting '{key}' expects a value of type {expected.__name__}.",
        details={"key": key, "expected_type": expected.__name__},
    )


def set_setting(db: Session, key: str, value, updated_by=None) -> PlatformSetting:
    default = DEFAULTS.get(key)
    if default is not None:
        value = _coerce_setting_value(key, value, default["value"])
    row = db.scalar(select(PlatformSetting).where(PlatformSetting.key == key))
    if row is None:
        row = PlatformSetting(
            key=key,
            value=value,
            description=default.get("description") if default else None,
            updated_by=updated_by,
        )
        db.add(row)
    else:
        row.value = value
        row.updated_by = updated_by
    db.commit()
    return row


def all_settings(db: Session) -> dict[str, object]:
    return {key: get_setting(db, key) for key in DEFAULTS}
