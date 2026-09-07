"""Distribuciones de la población resultante de ratings oficiales."""

import uuid

from sqlalchemy import CheckConstraint, Column, Date, DateTime, Index, Integer, JSON, Numeric, SmallInteger, String

from app.core.time import utcnow
from app.database import Base


def _new_id() -> str:
    return str(uuid.uuid4())


class RatingDistribution(Base):
    """Resumen de ratings comparables para calcular tiers de performance."""

    __tablename__ = "rating_distributions"
    __table_args__ = (
        Index(
            "uq_rating_distributions_identity",
            "season",
            "role",
            "metric",
            "rating_model_version",
            "source_distribution_version",
            "rarity_model_version",
            "data_start_date",
            "data_end_date",
            unique=True,
        ),
        CheckConstraint("season >= 1900 AND season <= 2100", name="ck_rating_distributions_season"),
        CheckConstraint("role IN ('BATTER', 'PITCHER')", name="ck_rating_distributions_role"),
        CheckConstraint("population_size > 0", name="ck_rating_distributions_population"),
        CheckConstraint("data_end_date >= data_start_date", name="ck_rating_distributions_window"),
        CheckConstraint(
            "minimum <= p05 AND p05 <= p10 AND p10 <= p25 AND p25 <= p50 "
            "AND p50 <= p75 AND p75 <= p90 AND p90 <= p95 AND p95 <= maximum",
            name="ck_rating_distributions_percentiles",
        ),
        CheckConstraint("minimum >= 40 AND maximum <= 99", name="ck_rating_distributions_range"),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    season = Column(SmallInteger, nullable=False, index=True)
    role = Column(String(10), nullable=False, index=True)
    rating_model_version = Column(String(40), nullable=False, index=True)
    source_distribution_version = Column(String(40), nullable=False, index=True)
    # Nombre físico legacy; versiona el modelo de performance tier.
    rarity_model_version = Column(String(40), nullable=False, index=True)
    metric = Column(String(64), nullable=False, index=True)
    population_size = Column(Integer, nullable=False)
    # Conteos discretos necesarios para resolver empates con mid-rank real.
    population_histogram = Column(JSON, nullable=False)
    minimum = Column(Numeric(12, 8), nullable=False)
    p05 = Column(Numeric(12, 8), nullable=False)
    p10 = Column(Numeric(12, 8), nullable=False)
    p25 = Column(Numeric(12, 8), nullable=False)
    p50 = Column(Numeric(12, 8), nullable=False)
    p75 = Column(Numeric(12, 8), nullable=False)
    p90 = Column(Numeric(12, 8), nullable=False)
    p95 = Column(Numeric(12, 8), nullable=False)
    maximum = Column(Numeric(12, 8), nullable=False)
    population_mean = Column(Numeric(12, 8), nullable=False)
    data_start_date = Column(Date, nullable=False)
    data_end_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
