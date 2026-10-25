"""Imports all model modules so Base.metadata is complete.

Alembic autogeneration and metadata.create_all() both rely on this package
importing every model module.
"""

from app.models import (  # noqa: F401
    catalog,
    commerce,
    finance,
    logistics,
    market,
    ops,
    otp,
    profiles,
    user,
)
