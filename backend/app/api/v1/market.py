"""Market-data + AI endpoints: price recommendation and demand forecasts.

Both endpoints return full model provenance (version, metrics, run time) so
no AI output is ever opaque.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.forecasting import build_demand_forecast
from app.ai.forecasting.service import InsufficientDataError as ForecastNoData
from app.ai.pricing import build_price_recommendation
from app.ai.pricing.service import InsufficientDataError as PriceNoData
from app.core.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.catalog import Commodity
from app.models.market import DemandForecast, ModelRun, PriceRecommendation
from app.models.user import User

router = APIRouter(prefix="/market-prices", tags=["market-data"])
forecasts_router = APIRouter(prefix="/forecasts", tags=["forecasting"])


class ModelRunOut(BaseModel):
    id: str
    model_type: str
    model_version: str
    ran_at: datetime
    trained_on_from: str | None
    trained_on_to: str | None
    metrics: dict | None
    parameters: dict | None
    notes: str | None


class RecommendationOut(BaseModel):
    id: str
    commodity_id: str
    commodity_name: str
    district: str | None
    recommended_min_paise: int | None
    recommended_modal_paise: int
    recommended_max_paise: int | None
    recommended_modal_per_kg_paise: int | None
    unit: str | None
    benchmark_market: str | None
    benchmark_observed_on: str | None
    benchmark_source: str | None
    confidence: str
    explanation: str | None
    model_run: ModelRunOut


def _run_out(run: ModelRun) -> ModelRunOut:
    return ModelRunOut(
        id=str(run.id),
        model_type=run.model_type.value,
        model_version=run.model_version,
        ran_at=run.ran_at,
        trained_on_from=run.trained_on_from.isoformat() if run.trained_on_from else None,
        trained_on_to=run.trained_on_to.isoformat() if run.trained_on_to else None,
        metrics=run.metrics,
        parameters=run.parameters,
        notes=run.notes,
    )


@router.get("/recommendation", response_model=RecommendationOut)
def get_price_recommendation(
    commodity_id: UUID = Query(..., description="Commodity UUID"),
    district: str | None = Query(None, description="Optional district filter"),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Transparent median-based price recommendation with benchmark market,
    observation date, confidence and a human explanation."""
    try:
        rec = build_price_recommendation(db, commodity_id, district=district)
    except PriceNoData as exc:
        raise NotFoundError(str(exc)) from exc
    run = db.get(ModelRun, rec.model_run_id)
    commodity = db.get(Commodity, rec.commodity_id)
    per_kg = (
        rec.recommended_modal_paise // 100 if rec.unit and rec.unit.value == "quintal" else None
    )
    return RecommendationOut(
        id=str(rec.id),
        commodity_id=str(rec.commodity_id),
        commodity_name=commodity.name_en if commodity else "",
        district=rec.district,
        recommended_min_paise=rec.recommended_min_paise,
        recommended_modal_paise=rec.recommended_modal_paise,
        recommended_max_paise=rec.recommended_max_paise,
        recommended_modal_per_kg_paise=per_kg,
        unit=rec.unit.value if rec.unit else None,
        benchmark_market=rec.benchmark_market,
        benchmark_observed_on=(
            rec.benchmark_observed_on.isoformat() if rec.benchmark_observed_on else None
        ),
        benchmark_source=rec.benchmark_source.value if rec.benchmark_source else None,
        confidence=rec.confidence.value,
        explanation=rec.explanation,
        model_run=_run_out(run),
    )


class ForecastOut(BaseModel):
    id: str
    commodity_id: str
    commodity_name: str
    district: str | None
    forecast_for: str
    horizon_days: int
    predicted_price_paise: int | None
    lower_bound_paise: int | None
    upper_bound_paise: int | None
    predicted_demand_qty: float | None
    unit: str | None
    trend: str | None
    is_synthetic: bool
    planning_notes: str | None
    model_run: ModelRunOut


@forecasts_router.get("", response_model=list[ForecastOut])
def get_forecasts(
    commodity_id: UUID | None = Query(None, description="Commodity UUID"),
    district: str | None = Query(None, description="Optional district filter"),
    horizon_days: int = Query(7, ge=1, le=30),
    build_if_missing: bool = Query(
        True, description="Compute a fresh forecast synchronously when none is stored"
    ),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Latest stored demand/price forecast per commodity (+ provenance)."""
    pairs = _load_latest_forecasts(db, commodity_id, district)
    if not pairs and build_if_missing and commodity_id is not None:
        try:
            build_demand_forecast(
                db, commodity_id, district=district, horizon_days=horizon_days
            )
        except ForecastNoData as exc:
            raise NotFoundError(str(exc)) from exc
        pairs = _load_latest_forecasts(db, commodity_id, district)
    if not pairs:
        raise NotFoundError(
            "no forecasts stored for these filters "
            "(pass a commodity_id and build_if_missing=true to compute one)"
        )

    out = []
    for fc, run in pairs:
        commodity = db.get(Commodity, fc.commodity_id)
        out.append(
            ForecastOut(
                id=str(fc.id),
                commodity_id=str(fc.commodity_id),
                commodity_name=commodity.name_en if commodity else "",
                district=fc.district,
                forecast_for=fc.forecast_for.isoformat(),
                horizon_days=fc.horizon_days,
                predicted_price_paise=fc.predicted_price_paise,
                lower_bound_paise=fc.lower_bound_paise,
                upper_bound_paise=fc.upper_bound_paise,
                predicted_demand_qty=fc.predicted_demand_qty,
                unit=fc.unit.value if fc.unit else None,
                trend=fc.trend,
                is_synthetic=fc.is_synthetic,
                planning_notes=fc.planning_notes,
                model_run=_run_out(run),
            )
        )
    return out


def _load_latest_forecasts(
    db: Session, commodity_id: UUID | None, district: str | None
) -> list[tuple[DemandForecast, ModelRun]]:
    """Rows of the most recent run per (commodity, district)."""
    q = (
        select(DemandForecast, ModelRun)
        .join(ModelRun, DemandForecast.model_run_id == ModelRun.id)
    )
    if commodity_id is not None:
        q = q.where(DemandForecast.commodity_id == commodity_id)
    if district:
        q = q.where(DemandForecast.district == district)
    rows = db.execute(q).all()

    latest: dict[tuple, tuple[DemandForecast, ModelRun]] = {}
    for fc, run in rows:
        key = (str(fc.commodity_id), fc.district or "")
        current = latest.get(key)
        if current is None or run.ran_at > current[1].ran_at:
            latest[key] = (fc, run)
    latest_run_ids = {run.id for _fc, run in latest.values()}
    return sorted(
        [(fc, run) for fc, run in rows if run.id in latest_run_ids],
        key=lambda p: (p[1].ran_at, p[0].forecast_for),
    )
