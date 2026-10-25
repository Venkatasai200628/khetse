"""Demand/price forecasting: seasonal-naive baseline, LightGBM when earned.

Honesty rules baked into this module:
- The baseline is always seasonal-naive (last week's value), and its error is
  measured on a real holdout — never invented.
- LightGBM is only trained when there is enough REAL history
  (>= ``MIN_REAL_DAYS_FOR_LGBM`` distinct days of non-synthetic observations);
  otherwise it is skipped and the skip reason is recorded in ModelRun.notes.
- Whichever model has the lower holdout MAE produces the published forecast;
  both models' metrics are persisted on the ModelRun row.
"""

from __future__ import annotations

import logging
import statistics
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import Commodity
from app.models.enums import DataQualityStatus, ModelType, UnitEnum
from app.models.market import DemandForecast, MarketPriceObservation, ModelRun

logger = logging.getLogger("khetse.forecasting")

BASELINE_VERSION = "seasonal-naive-v1"
LGBM_VERSION = "lightgbm-panel-v1"

SEASONALITY_DAYS = 7
HOLDOUT_DAYS = 7
MIN_SERIES_DAYS_FOR_METRICS = 14  # below this, metrics are not computed
MIN_REAL_DAYS_FOR_LGBM = 42  # distinct real (non-synthetic) observation days
TREND_WINDOW_DAYS = 14
TREND_PCT_PER_DAY_THRESHOLD = 0.3  # %/day; smaller slopes count as "stable"

SEASONAL_NAIVE_FEATURES = ["lag_1", "lag_7", "roll_mean_7", "roll_std_7", "dow", "month"]


class InsufficientDataError(Exception):
    """Not enough observations to forecast."""


def _daily_series(
    session: Session,
    commodity_id,
    district: str | None,
    as_of: date,
) -> pd.DataFrame:
    """One row per observed day: median modal price and median arrival across
    the day's valid observations."""
    q = select(MarketPriceObservation).where(
        MarketPriceObservation.commodity_id == commodity_id,
        MarketPriceObservation.observed_on <= as_of,
        MarketPriceObservation.data_quality == DataQualityStatus.VALID,
    )
    if district:
        q = q.where(MarketPriceObservation.district == district)
    rows = list(session.scalars(q))
    if not rows:
        return pd.DataFrame(columns=["observed_on", "modal_paise", "arrival_qty"])

    by_day: dict[date, list[MarketPriceObservation]] = {}
    for r in rows:
        by_day.setdefault(r.observed_on, []).append(r)
    records = []
    for day in sorted(by_day):
        day_rows = by_day[day]
        modals = [r.modal_price_paise for r in day_rows if r.modal_price_paise is not None]
        arrivals = [
            r.arrival_quantity for r in day_rows if r.arrival_quantity is not None
        ]
        records.append(
            {
                "observed_on": day,
                "modal_paise": float(statistics.median(modals)) if modals else np.nan,
                "arrival_qty": float(statistics.median(arrivals)) if arrivals else np.nan,
                "n_observations": len(day_rows),
                "any_synthetic": any(r.is_synthetic for r in day_rows),
            }
        )
    return pd.DataFrame.from_records(records)


def _seasonal_naive_predict(series: pd.Series, steps: int) -> list[float]:
    """Value from 7 days earlier; fall back to the last seen value."""
    values = [float(v) for v in series.tolist()]
    out: list[float] = []
    for _ in range(steps):
        if len(values) >= SEASONALITY_DAYS + 1:
            out.append(values[-SEASONALITY_DAYS])
        elif values:
            out.append(values[-1])
        else:
            raise InsufficientDataError("empty series")
        values.append(out[-1])
    return out


def _add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("observed_on").reset_index(drop=True).copy()
    df["lag_1"] = df["modal_paise"].shift(1)
    df["lag_7"] = df["modal_paise"].shift(SEASONALITY_DAYS)
    df["roll_mean_7"] = df["modal_paise"].shift(1).rolling(7).mean()
    df["roll_std_7"] = df["modal_paise"].shift(1).rolling(7).std()
    df["dow"] = df["observed_on"].map(lambda d: d.weekday())
    df["month"] = df["observed_on"].map(lambda d: d.month)
    return df


def _trend(series: pd.Series, days: list[date]) -> str:
    tail_y = series.tail(TREND_WINDOW_DAYS).astype(float).tolist()
    if len(tail_y) < 3:
        return "stable"
    x = np.arange(len(tail_y), dtype=float)
    slope = float(np.polyfit(x, tail_y, 1)[0])
    mean_level = float(np.mean(tail_y)) or 1.0
    pct_per_day = abs(slope) / mean_level * 100.0
    if pct_per_day < TREND_PCT_PER_DAY_THRESHOLD:
        return "stable"
    return "rising" if slope > 0 else "falling"


