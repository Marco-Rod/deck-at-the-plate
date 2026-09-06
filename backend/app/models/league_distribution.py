"""Distribuciones versionadas de métricas de liga para normalizar ratings."""

import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    text,
)

from app.core.time import utcnow
from app.database import Base


def _new_id() -> str:
    return str(uuid.uuid4())


class LeagueMetricDistribution(Base):
    """Resumen reproducible de una métrica para una población elegible."""

    __tablename__ = "league_metric_distributions"
    __table_args__ = (
        Index(
            "uq_league_metric_distributions_identity",
            "season",
            "role",
            "metric",
            "distribution_version",
            "data_start_date",
            "data_end_date",
            text("COALESCE(pitch_type, '')"),
            text("COALESCE(pitch_family, '')"),
            unique=True,
        ),
        CheckConstraint("season >= 1900 AND season <= 2100", name="ck_league_metric_distributions_season"),
        CheckConstraint("population_size > 0", name="ck_league_metric_distributions_population"),
        CheckConstraint("sample_size_total >= population_size", name="ck_league_metric_distributions_sample"),
        CheckConstraint("data_end_date >= data_start_date", name="ck_league_metric_distributions_window"),
        CheckConstraint(
            "minimum <= p05 AND p05 <= p10 AND p10 <= p25 AND p25 <= p50 "
            "AND p50 <= p75 AND p75 <= p90 AND p90 <= p95 AND p95 <= maximum",
            name="ck_league_metric_distributions_percentiles",
        ),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    season = Column(SmallInteger, nullable=False, index=True)
    role = Column(String(20), nullable=False, index=True)
    metric = Column(String(64), nullable=False, index=True)
    pitch_type = Column(String(12), nullable=True, index=True)
    pitch_family = Column(String(20), nullable=True, index=True)
    population_size = Column(Integer, nullable=False)
    sample_size_total = Column(Integer, nullable=False)
    population_mean = Column(Numeric(12, 8), nullable=False)
    league_baseline = Column(Numeric(12, 8), nullable=False)
    median = Column(Numeric(12, 8), nullable=False)
    stddev = Column(Numeric(12, 8), nullable=False)
    p05 = Column(Numeric(12, 8), nullable=False)
    p10 = Column(Numeric(12, 8), nullable=False)
    p25 = Column(Numeric(12, 8), nullable=False)
    p50 = Column(Numeric(12, 8), nullable=False)
    p75 = Column(Numeric(12, 8), nullable=False)
    p90 = Column(Numeric(12, 8), nullable=False)
    p95 = Column(Numeric(12, 8), nullable=False)
    minimum = Column(Numeric(12, 8), nullable=False)
    maximum = Column(Numeric(12, 8), nullable=False)
    distribution_version = Column(String(40), nullable=False, index=True)
    data_start_date = Column(Date, nullable=False)
    data_end_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
