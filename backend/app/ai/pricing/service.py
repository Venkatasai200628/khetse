"""Transparent price recommendation over cleaned mandi observations.

No black box: the recommendation is the median of min/modal/max prices across
valid observations (one per market — the most recent per market), with the
benchmark market, the observation date, a confidence grade and a human
explanation attached. Every recommendation gets a ModelRun provenance row so
the exact inputs (window, counts, method version) are auditable.
"""

from __future__ import annotations

import statistics
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import Commodity
from app.models.enums import (
    DataQualityStatus,
    ModelType,
    RecommendationConfidence,
)
from app.models.market import MarketPriceObservation, ModelRun, PriceRecommendation

MODEL_VERSION = "stats-median-v1"

# Recommendation window and confidence rules (documented in the explanation).
WINDOW_DAYS = 30
HIGH_CONFIDENCE_MIN_MARKETS = 8
MEDIUM_CONFIDENCE_MIN_MARKETS = 4
RECENT_DAYS = 7  # benchmark must be this fresh for HIGH confidence


class InsufficientDataError(Exception):
    """Not a single valid observation in the window."""


def _dedupe_latest_per_market(
    rows: list[MarketPriceObservation],
) -> list[MarketPriceObservation]:
    """Keep only the most recent observation per (market, district)."""
    def _naive(dt):
        # SQLite returns naive datetimes, PostgreSQL aware — normalise.
        return dt.replace(tzinfo=None) if dt is not None else datetime.min

    best: dict[tuple[str, str], MarketPriceObservation] = {}
    for row in rows:
        key = (row.market_name, row.district)
        current = best.get(key)
        if current is None or (
            row.observed_on > current.observed_on
            or (
                row.observed_on == current.observed_on
                and _naive(row.imported_at) > _naive(current.imported_at)
            )
        ):
            best[key] = row
    return list(best.values())


def _format_rs(paise: int | None, unit: str) -> str:
    if paise is None:
        return "n/a"
    return f"Rs {paise / 100:,.2f}/{unit}"


