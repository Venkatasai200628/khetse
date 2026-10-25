"""Market-data integrations (Agmarknet mandi prices).

See :mod:`app.integrations.market_data.agmarknet` for the provider interface,
the real adapters, the labelled synthetic mock and the import command.
"""

from app.integrations.market_data.agmarknet import (
    AgmarknetDataGovClient,
    ImportSummary,
    MandiMirrorClient,
    MarketDataProvider,
    RawPriceRecord,
    STATE_AVG_DISTRICT,
    SyntheticAgmarknetClient,
    flag_quality,
    get_or_create_commodity,
    import_market_prices,
    resolve_provider,
)

__all__ = [
    "AgmarknetDataGovClient",
    "ImportSummary",
    "MandiMirrorClient",
    "MarketDataProvider",
    "RawPriceRecord",
    "STATE_AVG_DISTRICT",
    "SyntheticAgmarknetClient",
    "flag_quality",
    "get_or_create_commodity",
    "import_market_prices",
    "resolve_provider",
]
