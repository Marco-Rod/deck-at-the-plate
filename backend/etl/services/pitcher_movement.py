"""Candidato auditable de Movement para ratings-2.0, sin persistencia de carta."""

from dataclasses import dataclass, field
from datetime import date
from math import hypot

from sqlalchemy.orm import Session

from app.models import LeagueMetricDistribution, PitcherPitchProfile, Player, PlayerSeason
from etl.config.league_distributions import MOVEMENT_EXCLUDED_PITCH_TYPES, default_distribution_version
from etl.config.ratings_2 import MOVEMENT_STABILIZATION_PITCHES, RATING_MODEL_VERSION
from etl.services.percentiles import distribution_percentile_rank, percentile_rating


@dataclass(frozen=True)
class PitchMovementCandidate:
    pitch_type: str
    pitch_family: str
    scope: str
    raw_magnitude: float
    league_baseline: float
    pitch_count: int
    shrinkage_weight: float
    adjusted_magnitude: float
    percentile: float
    rating: int
    usage: float


@dataclass(frozen=True)
class MovementCandidateResult:
    mlb_id: int
    rating_model_version: str
    distribution_version: str
    movement_rating: int | None
    evaluable_usage: float
    pitches: list[PitchMovementCandidate] = field(default_factory=list)
    skipped_pitch_types: list[str] = field(default_factory=list)


def _distribution(
    db: Session,
    *,
    season: int,
    data_start_date: date,
    data_end_date: date,
    distribution_version: str,
    pitch_type: str | None,
    pitch_family: str,
):
    return db.query(LeagueMetricDistribution).filter_by(
        season=season,
        role="PITCHER",
        metric="movement_magnitude",
        pitch_type=pitch_type,
        pitch_family=pitch_family,
        distribution_version=distribution_version,
        data_start_date=data_start_date,
        data_end_date=data_end_date,
    ).one_or_none()


def calculate_movement_candidate(
    db: Session,
    *,
    mlb_id: int,
    season: int,
    data_start_date: date,
    data_end_date: date,
    distribution_version: str | None = None,
) -> MovementCandidateResult:
    """Resuelve type→family→skip, aplica shrinkage y renormaliza usage."""
    version = distribution_version or default_distribution_version()
    player_season = (
        db.query(PlayerSeason)
        .join(Player, Player.id == PlayerSeason.player_id)
        .filter(
            Player.mlb_id == mlb_id,
            PlayerSeason.season == season,
            PlayerSeason.data_start_date == data_start_date,
            PlayerSeason.data_end_date == data_end_date,
        )
        .one_or_none()
    )
    if player_season is None:
        raise ValueError(f"sin PlayerSeason para mlb_id={mlb_id} en el snapshot solicitado")

    profiles = db.query(PitcherPitchProfile).filter(
        PitcherPitchProfile.player_season_id == player_season.id,
        PitcherPitchProfile.batter_side == "ALL",
        PitcherPitchProfile.pitch_count > 0,
        PitcherPitchProfile.avg_pfx_x.isnot(None),
        PitcherPitchProfile.avg_pfx_z.isnot(None),
        ~PitcherPitchProfile.pitch_type.in_(MOVEMENT_EXCLUDED_PITCH_TYPES),
    ).order_by(PitcherPitchProfile.pitch_count.desc(), PitcherPitchProfile.pitch_type).all()

    candidates: list[PitchMovementCandidate] = []
    skipped: list[str] = []
    profile_pitch_total = sum(profile.pitch_count for profile in profiles)
    for profile in profiles:
        family = profile.pitch_family.value if hasattr(profile.pitch_family, "value") else str(profile.pitch_family)
        distribution = _distribution(
            db, season=season, data_start_date=data_start_date, data_end_date=data_end_date,
            distribution_version=version, pitch_type=profile.pitch_type, pitch_family=family,
        )
        scope = "pitch_type"
        if distribution is None:
            distribution = _distribution(
                db, season=season, data_start_date=data_start_date, data_end_date=data_end_date,
                distribution_version=version, pitch_type=None, pitch_family=family,
            )
            scope = "pitch_family"
        if distribution is None:
            skipped.append(profile.pitch_type)
            continue

        observed = hypot(float(profile.avg_pfx_x), float(profile.avg_pfx_z))
        baseline = float(distribution.league_baseline)
        weight = profile.pitch_count / (profile.pitch_count + MOVEMENT_STABILIZATION_PITCHES)
        adjusted = weight * observed + (1 - weight) * baseline
        percentile = distribution_percentile_rank(adjusted, distribution, direction="higher")
        usage = (
            float(profile.usage_rate)
            if profile.usage_rate is not None
            else profile.pitch_count / profile_pitch_total
        )
        candidates.append(PitchMovementCandidate(
            pitch_type=profile.pitch_type,
            pitch_family=family,
            scope=scope,
            raw_magnitude=observed,
            league_baseline=baseline,
            pitch_count=profile.pitch_count,
            shrinkage_weight=weight,
            adjusted_magnitude=adjusted,
            percentile=percentile,
            rating=percentile_rating(percentile),
            usage=usage,
        ))

    evaluable_usage = sum(candidate.usage for candidate in candidates)
    movement_rating = (
        round(sum(candidate.rating * candidate.usage for candidate in candidates) / evaluable_usage)
        if evaluable_usage > 0 else None
    )
    return MovementCandidateResult(
        mlb_id=mlb_id,
        rating_model_version=RATING_MODEL_VERSION,
        distribution_version=version,
        movement_rating=movement_rating,
        evaluable_usage=evaluable_usage,
        pitches=candidates,
        skipped_pitch_types=skipped,
    )