def build_price_recommendation(
    session: Session,
    commodity_id,
    district: str | None = None,
    as_of: date | None = None,
    window_days: int = WINDOW_DAYS,
) -> PriceRecommendation:
    """Compute and persist one PriceRecommendation with full provenance."""
    as_of = as_of or date.today()
    window_start = as_of - timedelta(days=window_days)

    commodity = session.get(Commodity, commodity_id)
    if commodity is None:
        raise InsufficientDataError("commodity not found")

    base_q = select(MarketPriceObservation).where(
        MarketPriceObservation.commodity_id == commodity_id,
        MarketPriceObservation.observed_on >= window_start,
        MarketPriceObservation.observed_on <= as_of,
    )
    all_rows = list(session.scalars(base_q))

    def _counts(rows) -> dict[str, int]:
        return {
            "valid": sum(
                1 for r in rows if r.data_quality == DataQualityStatus.VALID
            ),
            "stale": sum(1 for r in rows if r.data_quality == DataQualityStatus.STALE),
            "anomalous": sum(
                1 for r in rows if r.data_quality == DataQualityStatus.ANOMALOUS
            ),
            "missing_fields": sum(
                1 for r in rows if r.data_quality == DataQualityStatus.MISSING_FIELDS
            ),
        }

    in_scope = [r for r in all_rows if r.district == district] if district else all_rows
    # District-filtered lookups with too little data widen to all districts;
    # the widening is recorded so the explanation stays truthful.
    widened = False
    valid = [
        r
        for r in in_scope
        if r.data_quality == DataQualityStatus.VALID
        and r.modal_price_paise is not None
        # State-average aggregate rows only used when no market rows exist.
        and not (
            r.district == "State Average"
            and any(x.district != "State Average" for x in in_scope)
        )
    ]
    if len(valid) < 3 and district:
        widened = True
        in_scope = all_rows
        valid = [
            r
            for r in in_scope
            if r.data_quality == DataQualityStatus.VALID
            and r.modal_price_paise is not None
            and not (
                r.district == "State Average"
                and any(x.district != "State Average" for x in in_scope)
            )
        ]

    if not valid:
        raise InsufficientDataError(
            f"no valid observations for commodity in the last {window_days} days"
        )

    cleaned = _dedupe_latest_per_market(valid)
    quality_counts = _counts(in_scope)

    mins = [r.min_price_paise for r in cleaned if r.min_price_paise is not None]
    modals = [r.modal_price_paise for r in cleaned if r.modal_price_paise is not None]
    maxs = [r.max_price_paise for r in cleaned if r.max_price_paise is not None]
    # Even-sized sets take the lower median (median_low) so every recommended
    # value is a price actually quoted by some market — never an average that
    # no market printed.
    rec_min = int(statistics.median_low(mins)) if mins else None
    rec_modal = int(statistics.median_low(modals))
    rec_max = int(statistics.median_low(maxs)) if maxs else None

    # Benchmark: the market whose modal price IS the recommended median
    # (deterministic middle row after sorting; ties broken by most recent).
    with_modal = sorted(
        cleaned,
        key=lambda r: (r.modal_price_paise, -r.observed_on.toordinal(), r.market_name),
    )
    benchmark = with_modal[(len(with_modal) - 1) // 2]

    latest_day = max(r.observed_on for r in cleaned)
    n_markets = len(cleaned)
    any_synthetic = any(r.is_synthetic for r in cleaned)

    if (
        n_markets >= HIGH_CONFIDENCE_MIN_MARKETS
        and (as_of - latest_day).days <= RECENT_DAYS
        and not any_synthetic
    ):
        confidence = RecommendationConfidence.HIGH
    elif n_markets >= MEDIUM_CONFIDENCE_MIN_MARKETS and not any_synthetic:
        confidence = RecommendationConfidence.MEDIUM
    else:
        confidence = RecommendationConfidence.LOW

    unit = benchmark.unit.value if benchmark.unit else "quintal"
    per_kg = f"Rs {rec_modal / 100 / 100:,.2f}/kg" if unit == "quintal" else ""

    excluded = (
        quality_counts["stale"]
        + quality_counts["anomalous"]
        + quality_counts["missing_fields"]
    )
    scope_note = (
        f"across all districts (no data for district '{district}')"
        if widened
        else (f"in district {district}" if district else "across all districts")
    )
    explanation = (
        f"Based on {n_markets} valid {'synthetic ' if any_synthetic else ''}"
        f"Agmarknet observations from {n_markets} markets {scope_note}, "
        f"latest {latest_day.isoformat()}: median (lower-median for even "
        f"counts, so every figure is a price a market actually quoted) modal "
        f"price {_format_rs(rec_modal, unit)} "
        f"(median min {_format_rs(rec_min, unit)}, median max {_format_rs(rec_max, unit)})"
        + (f", i.e. about {per_kg}" if per_kg else "")
        + f". Benchmark market: {benchmark.market_name} "
        f"({benchmark.district}, modal {_format_rs(benchmark.modal_price_paise, unit)} "
        f"on {benchmark.observed_on.isoformat()}, source {benchmark.source.value}). "
        f"{excluded} observation(s) in the {window_days}-day window were excluded "
        f"by data-quality flags (stale/anomalous/missing). Confidence "
        f"{confidence.value}: {'>=8 markets and data <=7 days old' if confidence == RecommendationConfidence.HIGH else '>=4 markets' if confidence == RecommendationConfidence.MEDIUM else 'fewer than 4 markets or synthetic-only data'}."
    )
    if any_synthetic:
        explanation += " All inputs are SYNTHETIC (mock) data."

    run = ModelRun(
        model_type=ModelType.PRICE_RECOMMENDATION,
        model_version=MODEL_VERSION,
        trained_on_from=min(r.observed_on for r in cleaned),
        trained_on_to=latest_day,
        training_data_description=(
            f"{n_markets} valid observations, {quality_counts['valid']} valid rows "
            f"in window; source={benchmark.source.value}; "
            f"synthetic={any_synthetic}"
        ),
        metrics={
            "n_observations_used": n_markets,
            "n_valid_rows_in_window": quality_counts["valid"],
            "n_excluded_stale": quality_counts["stale"],
            "n_excluded_anomalous": quality_counts["anomalous"],
            "n_excluded_missing_fields": quality_counts["missing_fields"],
            "median_min_paise": rec_min,
            "median_modal_paise": rec_modal,
            "median_max_paise": rec_max,
            "any_synthetic_inputs": any_synthetic,
        },
        parameters={
            "method": "lower-median of per-market latest valid observations",
            "window_days": window_days,
            "district": district,
            "widened_to_all_districts": widened,
            "high_confidence_min_markets": HIGH_CONFIDENCE_MIN_MARKETS,
            "medium_confidence_min_markets": MEDIUM_CONFIDENCE_MIN_MARKETS,
        },
        notes="Transparent statistics — no trained model involved.",
        ran_at=datetime.now(tz=timezone.utc),
    )
    session.add(run)
    session.flush()

    rec = PriceRecommendation(
        commodity_id=commodity_id,
        district=district,
        recommended_min_paise=int(rec_min) if rec_min is not None else None,
        recommended_modal_paise=int(rec_modal),
        recommended_max_paise=int(rec_max) if rec_max is not None else None,
        unit=benchmark.unit,
        benchmark_market=f"{benchmark.market_name} ({benchmark.district})",
        benchmark_observed_on=benchmark.observed_on,
        benchmark_source=benchmark.source,
        confidence=confidence,
        explanation=explanation,
        model_run_id=run.id,
    )
    session.add(rec)
    session.commit()
    session.refresh(rec)
    return rec