def build_demand_forecast(
    session: Session,
    commodity_id,
    district: str | None = None,
    horizon_days: int = 7,
    as_of: date | None = None,
) -> list[DemandForecast]:
    """Compute and persist ``horizon_days`` DemandForecast rows + ModelRun."""
    as_of = as_of or date.today()
    commodity = session.get(Commodity, commodity_id)
    if commodity is None:
        raise InsufficientDataError("commodity not found")

    df = _daily_series(session, commodity_id, district, as_of)
    # Real (non-synthetic) days decide LightGBM eligibility.
    real_mask = ~df["any_synthetic"] if not df.empty else pd.Series(dtype=bool)
    n_real_days = int(real_mask.sum()) if not df.empty else 0
    df = df.dropna(subset=["modal_paise"])
    if len(df) < SEASONALITY_DAYS + 1:
        raise InsufficientDataError(
            f"only {len(df)} usable observation days; need at least "
            f"{SEASONALITY_DAYS + 1}"
        )
    all_synthetic = bool(df["any_synthetic"].all())
    series = df["modal_paise"]
    days = df["observed_on"].tolist()

    # --- Holdout evaluation (honest metrics; skipped if series too short) ---
    can_evaluate = len(df) >= MIN_SERIES_DAYS_FOR_METRICS + HOLDOUT_DAYS
    baseline_mae = baseline_mape = None
    lgbm_mae = lgbm_mape = None
    chosen_model = "seasonal_naive"
    chosen_version = BASELINE_VERSION
    if can_evaluate:
        train, holdout = df.iloc[:-HOLDOUT_DAYS], df.iloc[-HOLDOUT_DAYS:]
        # Baseline: seasonal-naive walked over the holdout.
        preds = _seasonal_naive_predict(train["modal_paise"], HOLDOUT_DAYS)
        actual = holdout["modal_paise"].to_numpy(dtype=float)
        errors = np.abs(np.array(preds) - actual)
        baseline_mae = float(np.mean(errors))
        nonzero = actual != 0
        baseline_mape = (
            float(np.mean(errors[nonzero] / np.abs(actual[nonzero])) * 100.0)
            if nonzero.any()
            else None
        )

        # LightGBM only on enough REAL history.
        if n_real_days >= MIN_REAL_DAYS_FOR_LGBM:
            try:
                from lightgbm import LGBMRegressor
                from sklearn.metrics import mean_absolute_error

                feats = _add_features(df).dropna(
                    subset=["lag_7", "roll_mean_7", "roll_std_7"]
                )
                split_day = holdout["observed_on"].iloc[0]
                tr = feats[feats["observed_on"] < split_day]
                ho = feats[feats["observed_on"] >= split_day]
                model = LGBMRegressor(
                    n_estimators=200,
                    learning_rate=0.05,
                    num_leaves=7,
                    min_child_samples=5,
                    random_state=42,
                    verbose=-1,
                )
                model.fit(tr[SEASONAL_NAIVE_FEATURES], tr["modal_paise"])
                ho_preds = model.predict(ho[SEASONAL_NAIVE_FEATURES])
                lgbm_mae = float(
                    mean_absolute_error(ho["modal_paise"], ho_preds)
                )
                nz = ho["modal_paise"].to_numpy(dtype=float) != 0
                lgbm_mape = (
                    float(
                        np.mean(
                            np.abs(
                                ho_preds[nz]
                                - ho["modal_paise"].to_numpy(dtype=float)[nz]
                            )
                            / np.abs(ho["modal_paise"].to_numpy(dtype=float)[nz]
                            )
                        )
                        * 100.0
                    )
                    if nz.any()
                    else None
                )
                if lgbm_mae < baseline_mae:
                    chosen_model = "lightgbm"
                    chosen_version = LGBM_VERSION
            except Exception as exc:  # noqa: BLE001 — degrade to baseline
                logger.warning("LightGBM training failed: %s", exc)
                lgbm_mae = lgbm_mape = None

    # --- Produce the horizon forecast with the chosen model ---
    if chosen_model == "lightgbm":
        from lightgbm import LGBMRegressor

        model_full = LGBMRegressor(
            n_estimators=200,
            learning_rate=0.05,
            num_leaves=7,
            min_child_samples=5,
            random_state=42,
            verbose=-1,
        )
        feats = _add_features(df).dropna(subset=["lag_7", "roll_mean_7", "roll_std_7"])
        model_full.fit(feats[SEASONAL_NAIVE_FEATURES], feats["modal_paise"])
        future_dates: list[date] = [
            as_of + timedelta(days=i) for i in range(1, horizon_days + 1)
        ]
        hist = feats[["observed_on", "modal_paise"]].copy()
        preds: list[float] = []
        for fd in future_dates:
            lag1 = hist["modal_paise"].iloc[-1]
            lag7 = hist["modal_paise"].iloc[-SEASONALITY_DAYS]
            roll = hist["modal_paise"].tail(7)
            row = pd.DataFrame(
                [
                    {
                        "lag_1": lag1,
                        "lag_7": lag7,
                        "roll_mean_7": roll.mean(),
                        "roll_std_7": roll.std(ddof=1),
                        "dow": fd.weekday(),
                        "month": fd.month,
                    }
                ]
            )
            p = float(model_full.predict(row[SEASONAL_NAIVE_FEATURES])[0])
            preds.append(p)
            hist = pd.concat(
                [hist, pd.DataFrame([{"observed_on": fd, "modal_paise": p}])],
                ignore_index=True,
            )
    else:
        future_dates = [as_of + timedelta(days=i) for i in range(1, horizon_days + 1)]
        preds = _seasonal_naive_predict(series, horizon_days)

    # Uncertainty band: +/- 1 std of in-sample residuals of the chosen model.
    if chosen_model == "seasonal_naive" and len(df) > SEASONALITY_DAYS:
        fitted = series.shift(SEASONALITY_DAYS)
        residuals = (series - fitted).dropna()
        sigma = float(residuals.std(ddof=1)) if len(residuals) > 1 else 0.0
    elif chosen_model == "lightgbm":
        resid = feats["modal_paise"] - model_full.predict(
            feats[SEASONAL_NAIVE_FEATURES]
        )
        sigma = float(resid.std(ddof=1)) if len(resid) > 1 else 0.0
    else:
        sigma = 0.0

    # Demand quantity: seasonal-naive on arrivals when the source reports any.
    demand_preds: list[float | None] = []
    if df["arrival_qty"].notna().any():
        demand_preds = _seasonal_naive_predict(df["arrival_qty"], horizon_days)
    else:
        demand_preds = [None] * horizon_days

    trend = _trend(series, days)
    run = ModelRun(
        model_type=ModelType.DEMAND_FORECAST,
        model_version=chosen_version,
        trained_on_from=min(days),
        trained_on_to=max(days),
        training_data_description=(
            f"{len(df)} daily observations (median across markets), "
            f"{n_real_days} real (non-synthetic) days; district={district or 'all'}"
        ),
        metrics={
            k: v
            for k, v in {
                "baseline_seasonal_naive_mae_paise": baseline_mae,
                "baseline_seasonal_naive_mape_pct": baseline_mape,
                "lightgbm_mae_paise": lgbm_mae,
                "lightgbm_mape_pct": lgbm_mape,
                "holdout_days": HOLDOUT_DAYS if can_evaluate else 0,
                "n_train_days": int(len(df) - HOLDOUT_DAYS) if can_evaluate else len(df),
                "n_real_days": n_real_days,
                "chosen_model": chosen_model,
            }.items()
        },
        parameters={
            "seasonality_days": SEASONALITY_DAYS,
            "horizon_days": horizon_days,
            "uncertainty": "+/- 1 std of in-sample residuals",
            "features": SEASONAL_NAIVE_FEATURES,
            "min_real_days_for_lightgbm": MIN_REAL_DAYS_FOR_LGBM,
            "district": district,
        },
        notes=(
            (
                f"LightGBM skipped: only {n_real_days} real observation days "
                f"available (minimum {MIN_REAL_DAYS_FOR_LGBM})."
            )
            if lgbm_mae is None and n_real_days < MIN_REAL_DAYS_FOR_LGBM
            else (
                "LightGBM trained on real history; model with the lower "
                "holdout MAE was published."
                if lgbm_mae is not None
                else (
                    "LightGBM training failed; seasonal-naive published. "
                    "Baseline metrics above are holdout-measured."
                    if can_evaluate
                    else f"Holdout metrics not computed (series shorter than {MIN_SERIES_DAYS_FOR_METRICS + HOLDOUT_DAYS} days)."
                )
            )
        )
        + (" ALL inputs are SYNTHETIC (mock) data." if all_synthetic else ""),
        ran_at=datetime.now(tz=timezone.utc),
    )
    session.add(run)
    session.flush()

    unit = (
        session.scalar(
            select(MarketPriceObservation.unit).where(
                MarketPriceObservation.commodity_id == commodity_id
            )
        )
        or UnitEnum.QUINTAL
    )

    def _fmt_mae(value: float | None) -> str:
        return f"{value:.0f} paise" if value is not None else "not computed"

    base_note = (
        f"{chosen_model} forecast (baseline seasonal-naive MAE "
        f"{_fmt_mae(baseline_mae)} on a {HOLDOUT_DAYS if can_evaluate else 0}-day "
        f"holdout"
        + (f"; LightGBM MAE {_fmt_mae(lgbm_mae)}" if lgbm_mae is not None else "")
        + ")"
    )
    demand_note = (
        "; demand qty n/a — this source reports no arrival quantities"
        if all(d is None for d in demand_preds)
        else ""
    )

    out: list[DemandForecast] = []
    for fd, price_pred, demand_pred in zip(future_dates, preds, demand_preds):
        row = DemandForecast(
            commodity_id=commodity_id,
            district=district,
            forecast_for=fd,
            horizon_days=horizon_days,
            predicted_demand_qty=round(demand_pred, 1) if demand_pred else None,
            predicted_price_paise=int(round(price_pred)),
            lower_bound_paise=int(round(price_pred - sigma)),
            upper_bound_paise=int(round(price_pred + sigma)),
            unit=unit,
            trend=trend,
            planning_notes=base_note + demand_note +
            (" [SYNTHETIC INPUT DATA]" if all_synthetic else ""),
            model_run_id=run.id,
            is_synthetic=all_synthetic,
        )
        session.add(row)
        out.append(row)
    session.commit()
    return out
