"""Tests for the market-data + AI layer.

Covers:
- the Agmarknet importer (paise conversion, dedupe, provenance, jobs),
- data-quality flagging (missing fields, anomalies, staleness, outliers),
- the clearly-labelled synthetic fallback (provider resolution + import),
- transparent price-recommendation math (lower-median, benchmark market,
  confidence grades, exclusion of flagged rows, district widening),
- demand forecasting (seasonal-naive baseline with honest holdout metrics,
  LightGBM only on enough real history, ModelRun provenance),
- the /api/v1/market-prices/recommendation and /api/v1/forecasts endpoints.

No network access is needed: real providers are stubbed/monkeypatched.
"""

from datetime import date, timedelta
from uuid import UUID

import pytest

from app.db.session import SessionLocal
from app.integrations.market_data.agmarknet import (
    AgmarknetDataGovClient,
    MandiMirrorClient,
    RawPriceRecord,
    STALE_AFTER_DAYS,
    SyntheticAgmarknetClient,
    flag_quality,
    import_market_prices,
    resolve_provider,
)
from app.models.enums import (
    DataQualityStatus,
    PriceSourceType,
    RecommendationConfidence,
    UnitEnum,
)
from app.models.market import (
    DataImportJob,
    DemandForecast,
    MarketPriceObservation,
    ModelRun,
    PriceRecommendation,
)

from tests.helpers import register_user, seed_commodity


@pytest.fixture(autouse=True)
def _fresh_tables(db):
    """Every test in this module starts from clean tables (conftest's `db`)."""
    yield


# --- Local helpers ----------------------------------------------------------


def _rec(
    commodity="Onion",
    state="Karnataka",
    district="Belagavi",
    market="Belagavi APMC",
    observed_on=None,
    min_rs=90.0,
    modal_rs=100.0,
    max_rs=110.0,
    **kwargs,
) -> RawPriceRecord:
    return RawPriceRecord(
        commodity=commodity,
        state=state,
        district=district,
        market_name=market,
        observed_on=observed_on or date.today(),
        min_price_rs=min_rs,
        modal_price_rs=modal_rs,
        max_price_rs=max_rs,
        **kwargs,
    )


class StubProvider:
    """Minimal deterministic provider for importer tests."""

    name = "stub"
    is_synthetic = False

    def __init__(self, records_by_commodity):
        self.records = records_by_commodity

    def fetch_latest(self, state, commodity):
        return [r for r in self.records.get(commodity, []) if r.observed_on == max(
            x.observed_on for x in self.records.get(commodity, [r])
        )]

    def fetch_history(self, state, commodity):
        return self.records.get(commodity, [])


def _uuid(v) -> UUID:
    """helpers.seed_commodity returns the id as str; ORM needs a UUID."""
    return v if isinstance(v, UUID) else UUID(str(v))


def _seed_observations(commodity_id, rows):
    """Insert MarketPriceObservation rows given dicts of paise values."""
    commodity_id = _uuid(commodity_id)
    db = SessionLocal()
    try:
        for kw in rows:
            db.add(
                MarketPriceObservation(
                    commodity_id=commodity_id,
                    market_name=kw["market"],
                    district=kw.get("district", "Belagavi"),
                    state=kw.get("state", "Karnataka"),
                    observed_on=kw["observed_on"],
                    min_price_paise=kw.get("min_paise"),
                    modal_price_paise=kw["modal_paise"],
                    max_price_paise=kw.get("max_paise"),
                    unit=kw.get("unit", UnitEnum.QUINTAL),
                    arrival_quantity=kw.get("arrival_qty"),
                    source=kw.get("source", PriceSourceType.AGMARKNET),
                    data_quality=kw.get("data_quality", DataQualityStatus.VALID),
                    is_synthetic=kw.get("is_synthetic", False),
                )
            )
        db.commit()
    finally:
        db.close()


def _latest_run(db, model_type):
    return (
        db.query(ModelRun)
        .where(ModelRun.model_type == model_type)
        .order_by(ModelRun.ran_at.desc())
        .first()
    )


# --- Data-quality flagging --------------------------------------------------


def test_flag_quality_valid_record_stays_valid():
    records = [_rec()]
    flag_quality(records)
    assert records[0].data_quality == DataQualityStatus.VALID


