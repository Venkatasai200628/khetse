"""Platform settings service: type validation on write."""

import pytest

from app.core.errors import ValidationAppError
from app.db.session import SessionLocal
from app.services import settings_service


def test_set_setting_coerces_string_numbers_to_default_type(db):
    session = SessionLocal()
    try:
        row = settings_service.set_setting(session, "platform_fee_percent", "3")
        assert row.value == 3.0
        assert isinstance(row.value, float)

        row = settings_service.set_setting(session, "max_route_stops", "12")
        assert row.value == 12
        assert isinstance(row.value, int)

        # Reads observe the coerced value.
        assert settings_service.get_setting(session, "platform_fee_percent") == 3.0
    finally:
        session.close()


def test_set_setting_rejects_values_of_the_wrong_type(db):
    session = SessionLocal()
    try:
        with pytest.raises(ValidationAppError):
            settings_service.set_setting(session, "platform_fee_percent", "not-a-number")
        with pytest.raises(ValidationAppError):
            # A non-integral float cannot silently truncate a paise amount.
            settings_service.set_setting(session, "delivery_fee_base_paise", 2.5)
        with pytest.raises(ValidationAppError):
            # Booleans are not percents.
            settings_service.set_setting(session, "platform_fee_percent", True)
        # Nothing was written.
        assert settings_service.get_setting(session, "platform_fee_percent") == 2.5
    finally:
        session.close()


def test_unknown_keys_are_stored_without_coercion(db):
    session = SessionLocal()
    try:
        row = settings_service.set_setting(session, "custom_flag", {"nested": True})
        assert row.value == {"nested": True}
    finally:
        session.close()
