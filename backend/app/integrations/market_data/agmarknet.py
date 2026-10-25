"""Agmarknet mandi-price integration: one interface, three providers.

Providers (all behind :class:`MarketDataProvider`):

- :class:`AgmarknetDataGovClient` — primary REAL adapter hitting the official
  data.gov.in resource ``9ef84268-d588-465a-a308-a864a43d0070`` (Agmarknet
  daily mandi prices, Ministry of Agriculture).
- :class:`MandiMirrorClient` — REAL fallback adapter (mandi-api.vercel.app /
  mandi-api.onrender.com) that republishes the same Agmarknet data.
- :class:`SyntheticAgmarknetClient` — clearly-labelled MOCK generator with
  realistic seasonal patterns; every record it produces carries
  ``is_synthetic=True`` and source ``SYNTHETIC``.

All prices are kept in the source unit (Rs/quintal for Agmarknet) in
:class:`RawPriceRecord`; the importer converts to integer paise.

Run the importer as a command (from ``backend/``)::

    python -m app.integrations.market_data            # auto provider
    python -m app.integrations.market_data --provider mirror
"""

from __future__ import annotations

import logging
import math
import os
import random
import statistics
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Protocol

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import Commodity
from app.models.enums import (
    CommodityCategory,
    DataQualityStatus,
    PriceSourceType,
    UnitEnum,
)
from app.models.market import DataImportJob, ImportJobStatus, MarketPriceObservation

logger = logging.getLogger("khetse.market_data")

# --- Source constants -------------------------------------------------------

DATA_GOV_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
DATA_GOV_BASE_URL = "https://api.data.gov.in/resource/" + DATA_GOV_RESOURCE_ID
# Public sample key from data.gov.in's API portal; overridable via env/settings.
DEFAULT_DATA_GOV_API_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"
MANDI_MIRROR_BASE_URL = "https://mandi-api.onrender.com/v1"

# Agmarknet quotes prices in Rs per quintal.
SOURCE_UNIT = UnitEnum.QUINTAL

# Rows from /prices/history are state-wide averages (no district). They are
# stored under this sentinel district so district-filtered queries never mix
# aggregated and market-level rows silently.
STATE_AVG_DISTRICT = "State Average"

# A record older than this many days before "today" is flagged STALE.
STALE_AFTER_DAYS = 14
# A record whose modal price is this far off the cross-sectional median of the
# same commodity/state/day (ratio) is flagged ANOMALOUS.
OUTLIER_RATIO = 5.0

RS_PER_QUINTAL_TO_PAISE = 100  # Rs 1/quintal = 100 paise/quintal


@dataclass
class RawPriceRecord:
    """One normalised mandi price row, unit: Rs per quintal."""

    commodity: str
    state: str
    district: str
    market_name: str
    observed_on: date
    min_price_rs: float | None = None
    modal_price_rs: float | None = None
    max_price_rs: float | None = None
    variety: str | None = None
    grade: str | None = None
    arrival_qty: float | None = None  # quintals, when the source reports it
    is_synthetic: bool = False
    source: PriceSourceType = PriceSourceType.AGMARKNET
    source_ref: str = ""
    raw: dict = field(default_factory=dict)
    data_quality: DataQualityStatus = DataQualityStatus.VALID
    # Snapshot records claim to be the market's LATEST report; for them an
    # old observed_on genuinely means "stale". History records are old by
    # construction, so staleness must not be judged on them.
    is_snapshot: bool = False


class MarketDataProvider(Protocol):
    """The single interface every provider implements."""

    name: str
    is_synthetic: bool

    def fetch_latest(self, state: str, commodity: str) -> list[RawPriceRecord]:
        """Latest snapshot, one row per market."""
        ...

    def fetch_history(self, state: str, commodity: str) -> list[RawPriceRecord]:
        """Daily history (state-wide averages when the source aggregates)."""
        ...


