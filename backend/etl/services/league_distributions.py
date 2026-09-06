"""Construcción idempotente de distribuciones de liga a partir de Analytics."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from statistics import fmean, median, pstdev
from math import hypot

from sqlalchemy.orm import Session

from app.models import (
    BatterSeasonStats,
    LeagueMetricDistribution,
    PitcherPitchProfile,
    PitcherSeasonStats,
    PlayerSeason,
)
from etl.config.league_distributions import (
    BATTER_METRICS,
    MOVEMENT_EXCLUDED_PITCH_TYPES,
    MOVEMENT_FAMILY_MIN_POPULATION,
    MOVEMENT_PITCH_TYPE_MIN_POPULATION,
    MOVEMENT_PROFILE_MIN_PITCHES,
    PITCHER_METRICS,
    default_distribution_version,
)
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


def _upsert_distribution(db: Session, identity: dict, payload: dict) -> str:
    existing = db.query(LeagueMetricDistribution).filter_by(**identity).one_or_none()
    if existing is None:
        db.add(LeagueMetricDistribution(**identity, **payload))
        return "created"
    if all(getattr(existing, field) == value for field, value in payload.items()):
        return "unchanged"
    for field, value in payload.items():
        setattr(existing, field, value)
    return "updated"


def _batter_metric_value(row: BatterSeasonStats, metric: str):
    if metric == "iso":
        if row.slg is None or row.avg is None:
            return None
        return row.slg - row.avg
    if metric == "walk_rate":
        return row.walks / row.pa if row.pa else None
    if metric == "strikeout_rate":
        return row.strikeouts / row.pa if row.pa else None
    return getattr(row, metric)


def _build_batter_distributions(
    db: Session,
    *,
    season: int,
    data_start_date: date,
    data_end_date: date,
    version: str,
) -> DistributionBuildResult:
    rows = (
        db.query(BatterSeasonStats)
        .join(PlayerSeason, PlayerSeason.id == BatterSeasonStats.player_season_id)
        .filter(
            PlayerSeason.season == season,
            PlayerSeason.data_start_date == data_start_date,
            PlayerSeason.data_end_date == data_end_date,
        )
        .all()
    )
    created = updated = unchanged = skipped = 0
    for metric, config in BATTER_METRICS.items():
        observations = [
            (_batter_metric_value(row, metric), int(getattr(row, config.sample_field)))
            for row in rows
        ]
        eligible = [
            (value, sample)
            for value, sample in observations
            if value is not None and sample > 0
        ]
        if not eligible:
            skipped += 1
            continue
        values = [float(value) for value, _sample in eligible]
        samples = [sample for _value, sample in eligible]
        identity = {
            "season": season,
            "role": "BATTER",
            "metric": metric,
            "pitch_type": None,
            "pitch_family": None,
            "distribution_version": version,
            "data_start_date": data_start_date,
            "data_end_date": data_end_date,
        }
        outcome = _upsert_distribution(db, identity, _summary(values, samples))
        if outcome == "created":
            created += 1
        elif outcome == "updated":
            updated += 1
        else:
            unchanged += 1
    db.commit()
    return DistributionBuildResult(created, updated, unchanged, skipped, version)


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
    if normalized_role not in {"BATTER", "PITCHER"}:
        raise ValueError("role debe ser batter o pitcher")
    if data_end_date < data_start_date:
        raise ValueError("data_end_date debe ser igual o posterior a data_start_date")

    version = distribution_version or default_distribution_version()
    if normalized_role == "BATTER":
        return _build_batter_distributions(
            db,
            season=season,
            data_start_date=data_start_date,
            data_end_date=data_end_date,
            version=version,
        )
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
            "pitch_type": None,
            "pitch_family": None,
            "distribution_version": version,
            "data_start_date": data_start_date,
            "data_end_date": data_end_date,
        }
        outcome = _upsert_distribution(db, identity, payload)
        if outcome == "created":
            created += 1
        elif outcome == "updated":
            updated += 1
        else:
            unchanged += 1

    profiles = (
        db.query(PitcherPitchProfile)
        .join(PlayerSeason, PlayerSeason.id == PitcherPitchProfile.player_season_id)
        .filter(
            PlayerSeason.season == season,
            PlayerSeason.data_start_date == data_start_date,
            PlayerSeason.data_end_date == data_end_date,
            PitcherPitchProfile.batter_side == "ALL",
            PitcherPitchProfile.pitch_count >= MOVEMENT_PROFILE_MIN_PITCHES,
            PitcherPitchProfile.avg_pfx_x.isnot(None),
            PitcherPitchProfile.avg_pfx_z.isnot(None),
            ~PitcherPitchProfile.pitch_type.in_(MOVEMENT_EXCLUDED_PITCH_TYPES),
        )
        .all()
    )
    type_profiles: dict[tuple[str, str], list[PitcherPitchProfile]] = {}
    family_pitcher_profiles: dict[tuple[str, str], list[PitcherPitchProfile]] = {}
    for profile in profiles:
        family = profile.pitch_family.value if hasattr(profile.pitch_family, "value") else str(profile.pitch_family)
        type_profiles.setdefault((profile.pitch_type, family), []).append(profile)
        family_pitcher_profiles.setdefault((family, profile.player_season_id), []).append(profile)

    for (pitch_type, pitch_family), scoped in sorted(type_profiles.items(), key=lambda item: (item[0][1], item[0][0])):
        if len(scoped) < MOVEMENT_PITCH_TYPE_MIN_POPULATION:
            continue
        values = [hypot(float(row.avg_pfx_x), float(row.avg_pfx_z)) for row in scoped]
        samples = [row.pitch_count for row in scoped]
        identity = {
            "season": season,
            "role": normalized_role,
            "metric": "movement_magnitude",
            "pitch_type": pitch_type,
            "pitch_family": pitch_family,
            "distribution_version": version,
            "data_start_date": data_start_date,
            "data_end_date": data_end_date,
        }
        outcome = _upsert_distribution(db, identity, _summary(values, samples))
        if outcome == "created":
            created += 1
        elif outcome == "updated":
            updated += 1
        else:
            unchanged += 1

    # El fallback agrupa primero todos los pitch types de cada pitcher. Así los
    # percentiles dan un voto por pitcher, aunque use FF+SI+FC, mientras que el
    # baseline conserva como peso el total de pitches de la familia.
    family_observations: dict[str, list[tuple[float, int]]] = {}
    for (pitch_family, _player_season_id), pitcher_profiles in family_pitcher_profiles.items():
        sample = sum(row.pitch_count for row in pitcher_profiles)
        weighted_magnitude = sum(
            hypot(float(row.avg_pfx_x), float(row.avg_pfx_z)) * row.pitch_count
            for row in pitcher_profiles
        ) / sample
        family_observations.setdefault(pitch_family, []).append((weighted_magnitude, sample))

    for pitch_family, observations in sorted(family_observations.items()):
        if len(observations) < MOVEMENT_FAMILY_MIN_POPULATION:
            continue
        values = [value for value, _sample in observations]
        samples = [sample for _value, sample in observations]
        identity = {
            "season": season,
            "role": normalized_role,
            "metric": "movement_magnitude",
            "pitch_type": None,
            "pitch_family": pitch_family,
            "distribution_version": version,
            "data_start_date": data_start_date,
            "data_end_date": data_end_date,
        }
        outcome = _upsert_distribution(db, identity, _summary(values, samples))
        if outcome == "created":
            created += 1
        elif outcome == "updated":
            updated += 1
        else:
            unchanged += 1

    db.commit()
    return DistributionBuildResult(created, updated, unchanged, skipped, version)