def test_flag_quality_missing_fields():
    no_modal = _rec(min_rs=None, modal_rs=None, max_rs=None)
    no_district = _rec(district="")
    no_market = _rec(market="")
    flag_quality([no_modal, no_district, no_market])
    assert no_modal.data_quality == DataQualityStatus.MISSING_FIELDS
    assert no_district.data_quality == DataQualityStatus.MISSING_FIELDS
    assert no_market.data_quality == DataQualityStatus.MISSING_FIELDS


def test_flag_quality_anomalous_prices():
    zero = _rec(min_rs=0.0, modal_rs=100.0)
    neg = _rec(modal_rs=-5.0)
    bad_order = _rec(min_rs=150.0, modal_rs=100.0, max_rs=90.0)
    flag_quality([zero, neg, bad_order])
    assert zero.data_quality == DataQualityStatus.ANOMALOUS
    assert neg.data_quality == DataQualityStatus.ANOMALOUS
    assert bad_order.data_quality == DataQualityStatus.ANOMALOUS


def test_flag_quality_stale_snapshot_only():
    old = date.today() - timedelta(days=STALE_AFTER_DAYS + 5)
    # A snapshot record IS the market's latest report: old date => stale.
    stale = _rec(observed_on=old, market="Old Mandi", is_snapshot=True)
    flag_quality([stale])
    assert stale.data_quality == DataQualityStatus.STALE
    # The same age as HISTORY (not a snapshot) is historical by construction.
    history = _rec(observed_on=old, market="Old Mandi")
    flag_quality([history])
    assert history.data_quality == DataQualityStatus.VALID
    # A market whose newest report is fresh is not stale.
    fresh = _rec(observed_on=date.today(), market="Fresh Mandi", is_snapshot=True)
    flag_quality([fresh])
    assert fresh.data_quality == DataQualityStatus.VALID


def test_flag_quality_cross_sectional_outlier():
    day = date.today()
    a = _rec(observed_on=day, market="Mandvi A", modal_rs=1000.0, min_rs=950.0, max_rs=1050.0)
    b = _rec(observed_on=day, market="Mandvi B", modal_rs=1100.0, min_rs=1000.0, max_rs=1150.0)
    outlier = _rec(observed_on=day, market="Mandvi C", modal_rs=9000.0, min_rs=8800.0, max_rs=9200.0)
    flag_quality([a, b, outlier])
    assert a.data_quality == DataQualityStatus.VALID
    assert b.data_quality == DataQualityStatus.VALID
    assert outlier.data_quality == DataQualityStatus.ANOMALOUS


# --- Importer ---------------------------------------------------------------


def test_import_converts_to_paise_and_records_provenance():
    commodity_id = seed_commodity(name_en="Onion")
    today = date.today()
    rec = _rec(
        observed_on=today, market="Belagavi APMC",
        min_rs=1500.0, modal_rs=2500.55, max_rs=3000.0,
        raw={"commodity": "Onion", "market": "Belagavi APMC"},
    )
    provider = StubProvider({"Onion": [rec]})
    db = SessionLocal()
    try:
        summary = import_market_prices(
            db, provider, commodities=["Onion"], states=["Karnataka"],
            include_history=False, provider_note="stub run",
        )
        rows = db.query(MarketPriceObservation).all()
        assert summary.records_written == 1
        assert len(rows) == 1
        row = rows[0]
        # Rs 2500.55/quintal -> 250055 paise (x100, rounded).
        assert row.modal_price_paise == 250055
        assert row.min_price_paise == 150000
        assert row.max_price_paise == 300000
        assert row.unit == UnitEnum.QUINTAL
        assert row.source == PriceSourceType.AGMARKNET
        assert row.is_synthetic is False
        assert row.district == "Belagavi"
        assert row.observed_on == today
        assert row.raw_payload["commodity"] == "Onion"  # raw payload preserved
        assert str(row.commodity_id) == commodity_id

        job = db.query(DataImportJob).order_by(DataImportJob.started_at.desc()).first()
        assert job is not None
        assert job.status.value == "completed"
        assert job.records_written == 1
        assert job.records_read == 1
        assert job.source == PriceSourceType.AGMARKNET
    finally:
        db.close()


