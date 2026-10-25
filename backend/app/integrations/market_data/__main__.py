"""Import command for Agmarknet mandi prices.

Run from the backend directory::

    ../.venv/Scripts/python -m app.integrations.market_data   # Windows
    ../.venv/bin/python -m app.integrations.market_data        # Linux/macOS

Provider chain (``--provider auto``, the default): official data.gov.in
resource -> Agmarknet mirror -> clearly-labelled synthetic mock. Whatever was
used is printed and recorded on the import job.

Writes MarketPriceObservation rows (min/modal/max in paise, district,
observed_on, source, raw_payload, data-quality flags) plus a DataImportJob
audit row. Re-runs skip exact duplicates.
"""

import argparse
import logging
from datetime import date

import app.models  # noqa: F401 — register every model on Base.metadata
from app.db.session import Base, SessionLocal, engine
from app.integrations.market_data.agmarknet import (
    import_market_prices,
    resolve_provider,
)

logger = logging.getLogger("khetse.market_data.command")

DEFAULT_COMMODITIES = ["Onion", "Tomato", "Potato", "Banana", "Wheat", "Maize"]
DEFAULT_STATES = ["Karnataka", "Maharashtra"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import Agmarknet mandi prices into market_price_observations."
    )
    parser.add_argument(
        "--provider",
        choices=["auto", "datagov", "mirror", "synthetic"],
        default="auto",
        help="auto = data.gov.in -> mirror -> labelled synthetic mock",
    )
    parser.add_argument(
        "--commodities",
        nargs="+",
        default=DEFAULT_COMMODITIES,
        help="Commodity names as published by Agmarknet",
    )
    parser.add_argument("--states", nargs="+", default=DEFAULT_STATES)
    parser.add_argument("--no-history", action="store_true",
                        help="Skip the /prices/history backfill")
    args = parser.parse_args(argv)

    provider, note = resolve_provider(args.provider)
    print(f"provider: {provider.name}\nresolution: {note}")

    # Dev convenience so the command is runnable against a fresh DB; in
    # production the Alembic migrations own the schema. create_all is a no-op
    # when the tables already exist.
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        summary = import_market_prices(
            session,
            provider,
            commodities=args.commodities,
            states=args.states,
            include_history=not args.no_history,
            provider_note=note,
        )
    finally:
        session.close()

    print(
        f"read={summary.records_read} written={summary.records_written} "
        f"rejected_fetches={summary.records_rejected} "
        f"duplicates_skipped={summary.duplicates_skipped} "
        f"(job {summary.job_id}, {date.today()})"
    )
    print(f"synthetic={provider.is_synthetic}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
