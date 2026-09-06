"""Construcción idempotente de distribuciones de liga a partir de Analytics."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from statistics import fmean, median, pstdev

from sqlalchemy.orm import Session

from app.models import LeagueMetricDistribution, PitcherSeasonStats, PlayerSeason
from etl.config.league_distributions import PITCHER_METRICS, default_distribution_version
from etl.services.percentiles import percentile


DECIMAL_STEP = Decimal("0.00000001")


@dataclass(frozen=True)
class DistributionBuildResult:
    created: int
    updated: int
    unchanged: int
    skipped: int
    version: str


def _decimal(value: float) -> Decimal:
    return Decimal(str(value)).quantize(DECIMAL_STEP, rounding=ROUND_HALF_UP)


def _summary(values: list[float], samples: list[int]) -> dict:
    sample_size_total = sum(samples)
    return {
        "population_size": len(values),
        "sample_size_total": sample_size_total,
        # Los percentiles y este promedio describen la población de pitchers:
        # cada pitcher es una observación con el mismo peso.
        "population_mean": _decimal(fmean(values)),
        # El prior de shrinkage representa oportunidades MLB agregadas.
        "league_baseline": _decimal(
            sum(value * sample for value, sample in zip(values, samples)) / sample_size_total
        ),
        "median": _decimal(median(values)),
        "stddev": _decimal(pstdev(values)),
        "p05": _decimal(percentile(values, 0.05)),
        "p10": _decimal(percentile(values, 0.10)),
        "p25": _decimal(percentile(values, 0.25)),
        "p50": _decimal(percentile(values, 0.50)),
        "p75": _decimal(percentile(values, 0.75)),
        "p90": _decimal(percentile(values, 0.90)),
        "p95": _decimal(percentile(values, 0.95)),
        "minimum": _decimal(min(values)),
        "maximum": _decimal(max(values)),
    }


def build_league_distributions(
    db: Session,
    *,
    season: int,
    role: str,
    data_start_date: date,
    data_end_date: date,
    distribution_version: str | None = None,
) -> DistributionBuildResult:
    normalized_role = role.upper()
    if normalized_role != "PITCHER":
        raise ValueError("la primera versión solo soporta role=pitcher")
    if data_end_date < data_start_date:
        raise ValueError("data_end_date debe ser igual o posterior a data_start_date")

    version = distribution_version or default_distribution_version()
    rows = (
        db.query(PitcherSeasonStats)
        .join(PlayerSeason, PlayerSeason.id == PitcherSeasonStats.player_season_id)
        .filter(
            PlayerSeason.season == season,
            PlayerSeason.data_start_date == data_start_date,
            PlayerSeason.data_end_date == data_end_date,
        )
        .all()
    )
    created = updated = unchanged = skipped = 0

    for metric, config in PITCHER_METRICS.items():
        eligible = [
            row for row in rows
            if getattr(row, metric) is not None
            and getattr(row, config.sample_field) >= config.min_sample
        ]
        if not eligible:
            skipped += 1
            continue
        values = [float(getattr(row, metric)) for row in eligible]
        samples = [int(getattr(row, config.sample_field)) for row in eligible]
        payload = _summary(values, samples)
        identity = {
            "season": season,
            "role": normalized_role,
            "metric": metric,
            "distribution_version": version,
            "data_start_date": data_start_date,
            "data_end_date": data_end_date,
        }
        existing = db.query(LeagueMetricDistribution).filter_by(**identity).one_or_none()
        if existing is None:
            db.add(LeagueMetricDistribution(**identity, **payload))
            created += 1
        elif all(getattr(existing, field) == value for field, value in payload.items()):
            unchanged += 1
        else:
            for field, value in payload.items():
                setattr(existing, field, value)
            updated += 1

    db.commit()
    return DistributionBuildResult(created, updated, unchanged, skipped, version)