def _parse_price(value) -> float | None:
    """Agmarknet prices arrive as numbers or comma-separated strings."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        result = float(value)
    else:
        text = str(value).strip().replace(",", "")
        if not text:
            return None
        try:
            result = float(text)
        except ValueError:
            return None
    return result if math.isfinite(result) else None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


class AgmarknetDataGovClient:
    """REAL adapter for the official data.gov.in Agmarknet resource."""

    name = "data_gov_in_agmarknet"
    is_synthetic = False

    def __init__(self, api_key: str | None = None, timeout: float = 90.0):
        self.api_key = api_key or os.environ.get(
            "DATA_GOV_IN_API_KEY", DEFAULT_DATA_GOV_API_KEY
        )
        self.timeout = timeout

    def _get(self, params: dict) -> list[dict]:
        base = {"api-key": self.api_key, "format": "json", "limit": 200}
        base.update(params)
        with httpx.Client(timeout=httpx.Timeout(self.timeout, connect=20.0)) as client:
            resp = client.get(DATA_GOV_BASE_URL, params=base)
            resp.raise_for_status()
            body = resp.json()
        return body.get("records", []) or []

    def fetch_latest(self, state: str, commodity: str) -> list[RawPriceRecord]:
        records = self._get(
            {"filters[state]": state, "filters[commodity]": commodity}
        )
        return [self._to_record(r, state, commodity) for r in records]

    def fetch_history(self, state: str, commodity: str) -> list[RawPriceRecord]:
        # The data.gov.in resource is a daily snapshot; historical depth comes
        # from repeated daily imports, so history is whatever is in today's
        # snapshot (still market-level rows).
        return self.fetch_latest(state, commodity)

    def _to_record(self, r: dict, state: str, commodity: str) -> RawPriceRecord:
        return RawPriceRecord(
            commodity=str(r.get("commodity") or commodity),
            state=str(r.get("state") or state),
            district=str(r.get("district") or "").strip(),
            market_name=str(r.get("market") or "").strip(),
            observed_on=_parse_date(r.get("arrival_date")) or date.today(),
            min_price_rs=_parse_price(r.get("min_price")),
            modal_price_rs=_parse_price(r.get("modal_price")),
            max_price_rs=_parse_price(r.get("max_price")),
            variety=r.get("variety"),
            grade=r.get("grade"),
            arrival_qty=_parse_price(r.get("arrivalsFinds") or r.get("arrival_qty")),
            source=PriceSourceType.AGMARKNET,
            source_ref=f"data.gov.in:{DATA_GOV_RESOURCE_ID}",
            raw=dict(r),
        )


class MandiMirrorClient:
    """REAL fallback adapter — republishes Agmarknet (data.gov.in) data."""

    name = "mandi_mirror_agmarknet"
    is_synthetic = False

    def __init__(self, base_url: str = MANDI_MIRROR_BASE_URL, timeout: float = 90.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, params: dict | None = None) -> dict:
        with httpx.Client(timeout=httpx.Timeout(self.timeout, connect=20.0)) as client:
            resp = client.get(f"{self.base_url}{path}", params=params or {})
            resp.raise_for_status()
            return resp.json()

    def fetch_latest(self, state: str, commodity: str) -> list[RawPriceRecord]:
        body = self._get("/prices", {"state": state, "commodity": commodity})
        out = []
        for r in body.get("data", []) or []:
            out.append(
                RawPriceRecord(
                    commodity=str(r.get("commodity") or commodity),
                    state=str(r.get("state") or state),
                    district=str(r.get("district") or "").strip(),
                    market_name=str(r.get("market") or "").strip(),
                    observed_on=_parse_date(r.get("arrival_date")) or date.today(),
                    min_price_rs=_parse_price(r.get("min_price")),
                    modal_price_rs=_parse_price(r.get("modal_price")),
                    max_price_rs=_parse_price(r.get("max_price")),
                    variety=r.get("variety"),
                    grade=r.get("grade"),
                    source=PriceSourceType.AGMARKNET,
                    source_ref="mandi-api.onrender.com/v1/prices "
                    "(Agmarknet mirror of data.gov.in resource "
                    f"{DATA_GOV_RESOURCE_ID})",
                    raw=dict(r),
                )
            )
        return out

    def fetch_history(self, state: str, commodity: str) -> list[RawPriceRecord]:
        body = self._get(
            "/prices/history", {"state": state, "commodity": commodity}
        )
        out = []
        for r in body.get("data", []) or []:
            out.append(
                RawPriceRecord(
                    commodity=commodity,
                    state=state,
                    district=STATE_AVG_DISTRICT,
                    market_name=f"{state} State Average",
                    observed_on=_parse_date(r.get("arrival_date")) or date.today(),
                    min_price_rs=_parse_price(r.get("avg_min_price")),
                    modal_price_rs=_parse_price(r.get("avg_modal_price")),
                    max_price_rs=_parse_price(r.get("avg_max_price")),
                    source=PriceSourceType.AGMARKNET,
                    source_ref="mandi-api.onrender.com/v1/prices/history "
                    "(state-wide daily average, aggregated by the mirror)",
                    raw=dict(r),
                )
            )
        return out


# Illustrative base levels (Rs/quintal) roughly matching recent Agmarknet
# ranges — used ONLY by the clearly-labelled synthetic mock.
SYNTHETIC_BASE_PRICE_RS = {
    "Onion": 1800.0,
    "Tomato": 2500.0,
    "Potato": 1200.0,
    "Banana": 2200.0,
    "Wheat": 2400.0,
    "Maize": 2000.0,
}
SYNTHETIC_MARKETS = {
    "Karnataka": ["Davangere APMC", "Haveri APMC", "Kolar APMC"],
    "Maharashtra": ["Pune APMC", "Nashik APMC", "Kolhapur APMC"],
}
SYNTHETIC_DISTRICTS = {
    "Karnataka": ["Davangere", "Haveri", "Kolar"],
    "Maharashtra": ["Pune", "Nashik", "Kolhapur"],
}


class SyntheticAgmarknetClient:
    """MOCK provider: deterministic, clearly-labelled synthetic history.

    Seasonal model per (state, commodity):
    base price + annual sinusoid (monsoon/winter cycle) + slow random walk +
    daily noise. Every record is tagged ``is_synthetic=True`` and
    ``source=SYNTHETIC`` so it can never be confused with official data.
    """

    name = "synthetic_mock"
    is_synthetic = True

    def __init__(self, days: int = 180, seed: int = 20261025):
        self.days = days
        self.seed = seed

    def _series(self, state: str, commodity: str, market: str) -> list[RawPriceRecord]:
        rng = random.Random(f"{self.seed}:{state}:{commodity}:{market}".encode())
        base = SYNTHETIC_BASE_PRICE_RS.get(commodity, 1500.0)
        walk = 0.0
        today = date.today()
        rows: list[RawPriceRecord] = []
        for back in range(self.days - 1, -1, -1):
            day = today - timedelta(days=back)
            t = day.toordinal()
            # Annual seasonal cycle, amplitude 18% of base, phase fixed.
            seasonal = 0.18 * math.sin(2 * math.pi * (t % 365) / 365.0)
            walk += rng.gauss(0.0, 0.01)  # slow random walk
            walk = max(-0.25, min(0.25, walk))
            noise = rng.gauss(0.0, 0.04)
            modal = base * (1.0 + seasonal + walk + noise)
            spread = modal * rng.uniform(0.06, 0.16)
            rows.append(
                RawPriceRecord(
                    commodity=commodity,
                    state=state,
                    district="",
                    market_name=market,
                    observed_on=day,
                    min_price_rs=round(modal - spread, 2),
                    modal_price_rs=round(modal, 2),
                    max_price_rs=round(modal + spread, 2),
                    arrival_qty=round(
                        max(20.0, 200.0 * (1.0 + 0.3 * math.sin(2 * math.pi * t / 7.0))
                            + rng.gauss(0.0, 40.0)),
                        1,
                    ),
                    is_synthetic=True,
                    source=PriceSourceType.SYNTHETIC,
                    source_ref=f"synthetic_mock:seed={self.seed}",
                    raw={
                        "generator": "SyntheticAgmarknetClient",
                        "seed": self.seed,
                        "model": "base + annual sinusoid + random walk + noise",
                        "base_rs_per_quintal": base,
                    },
                )
            )
        return rows

    def _market_rows(self, state: str, commodity: str) -> list[RawPriceRecord]:
        """One deterministic series per synthetic market, geo-labelled."""
        markets = SYNTHETIC_MARKETS.get(state, [f"{state} APMC"])
        districts = SYNTHETIC_DISTRICTS.get(state, [state])
        out: list[RawPriceRecord] = []
        for idx, market in enumerate(markets):
            for rec in self._series(state, commodity, market):
                rec.market_name = market
                rec.district = districts[idx % len(districts)]
                out.append(rec)
        return out

    def fetch_latest(self, state: str, commodity: str) -> list[RawPriceRecord]:
        rows = self._market_rows(state, commodity)
        latest = max(r.observed_on for r in rows)
        return [r for r in rows if r.observed_on == latest]

    def fetch_history(self, state: str, commodity: str) -> list[RawPriceRecord]:
        rows = self._market_rows(state, commodity)
        by_day: dict[date, list[RawPriceRecord]] = {}
        for r in rows:
            by_day.setdefault(r.observed_on, []).append(r)
        out = []
        for day in sorted(by_day):
            day_rows = by_day[day]
            out.append(
                RawPriceRecord(
                    commodity=commodity,
                    state=state,
                    district=STATE_AVG_DISTRICT,
                    market_name=f"{state} State Average",
                    observed_on=day,
                    min_price_rs=round(
                        statistics.mean(r.min_price_rs for r in day_rows), 2
                    ),
                    modal_price_rs=round(
                        statistics.mean(r.modal_price_rs for r in day_rows), 2
                    ),
                    max_price_rs=round(
                        statistics.mean(r.max_price_rs for r in day_rows), 2
                    ),
                    arrival_qty=round(
                        statistics.mean(r.arrival_qty or 0.0 for r in day_rows), 1
                    ),
                    is_synthetic=True,
                    source=PriceSourceType.SYNTHETIC,
                    source_ref=f"synthetic_mock:seed={self.seed}",
                    raw={
                        "generator": "SyntheticAgmarknetClient",
                        "seed": self.seed,
                        "note": "state-wide average of synthetic market series",
                    },
                )
            )
        return out


class ProviderUnavailable(Exception):
    """Raised when a real provider cannot be reached."""


def resolve_provider(
    preference: str = "auto",
) -> tuple[MarketDataProvider, str]:
    """Pick a provider.

    Returns ``(provider, resolution_note)`` describing exactly which provider
    was chosen and why — the note is persisted on the import job so the
    provenance of every batch is auditable.
    """
    preference = (preference or "auto").lower()
    if preference == "synthetic":
        return SyntheticAgmarknetClient(), "explicit synthetic mock"
    if preference == "datagov":
        return AgmarknetDataGovClient(), "explicit data.gov.in (primary real source)"
    if preference == "mirror":
        return MandiMirrorClient(), "explicit Agmarknet mirror (fallback real source)"

    # auto: try the sources in order — official data.gov.in first, then the
    # Agmarknet mirror, then the clearly-labelled synthetic mock. Each probe
    # is one cheap request, and the note records exactly what happened.
    dg_error = "not attempted"
    try:
        AgmarknetDataGovClient(timeout=30.0)._get(
            {"limit": 1, "filters[state]": "Karnataka"}
        )
        return AgmarknetDataGovClient(), "auto: data.gov.in (official real source)"
    except Exception as dg_exc:  # noqa: BLE001
        dg_error = type(dg_exc).__name__
        logger.warning("data.gov.in unavailable (%s); trying mirror", dg_error)
    try:
        MandiMirrorClient(timeout=30.0)._get("/states")
        return MandiMirrorClient(), (
            f"auto: data.gov.in unreachable ({dg_error}); using the "
            "Agmarknet mirror (real data)"
        )
    except Exception as exc:  # noqa: BLE001 — any failure must fall back
        logger.warning("mirror provider unavailable (%s); using synthetic mock", exc)
        return (
            SyntheticAgmarknetClient(),
            f"auto: data.gov.in unreachable ({dg_error}) and mirror "
            f"unreachable ({type(exc).__name__}); synthetic mock generated",
        )


# --- Data-quality flagging --------------------------------------------------


def flag_quality(records: list[RawPriceRecord], today: date | None = None) -> None:
    """Set ``data_quality`` on every record, in place.

    Rules (transparent, order matters — first match wins):
    1. MISSING_FIELDS — no parseable modal price, or district/market missing.
    2. ANOMALOUS — any price <= 0, or min > max ordering violated.
    3. STALE — the market's NEWEST record in the batch (a market's latest
       report) is older than ``STALE_AFTER_DAYS`` days: that market has not
       reported recently. Older records behind a market's newest one, and
       records fetched as history, are historical by construction and stay
       unflagged by this rule.
    4. ANOMALOUS — cross-sectional outlier: modal deviates from the median
       modal of the same commodity/state/day by more than ``OUTLIER_RATIO`` x.
    5. VALID otherwise.
    """
    today = today or date.today()
    groups: dict[tuple[str, str, date], list[float]] = {}
    # Newest snapshot date per (commodity, state, market, district).
    market_newest: dict[tuple[str, str, str, str], date] = {}
    for r in records:
        if r.is_snapshot:
            key = (r.commodity, r.state, r.market_name, r.district)
            if key not in market_newest or r.observed_on > market_newest[key]:
                market_newest[key] = r.observed_on
    for r in records:
        if r.modal_price_rs is None or not r.district or not r.market_name:
            r.data_quality = DataQualityStatus.MISSING_FIELDS
            continue
        prices = [p for p in (r.min_price_rs, r.modal_price_rs, r.max_price_rs) if p is not None]
        if any(p <= 0 for p in prices):
            r.data_quality = DataQualityStatus.ANOMALOUS
            continue
        if (
            r.min_price_rs is not None
            and r.max_price_rs is not None
            and r.min_price_rs > r.max_price_rs
        ):
            r.data_quality = DataQualityStatus.ANOMALOUS
            continue
        if r.is_snapshot:
            key = (r.commodity, r.state, r.market_name, r.district)
            newest = market_newest.get(key)
            if newest is not None and r.observed_on == newest and newest < (
                today - timedelta(days=STALE_AFTER_DAYS)
            ):
                r.data_quality = DataQualityStatus.STALE
                continue
        groups.setdefault((r.commodity, r.state, r.observed_on), []).append(
            r.modal_price_rs
        )

    medians = {k: statistics.median(v) for k, v in groups.items()}
    for r in records:
        if r.data_quality != DataQualityStatus.VALID:
            continue
        key = (r.commodity, r.state, r.observed_on)
        med = medians.get(key)
        if med and med > 0 and (
            r.modal_price_rs > med * OUTLIER_RATIO
            or r.modal_price_rs < med / OUTLIER_RATIO
        ):
            r.data_quality = DataQualityStatus.ANOMALOUS


# --- Import command ---------------------------------------------------------


@dataclass
class ImportSummary:
    provider_name: str
    provider_note: str
    records_read: int
    records_written: int
    records_rejected: int
    duplicates_skipped: int
    commodities: list[str]
    states: list[str]
    job_id: str


COMMODITY_CATEGORIES = {
    "Onion": CommodityCategory.VEGETABLE,
    "Tomato": CommodityCategory.VEGETABLE,
    "Potato": CommodityCategory.VEGETABLE,
    "Banana": CommodityCategory.FRUIT,
    "Wheat": CommodityCategory.GRAIN,
    "Maize": CommodityCategory.GRAIN,
}


def get_or_create_commodity(session: Session, name_en: str) -> Commodity:
    """Commodities are matched case-insensitively on the English name."""
    row = session.scalar(
        select(Commodity).where(Commodity.name_en.ilike(name_en.strip()))
    )
    if row is not None:
        return row
    row = Commodity(
        name_en=name_en.strip(),
        category=COMMODITY_CATEGORIES.get(name_en, CommodityCategory.OTHER),
        default_unit=UnitEnum.KG,
    )
    session.add(row)
    session.flush()
    return row


def import_market_prices(
    session: Session,
    provider: MarketDataProvider,
    commodities: list[str],
    states: list[str],
    include_history: bool = True,
    provider_note: str = "",
) -> ImportSummary:
    """Fetch from ``provider`` and persist MarketPriceObservation rows.

    Every fetched record is preserved verbatim in ``raw_payload``; typed
    columns carry the cleaned paise values and a data-quality flag. One row
    is kept per (commodity, market, district, day, source): exact re-import
    duplicates AND additional variety/grade rows for the same market are
    counted together in ``duplicates_skipped`` (first row wins, the rest stay
    in raw_payload of their own fetch only) — this keeps the cross-market
    median un-weighted by multi-variety markets.
    """
    job = DataImportJob(
        source=(
            PriceSourceType.SYNTHETIC
            if provider.is_synthetic
            else PriceSourceType.AGMARKNET
        ),
        status=ImportJobStatus.RUNNING,
        started_at=datetime.now(tz=timezone.utc),
    )
    session.add(job)
    session.flush()

    records_read = records_written = records_rejected = duplicates = 0

    for commodity_name in commodities:
        commodity = get_or_create_commodity(session, commodity_name)
        fetched: list[RawPriceRecord] = []
        for state in states:
            try:
                latest = provider.fetch_latest(state, commodity_name)
                for rec in latest:
                    rec.is_snapshot = True
                fetched.extend(latest)
                if include_history:
                    fetched.extend(provider.fetch_history(state, commodity_name))
            except Exception as exc:  # noqa: BLE001 — record, keep going
                logger.error(
                    "fetch failed provider=%s state=%s commodity=%s: %s",
                    provider.name, state, commodity_name, exc,
                )
                records_rejected += 1
                continue

        flag_quality(fetched)
        records_read += len(fetched)

        existing = {
            (
                str(o.commodity_id),
                o.market_name,
                o.district,
                o.observed_on,
                o.source,
            )
            for o in session.scalars(
                select(MarketPriceObservation).where(
                    MarketPriceObservation.commodity_id == commodity.id
                )
            )
        }

        for rec in fetched:
            key = (
                str(commodity.id),
                rec.market_name,
                rec.district,
                rec.observed_on,
                rec.source,
            )
            if key in existing:
                duplicates += 1
                continue
            session.add(
                MarketPriceObservation(
                    commodity_id=commodity.id,
                    market_name=rec.market_name,
                    district=rec.district,
                    state=rec.state,
                    observed_on=rec.observed_on,
                    min_price_paise=(
                        int(round(rec.min_price_rs * RS_PER_QUINTAL_TO_PAISE))
                        if rec.min_price_rs is not None
                        else None
                    ),
                    modal_price_paise=(
                        int(round(rec.modal_price_rs * RS_PER_QUINTAL_TO_PAISE))
                        if rec.modal_price_rs is not None
                        else None
                    ),
                    max_price_paise=(
                        int(round(rec.max_price_rs * RS_PER_QUINTAL_TO_PAISE))
                        if rec.max_price_rs is not None
                        else None
                    ),
                    unit=SOURCE_UNIT,
                    arrival_quantity=rec.arrival_qty,
                    source=rec.source,
                    source_ref=rec.source_ref,
                    data_quality=rec.data_quality,
                    raw_payload={
                        **rec.raw,
                        "_quality_flags": {
                            "flag": rec.data_quality.value,
                            "stale_after_days": STALE_AFTER_DAYS,
                            "outlier_ratio": OUTLIER_RATIO,
                        },
                    },
                    is_synthetic=rec.is_synthetic,
                )
            )
            existing.add(key)
            records_written += 1

    job.records_read = records_read
    job.records_written = records_written
    job.records_rejected = records_rejected
    job.status = ImportJobStatus.COMPLETED
    job.finished_at = datetime.now(tz=timezone.utc)
    session.commit()

    return ImportSummary(
        provider_name=provider.name,
        provider_note=provider_note,
        records_read=records_read,
        records_written=records_written,
        records_rejected=records_rejected,
        duplicates_skipped=duplicates,
        commodities=commodities,
        states=states,
        job_id=str(job.id),
    )
