"""Market price observations, recommendations, forecasts and model provenance."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    func,
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base
from app.models.enums import (
    DataQualityStatus,
    ImportJobStatus,
    ModelType,
    PriceSourceType,
    RecommendationConfidence,
    UnitEnum,
)


def _enum(e, name: str):
    return Enum(e, name=name, native_enum=False)


class MarketPriceObservation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One row per commodity/market/day from an authorised source.

    Original source values are preserved in raw_payload for auditability;
    the typed columns hold the cleaned values.
    """

    __tablename__ = "market_price_observations"
    __table_args__ = (
        Index(
            "ix_mpo_commodity_district_date",
            "commodity_id",
            "district",
            "observed_on",
        ),
    )

    commodity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("commodities.id"), index=True
    )
    market_name: Mapped[str] = mapped_column(String(160))
    district: Mapped[str] = mapped_column(String(120), index=True)
    state: Mapped[str] = mapped_column(String(120))
    observed_on: Mapped[date] = mapped_column(Date)

    min_price_paise: Mapped[int | None] = mapped_column(Integer)
    modal_price_paise: Mapped[int | None] = mapped_column(Integer)
    max_price_paise: Mapped[int | None] = mapped_column(Integer)
    unit: Mapped[UnitEnum | None] = mapped_column(_enum(UnitEnum, "unit_enum"))
    arrival_quantity: Mapped[float | None] = mapped_column(Float)

    source: Mapped[PriceSourceType] = mapped_column(
        _enum(PriceSourceType, "price_source_type"),
        default=PriceSourceType.AGMARKNET,
    )
    source_ref: Mapped[str | None] = mapped_column(String(200))
    data_quality: Mapped[DataQualityStatus] = mapped_column(
        _enum(DataQualityStatus, "data_quality_status"),
        default=DataQualityStatus.VALID,
        index=True,
    )
    raw_payload: Mapped[dict | None] = mapped_column(JSON)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Synthetic seed rows are always distinguishable from official data.
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)

    commodity = relationship("Commodity")


class ModelRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Provenance for every AI/ML output: version, training window, metrics."""

    __tablename__ = "model_runs"

    model_type: Mapped[ModelType] = mapped_column(
        _enum(ModelType, "model_type"), index=True
    )
    model_version: Mapped[str] = mapped_column(String(40))
    trained_on_from: Mapped[date | None] = mapped_column(Date)
    trained_on_to: Mapped[date | None] = mapped_column(Date)
    training_data_description: Mapped[str | None] = mapped_column(Text)
    metrics: Mapped[dict | None] = mapped_column(JSON)
    parameters: Mapped[dict | None] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(Text)
    ran_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PriceRecommendation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "price_recommendations"

    listing_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("produce_listings.id"), index=True
    )
    commodity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("commodities.id"), index=True
    )
    district: Mapped[str | None] = mapped_column(String(120), index=True)

    recommended_min_paise: Mapped[int | None] = mapped_column(Integer)
    recommended_modal_paise: Mapped[int | None] = mapped_column(Integer)
    recommended_max_paise: Mapped[int | None] = mapped_column(Integer)
    unit: Mapped[UnitEnum | None] = mapped_column(_enum(UnitEnum, "unit_enum"))

    benchmark_market: Mapped[str | None] = mapped_column(String(160))
    benchmark_observed_on: Mapped[date | None] = mapped_column(Date)
    benchmark_source: Mapped[PriceSourceType | None] = mapped_column(
        _enum(PriceSourceType, "price_source_type")
    )
    confidence: Mapped[RecommendationConfidence] = mapped_column(
        _enum(RecommendationConfidence, "recommendation_confidence"),
        default=RecommendationConfidence.LOW,
    )
    explanation: Mapped[str | None] = mapped_column(Text)
    model_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("model_runs.id"), index=True
    )


class DemandForecast(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "demand_forecasts"

    commodity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("commodities.id"), index=True
    )
    district: Mapped[str | None] = mapped_column(String(120), index=True)
    forecast_for: Mapped[date] = mapped_column(Date, index=True)
    horizon_days: Mapped[int] = mapped_column(Integer, default=7)

    predicted_demand_qty: Mapped[float | None] = mapped_column(Float)
    predicted_price_paise: Mapped[int | None] = mapped_column(Integer)
    lower_bound_paise: Mapped[int | None] = mapped_column(Integer)
    upper_bound_paise: Mapped[int | None] = mapped_column(Integer)
    unit: Mapped[UnitEnum | None] = mapped_column(_enum(UnitEnum, "unit_enum"))

    trend: Mapped[str | None] = mapped_column(String(20))  # rising/falling/stable
    planning_notes: Mapped[str | None] = mapped_column(Text)
    model_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("model_runs.id"), index=True
    )
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)


class DataImportJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "data_import_jobs"

    source: Mapped[PriceSourceType] = mapped_column(
        _enum(PriceSourceType, "price_source_type")
    )
    status: Mapped[ImportJobStatus] = mapped_column(
        _enum(ImportJobStatus, "import_job_status"),
        default=ImportJobStatus.RUNNING,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    records_read: Mapped[int] = mapped_column(Integer, default=0)
    records_written: Mapped[int] = mapped_column(Integer, default=0)
    records_rejected: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