def test_import_dedupes_reruns():
    seed_commodity(name_en="Onion")
    today = date.today()
    rec = _rec(observed_on=today, market="Belagavi APMC")
    provider = StubProvider({"Onion": [rec]})
    db = SessionLocal()
    try:
        first = import_market_prices(db, provider, ["Onion"], ["Karnataka"], include_history=False)
        assert first.records_written == 1
        second = import_market_prices(db, provider, ["Onion"], ["Karnataka"], include_history=False)
        assert second.records_written == 0
        assert second.duplicates_skipped >= 1
        assert db.query(MarketPriceObservation).count() == 1
    finally:
        db.close()


def test_synthetic_import_is_labelled():
    seed_commodity(name_en="Onion")
    provider = SyntheticAgmarknetClient(days=30)
    assert provider.is_synthetic is True
    db = SessionLocal()
    try:
        summary = import_market_prices(
            db, provider, ["Onion"], ["Karnataka"], include_history=True,
            provider_note="synthetic test",
        )
        assert provider.name == "synthetic_mock"
        assert summary.records_written > 0
        rows = db.query(MarketPriceObservation).all()
        assert rows
        for row in rows:
            assert row.is_synthetic is True
            assert row.source == PriceSourceType.SYNTHETIC
            assert row.raw_payload["generator"] == "SyntheticAgmarknetClient"
        # Realistic seasonal pattern: the modal series actually moves.
        modals = sorted({r.modal_price_paise for r in rows})
        assert len(modals) > 5
    finally:
        db.close()


def test_resolve_provider_falls_back_to_synthetic(monkeypatch):
    def boom(self, *a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(AgmarknetDataGovClient, "_get", boom)
    monkeypatch.setattr(MandiMirrorClient, "_get", boom)
    provider, note = resolve_provider("auto")
    assert isinstance(provider, SyntheticAgmarknetClient)
    assert provider.is_synthetic is True
    assert "synthetic" in note.lower()
    # The note records both real-source failures (by exception type name).
    assert "RuntimeError" in note


def test_resolve_provider_explicit_choices():
    provider, note = resolve_provider("synthetic")
    assert isinstance(provider, SyntheticAgmarknetClient)
    # Explicit real choices are returned without probing the network.
    dg, _ = resolve_provider("datagov")
    assert isinstance(dg, AgmarknetDataGovClient)
    mirror, _ = resolve_provider("mirror")
    assert isinstance(mirror, MandiMirrorClient)


# --- Price recommendation ---------------------------------------------------


def test_recommendation_median_math_and_benchmark():
    commodity_id = seed_commodity(name_en="Onion")
    day = date.today()
    _seed_observations(
        commodity_id,
        [
            {"market": "Mandvi A", "observed_on": day, "min_paise": 90_000, "modal_paise": 100_000, "max_paise": 120_000},
            {"market": "Mandvi B", "observed_on": day, "min_paise": 180_000, "modal_paise": 200_000, "max_paise": 220_000},
            {"market": "Mandvi C", "observed_on": day, "min_paise": 380_000, "modal_paise": 400_000, "max_paise": 420_000},
        ],
    )
    db = SessionLocal()
    try:
        rec = db.query(PriceRecommendation).first()  # none yet
        assert rec is None
        from app.ai.pricing import build_price_recommendation

        rec = build_price_recommendation(db, _uuid(commodity_id))
        # median of {100000, 200000, 400000} = 200000 — a quoted price.
        assert rec.recommended_modal_paise == 200_000
        assert rec.recommended_min_paise == 180_000
        assert rec.recommended_max_paise == 220_000
        # Benchmark market is the one quoting the recommended median.
        assert rec.benchmark_market == "Mandvi B (Belagavi)"
        assert rec.benchmark_observed_on == day
        assert rec.benchmark_source == PriceSourceType.AGMARKNET
        assert rec.confidence == RecommendationConfidence.LOW  # 3 markets < 4
        assert rec.explanation and "median" in rec.explanation
        run = db.get(ModelRun, rec.model_run_id)
        assert run.model_version == "stats-median-v1"
        assert run.metrics["n_observations_used"] == 3
        assert run.metrics["median_modal_paise"] == 200_000
        assert run.metrics["any_synthetic_inputs"] is False
    finally:
        db.close()


def test_recommendation_even_count_uses_lower_median_quoted_price():
    commodity_id = seed_commodity(name_en="Tomato")
    day = date.today()
    _seed_observations(
        commodity_id,
        [
            {"market": f"M{i}", "observed_on": day, "modal_paise": p}
            for i, p in enumerate([100_000, 200_000, 300_000, 400_000])
        ],
    )
    db = SessionLocal()
    try:
        from app.ai.pricing import build_price_recommendation

        rec = build_price_recommendation(db, _uuid(commodity_id))
        # lower median of an even set: 200000, which some market actually quoted
        # (never an interpolated average no market printed).
        assert rec.recommended_modal_paise == 200_000
        quoted = {100_000, 200_000, 300_000, 400_000}
        assert rec.recommended_modal_paise in quoted
    finally:
        db.close()


def test_recommendation_uses_latest_per_market_and_excludes_flagged():
    commodity_id = seed_commodity(name_en="Onion")
    today = date.today()
    old = today - timedelta(days=10)
    _seed_observations(
        commodity_id,
        [
            # older row for Mandvi A — must lose to the newer observation
            {"market": "Mandvi A", "observed_on": old, "modal_paise": 500_000},
            {"market": "Mandvi A", "observed_on": today, "modal_paise": 100_000},
            {"market": "Mandvi B", "observed_on": today, "modal_paise": 200_000},
            {"market": "Mandvi C", "observed_on": today, "modal_paise": 300_000},
            # flagged rows must be excluded entirely
            {"market": "Bad Mandi", "observed_on": today, "modal_paise": 9_000_000,
             "data_quality": DataQualityStatus.ANOMALOUS},
        ],
    )
    db = SessionLocal()
    try:
        from app.ai.pricing import build_price_recommendation

        rec = build_price_recommendation(db, _uuid(commodity_id))
        # valid pool after dedupe/latest = {100000, 200000, 300000}
        assert rec.recommended_modal_paise == 200_000
        run = db.get(ModelRun, rec.model_run_id)
        assert run.metrics["n_observations_used"] == 3
        assert run.metrics["n_excluded_anomalous"] == 1
    finally:
        db.close()


def test_recommendation_high_confidence_needs_many_fresh_real_markets():
    commodity_id = seed_commodity(name_en="Onion")
    day = date.today()
    _seed_observations(
        commodity_id,
        [
            {"market": f"M{i}", "observed_on": day, "modal_paise": 100_000 + i * 1_000}
            for i in range(8)
        ],
    )
    db = SessionLocal()
    try:
        from app.ai.pricing import build_price_recommendation

        rec = build_price_recommendation(db, _uuid(commodity_id))
        assert rec.confidence == RecommendationConfidence.HIGH
    finally:
        db.close()


def test_recommendation_synthetic_inputs_are_flagged_low_confidence():
    commodity_id = seed_commodity(name_en="Onion")
    day = date.today()
    _seed_observations(
        commodity_id,
        [
            {"market": f"S{i}", "observed_on": day, "modal_paise": 100_000 + i * 1_000,
             "is_synthetic": True, "source": PriceSourceType.SYNTHETIC}
            for i in range(10)
        ],
    )
    db = SessionLocal()
    try:
        from app.ai.pricing import build_price_recommendation

        rec = build_price_recommendation(db, _uuid(commodity_id))
        # Even with 10 markets, synthetic inputs cap confidence at LOW.
        assert rec.confidence == RecommendationConfidence.LOW
        assert "SYNTHETIC" in rec.explanation
        run = db.get(ModelRun, rec.model_run_id)
        assert run.metrics["any_synthetic_inputs"] is True
    finally:
        db.close()


def test_recommendation_insufficient_data_raises():
    commodity_id = seed_commodity(name_en="Onion")
    db = SessionLocal()
    try:
        from app.ai.pricing import build_price_recommendation
        from app.ai.pricing.service import InsufficientDataError

        with pytest.raises(InsufficientDataError):
            build_price_recommendation(db, _uuid(commodity_id))
    finally:
        db.close()


def test_recommendation_widens_district_and_says_so():
    commodity_id = seed_commodity(name_en="Onion")
    day = date.today()
    _seed_observations(
        commodity_id,
        [
            {"market": "Mandvi A", "district": "Belagavi", "observed_on": day, "modal_paise": 100_000},
            {"market": "Mandvi B", "district": "Mysuru", "observed_on": day, "modal_paise": 200_000},
        ],
    )
    db = SessionLocal()
    try:
        from app.ai.pricing import build_price_recommendation

        # No data for Hubballi -> widen to all districts, truthfully recorded.
        rec = build_price_recommendation(db, _uuid(commodity_id), district="Hubballi")
        assert rec.recommended_modal_paise == 100_000  # lower median of {100k, 200k}
        assert rec.district == "Hubballi"
        assert "across all districts" in rec.explanation
        run = db.get(ModelRun, rec.model_run_id)
        assert run.parameters["widened_to_all_districts"] is True
    finally:
        db.close()


# --- Demand forecasting -----------------------------------------------------


def _seed_daily_series(commodity_id, days, base_paise=200_000, amplitude=20_000,
                       is_synthetic=True, end=None):
    """Deterministic series with a weekly seasonal pattern, one market."""
    end = end or date.today()
    start = end - timedelta(days=days - 1)
    rows = []
    for i in range(days):
        day = start + timedelta(days=i)
        modal = base_paise + amplitude * ((i % 7) / 7.0)
        rows.append(
            {
                "market": "Seasonal APMC",
                "district": "Belagavi",
                "observed_on": day,
                "min_paise": int(modal * 0.95),
                "modal_paise": int(round(modal)),
                "max_paise": int(modal * 1.05),
                "arrival_qty": 100.0 + (i % 7) * 5.0,
                "is_synthetic": is_synthetic,
                "source": PriceSourceType.SYNTHETIC if is_synthetic else PriceSourceType.AGMARKNET,
            }
        )
    _seed_observations(commodity_id, rows)


def test_forecast_seasonal_naive_baseline_with_holdout_metrics():
    commodity_id = seed_commodity(name_en="Onion")
    _seed_daily_series(commodity_id, days=30, is_synthetic=True)  # 30 < 42 real days
    db = SessionLocal()
    try:
        from app.ai.forecasting import build_demand_forecast
        from app.ai.forecasting.service import MIN_REAL_DAYS_FOR_LGBM

        out = build_demand_forecast(db, _uuid(commodity_id), horizon_days=7)
        assert len(out) == 7
        expected_days = {date.today() + timedelta(days=i) for i in range(1, 8)}
        assert {f.forecast_for for f in out} == expected_days

        run = db.get(ModelRun, out[0].model_run_id)
        assert run.model_version == "seasonal-naive-v1"
        # Honest holdout metrics exist (30 days >= 14 + 7 holdout threshold).
        assert run.metrics["holdout_days"] == 7
        assert run.metrics["baseline_seasonal_naive_mae_paise"] is not None
        assert run.metrics["baseline_seasonal_naive_mape_pct"] is not None
        # LightGBM was skipped — not enough REAL history — and the run says so.
        assert run.metrics["lightgbm_mae_paise"] is None
        assert run.metrics["chosen_model"] == "seasonal_naive"
        assert f"only 0 real observation days" in run.notes
        assert str(MIN_REAL_DAYS_FOR_LGBM) in run.notes
        assert "SYNTHETIC" in run.notes
        # Forecast rows carry the synthetic label and the provenance link.
        for f in out:
            assert f.is_synthetic is True
            assert f.model_run_id == run.id
            assert f.predicted_price_paise is not None
            assert f.lower_bound_paise <= f.predicted_price_paise <= f.upper_bound_paise
    finally:
        db.close()


def test_forecast_trains_lightgbm_on_enough_real_history():
    commodity_id = seed_commodity(name_en="Onion")
    _seed_daily_series(commodity_id, days=60, is_synthetic=False)
    db = SessionLocal()
    try:
        from app.ai.forecasting import build_demand_forecast
        from app.ai.forecasting.service import MIN_REAL_DAYS_FOR_LGBM

        out = build_demand_forecast(db, _uuid(commodity_id), horizon_days=7)
        assert len(out) == 7
        run = db.get(ModelRun, out[0].model_run_id)
        m = run.metrics
        assert m["n_real_days"] == 60 >= MIN_REAL_DAYS_FOR_LGBM
        # Both models were evaluated on the real holdout; neither metric is invented.
        assert m["baseline_seasonal_naive_mae_paise"] is not None
        assert m["lightgbm_mae_paise"] is not None
        # The published model_version matches whichever model actually won.
        if m["chosen_model"] == "lightgbm":
            assert run.model_version == "lightgbm-panel-v1"
            assert m["lightgbm_mae_paise"] < m["baseline_seasonal_naive_mae_paise"]
        else:
            assert run.model_version == "seasonal-naive-v1"
        assert out[0].is_synthetic is False
        # Training window provenance matches the seeded history.
        assert run.trained_on_to == date.today()
    finally:
        db.close()


def test_forecast_insufficient_data_raises():
    commodity_id = seed_commodity(name_en="Onion")
    _seed_daily_series(commodity_id, days=5, is_synthetic=True)
    db = SessionLocal()
    try:
        from app.ai.forecasting import build_demand_forecast
        from app.ai.forecasting.service import InsufficientDataError

        with pytest.raises(InsufficientDataError):
            build_demand_forecast(db, _uuid(commodity_id), horizon_days=7)
    finally:
        db.close()


# --- API endpoints ----------------------------------------------------------


def test_api_recommendation_endpoint_full_provenance(client):
    commodity_id = seed_commodity(name_en="Onion")
    day = date.today()
    _seed_observations(
        commodity_id,
        [
            {"market": f"M{i}", "observed_on": day, "modal_paise": 100_000 + i * 1_000}
            for i in range(8)
        ],
    )
    auth = register_user(client, phone="9810000001", name="Rec Buyer", role="buyer")
    r = client.get(
        f"/api/v1/market-prices/recommendation?commodity_id={commodity_id}",
        headers=auth["headers"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["commodity_name"] == "Onion"
    assert body["recommended_modal_paise"] == 103_000  # lower median of 8 markets
    assert body["benchmark_market"] and "M3" in body["benchmark_market"]
    assert body["benchmark_observed_on"] == day.isoformat()
    assert body["confidence"] == "high"
    assert "median" in body["explanation"]
    run = body["model_run"]
    assert run["model_version"] == "stats-median-v1"
    assert run["model_type"] == "price_recommendation"
    assert run["metrics"]["n_observations_used"] == 8
    assert run["ran_at"]

    # Recommendation is persisted for auditability.
    db = SessionLocal()
    try:
        assert db.query(PriceRecommendation).count() == 1
    finally:
        db.close()


def test_api_recommendation_unknown_commodity_is_404(client):
    auth = register_user(client, phone="9810000002", name="404 Buyer", role="buyer")
    r = client.get(
        "/api/v1/market-prices/recommendation?commodity_id=00000000-0000-0000-0000-000000000000",
        headers=auth["headers"],
    )
    assert r.status_code == 404


def test_api_recommendation_requires_auth(client):
    commodity_id = seed_commodity(name_en="Onion")
    r = client.get(f"/api/v1/market-prices/recommendation?commodity_id={commodity_id}")
    assert r.status_code == 401


def test_api_forecasts_endpoint_builds_and_returns_provenance(client):
    commodity_id = seed_commodity(name_en="Onion")
    _seed_daily_series(commodity_id, days=30, is_synthetic=True)
    auth = register_user(client, phone="9810000003", name="Fc Buyer", role="buyer")
    r = client.get(
        f"/api/v1/forecasts?commodity_id={commodity_id}&horizon_days=7",
        headers=auth["headers"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) == 7
    first = body[0]
    assert first["commodity_name"] == "Onion"
    assert first["is_synthetic"] is True
    assert first["predicted_price_paise"] is not None
    assert first["unit"] == "quintal"
    assert first["model_run"]["model_type"] == "demand_forecast"
    assert first["model_run"]["metrics"]["baseline_seasonal_naive_mae_paise"] is not None
    assert "SYNTHETIC" in first["planning_notes"]
    # Second call must serve the stored forecasts, not recompute (same run id).
    r2 = client.get(
        f"/api/v1/forecasts?commodity_id={commodity_id}", headers=auth["headers"]
    )
    assert r2.status_code == 200
    assert r2.json()[0]["model_run"]["id"] == first["model_run"]["id"]
    db = SessionLocal()
    try:
        assert db.query(DemandForecast).count() == 7
    finally:
        db.close()


def test_api_forecasts_insufficient_data_is_404(client):
    commodity_id = seed_commodity(name_en="Onion")
    _seed_daily_series(commodity_id, days=3, is_synthetic=True)
    auth = register_user(client, phone="9810000004", name="Fc404 Buyer", role="buyer")
    r = client.get(
        f"/api/v1/forecasts?commodity_id={commodity_id}", headers=auth["headers"]
    )
    assert r.status_code == 404


def test_api_forecasts_requires_auth(client):
    r = client.get("/api/v1/forecasts")
    assert r.status_code == 401
