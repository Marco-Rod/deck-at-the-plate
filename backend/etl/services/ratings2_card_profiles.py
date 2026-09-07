"""Adaptadores PlayerRatings→CardGenerationProfile, sin recalcular ratings."""

import hashlib
import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import CardGenerationProfile, PlayerRatings, PlayerSeason, RatingDistribution
from app.models.card import CardRarity
from etl.config.performance_tier_2 import (
    OVERALL_RATING_METRIC,
    PERFORMANCE_TIER_MODEL_VERSION,
)
from etl.config.ratings_2 import RATING_MODEL_VERSION
from etl.services.pitcher_traits2 import (
    PITCHER_TRAIT_MODEL_VERSION,
    calculate_pitcher_trait,
)
from etl.services.performance_tier2 import (
    PerformanceTierResult,
    calculate_performance_tier,
)


ADAPTER_VERSION = "pitcher-ratings2-card-profile-2.0"
BATTER_ADAPTER_VERSION = "batter-ratings2-card-profile-2.0"


@dataclass(frozen=True)
class Ratings2CardProfileResult:
    status: str
    card_generation_profile_id: str | None
    player_ratings_id: str


def _adapter_input_hash(
    ratings: PlayerRatings,
    pitcher_trait: str | None,
    rating_distribution: RatingDistribution,
    performance: PerformanceTierResult,
) -> str:
    payload = {
        "adapter_version": ADAPTER_VERSION,
        "player_ratings_id": ratings.id,
        "player_ratings_input_hash": ratings.input_hash,
        "rating_model_version": ratings.rating_model_version,
        "distribution_version": ratings.distribution_version,
        "ratings": {
            "velocity": ratings.velocity_rating,
            "control": ratings.control_rating,
            "movement": ratings.movement_rating,
            "stuff": ratings.stuff_rating,
            "overall": ratings.overall_rating,
        },
        "pitcher_trait_model_version": PITCHER_TRAIT_MODEL_VERSION,
        "pitcher_trait": pitcher_trait,
        "performance_tier_model_version": performance.performance_tier_model_version,
        "rating_distribution_id": rating_distribution.id,
        "rating_distribution_population_size": rating_distribution.population_size,
        "rating_distribution_histogram": rating_distribution.population_histogram,
        "performance_tier": performance.performance_tier.value,
        "performance_percentile": performance.performance_percentile,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _batter_adapter_input_hash(
    ratings: PlayerRatings,
    rating_distribution: RatingDistribution,
    performance: PerformanceTierResult,
) -> str:
    payload = {
        "adapter_version": BATTER_ADAPTER_VERSION,
        "role": ratings.role,
        "player_ratings_id": ratings.id,
        "player_ratings_input_hash": ratings.input_hash,
        "rating_model_version": ratings.rating_model_version,
        "distribution_version": ratings.distribution_version,
        "ratings": {
            "contact": ratings.contact_rating,
            "power": ratings.power_rating,
            "vision": ratings.vision_rating,
            "clutch": ratings.clutch_rating,
            "overall": ratings.overall_rating,
        },
        "performance_tier_model_version": performance.performance_tier_model_version,
        "rating_distribution_id": rating_distribution.id,
        "rating_distribution_population_size": rating_distribution.population_size,
        "rating_distribution_histogram": rating_distribution.population_histogram,
        "performance_tier": performance.performance_tier.value,
        "performance_percentile": performance.performance_percentile,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def generate_pitcher_card_profile_from_ratings2(
    db: Session,
    *,
    player_ratings_id: str,
    player_season_id: str | None = None,
) -> Ratings2CardProfileResult:
    """Copia un snapshot estadístico completo a la capa de juego transicional."""
    ratings = db.get(PlayerRatings, player_ratings_id)
    if ratings is None:
        raise ValueError(f"PlayerRatings inexistente: {player_ratings_id}")
    if ratings.role != "PITCHER":
        raise ValueError("PlayerRatings no pertenece al rol PITCHER")
    if ratings.rating_model_version != RATING_MODEL_VERSION:
        raise ValueError(f"modelo inesperado: {ratings.rating_model_version}")

    snapshot_query = db.query(PlayerSeason).filter_by(
        player_id=ratings.player_id,
        season=ratings.season,
        data_start_date=ratings.data_start_date,
        data_end_date=ratings.data_end_date,
    )
    if player_season_id is not None:
        snapshot_query = snapshot_query.filter(PlayerSeason.id == player_season_id)
    player_season = snapshot_query.one_or_none()
    if player_season is None:
        raise ValueError("PlayerRatings no coincide con el jugador/snapshot solicitado")

    rating_distribution = db.query(RatingDistribution).filter_by(
        season=ratings.season,
        role=ratings.role,
        metric=OVERALL_RATING_METRIC,
        rating_model_version=ratings.rating_model_version,
        source_distribution_version=ratings.distribution_version,
        rarity_model_version=PERFORMANCE_TIER_MODEL_VERSION,
        data_start_date=ratings.data_start_date,
        data_end_date=ratings.data_end_date,
    ).one_or_none()
    if rating_distribution is None:
        return Ratings2CardProfileResult(
            "SKIPPED_NO_RATING_DISTRIBUTION", None, ratings.id
        )
    performance = calculate_performance_tier(
        ratings.overall_rating, rating_distribution
    )

    pitcher_trait = calculate_pitcher_trait(
        ratings.velocity_rating,
        ratings.control_rating,
        ratings.movement_rating,
        ratings.stuff_rating,
    )
    input_hash = _adapter_input_hash(
        ratings, pitcher_trait, rating_distribution, performance
    )
    values = {
        "role": "PITCHER",
        "player_ratings_id": ratings.id,
        "input_hash": input_hash,
        # Compatibilidad temporal con el contrato legacy de CardGenerationProfile.
        "contact_rating": None,
        "power_rating": None,
        "vision_rating": None,
        "clutch_rating": None,
        "velocity_rating": ratings.velocity_rating,
        "control_rating": ratings.control_rating,
        "movement_rating": ratings.movement_rating,
        "stuff_rating": ratings.stuff_rating,
        "overall_rating": ratings.overall_rating,
        # La rareza de carta queda neutral hasta que exista CardEdition.
        "calculated_rarity": CardRarity.COMMON,
        "primary_batter_trait": None,
        "primary_pitcher_trait": pitcher_trait,
        "repertoire_payload": None,
        "calculation_metadata": {
            "adapter_version": ADAPTER_VERSION,
            "distribution_version": ratings.distribution_version,
            "performance_tier_model_version": (
                performance.performance_tier_model_version
            ),
            "rating_distribution_id": rating_distribution.id,
            "performance_percentile": performance.performance_percentile,
            "performance_tier": performance.performance_tier.value,
            "card_rarity_status": "PENDING_CARD_EDITION",
            "pitcher_trait_model_version": PITCHER_TRAIT_MODEL_VERSION,
            "traits_status": "ASSIGNED" if pitcher_trait is not None else "NO_TRAIT",
        },
    }
    profile = db.query(CardGenerationProfile).filter_by(
        player_season_id=player_season.id,
        rating_model_version=ratings.rating_model_version,
        role="PITCHER",
    ).one_or_none()
    if profile is None:
        profile = CardGenerationProfile(
            player_season_id=player_season.id,
            rating_model_version=ratings.rating_model_version,
            **values,
        )
        db.add(profile)
        db.commit()
        return Ratings2CardProfileResult("CREATED", profile.id, ratings.id)
    if profile.input_hash == input_hash and profile.player_ratings_id == ratings.id:
        return Ratings2CardProfileResult("UNCHANGED", profile.id, ratings.id)
    for field_name, value in values.items():
        setattr(profile, field_name, value)
    db.commit()
    return Ratings2CardProfileResult("UPDATED", profile.id, ratings.id)


def generate_batter_card_profile_from_ratings2(
    db: Session,
    *,
    player_ratings_id: str,
    player_season_id: str | None = None,
) -> Ratings2CardProfileResult:
    """Adapta ratings BATTER completos usando la población equivalente exacta."""
    ratings = db.get(PlayerRatings, player_ratings_id)
    if ratings is None:
        raise ValueError(f"PlayerRatings inexistente: {player_ratings_id}")
    if ratings.role != "BATTER":
        raise ValueError("PlayerRatings no pertenece al rol BATTER")
    if ratings.rating_model_version != RATING_MODEL_VERSION:
        raise ValueError(f"modelo inesperado: {ratings.rating_model_version}")

    snapshot_query = db.query(PlayerSeason).filter_by(
        player_id=ratings.player_id,
        season=ratings.season,
        data_start_date=ratings.data_start_date,
        data_end_date=ratings.data_end_date,
    )
    if player_season_id is not None:
        snapshot_query = snapshot_query.filter(PlayerSeason.id == player_season_id)
    player_season = snapshot_query.one_or_none()
    if player_season is None:
        raise ValueError("PlayerRatings no coincide con el jugador/snapshot solicitado")

    rating_distribution = db.query(RatingDistribution).filter_by(
        season=ratings.season,
        role="BATTER",
        metric=OVERALL_RATING_METRIC,
        rating_model_version=ratings.rating_model_version,
        source_distribution_version=ratings.distribution_version,
        rarity_model_version=PERFORMANCE_TIER_MODEL_VERSION,
        data_start_date=ratings.data_start_date,
        data_end_date=ratings.data_end_date,
    ).one_or_none()
    if rating_distribution is None:
        return Ratings2CardProfileResult(
            "SKIPPED_NO_RATING_DISTRIBUTION", None, ratings.id
        )
    performance = calculate_performance_tier(
        ratings.overall_rating, rating_distribution
    )
    input_hash = _batter_adapter_input_hash(
        ratings, rating_distribution, performance
    )
    values = {
        "role": "BATTER",
        "player_ratings_id": ratings.id,
        "input_hash": input_hash,
        "contact_rating": ratings.contact_rating,
        "power_rating": ratings.power_rating,
        "vision_rating": ratings.vision_rating,
        "clutch_rating": ratings.clutch_rating,
        "velocity_rating": None,
        "control_rating": None,
        "movement_rating": None,
        "stuff_rating": None,
        "overall_rating": ratings.overall_rating,
        # La rareza de carta queda neutral hasta que exista CardEdition.
        "calculated_rarity": CardRarity.COMMON,
        "primary_batter_trait": None,
        "primary_pitcher_trait": None,
        "repertoire_payload": None,
        "calculation_metadata": {
            "adapter_version": BATTER_ADAPTER_VERSION,
            "distribution_version": ratings.distribution_version,
            "performance_tier_model_version": (
                performance.performance_tier_model_version
            ),
            "rating_distribution_id": rating_distribution.id,
            "rating_distribution_population_size": rating_distribution.population_size,
            "rating_distribution_histogram": rating_distribution.population_histogram,
            "performance_percentile": performance.performance_percentile,
            "performance_tier": performance.performance_tier.value,
            "card_rarity_status": "PENDING_CARD_EDITION",
            "traits_status": "PENDING_TRAITS_2.0",
        },
    }
    profile = db.query(CardGenerationProfile).filter_by(
        player_season_id=player_season.id,
        rating_model_version=ratings.rating_model_version,
        role="BATTER",
    ).one_or_none()
    if profile is None:
        profile = CardGenerationProfile(
            player_season_id=player_season.id,
            rating_model_version=ratings.rating_model_version,
            **values,
        )
        db.add(profile)
        db.commit()
        return Ratings2CardProfileResult("CREATED", profile.id, ratings.id)
    if profile.input_hash == input_hash and profile.player_ratings_id == ratings.id:
        return Ratings2CardProfileResult("UNCHANGED", profile.id, ratings.id)
    for field_name, value in values.items():
        setattr(profile, field_name, value)
    db.commit()
    return Ratings2CardProfileResult("UPDATED", profile.id, ratings.id)


def generate_card_profile_from_ratings2(
    db: Session,
    *,
    player_ratings_id: str,
    player_season_id: str | None = None,
) -> Ratings2CardProfileResult:
    """Despacha al adaptador del rol sin alterar el contrato del CLI."""
    ratings = db.get(PlayerRatings, player_ratings_id)
    if ratings is None:
        raise ValueError(f"PlayerRatings inexistente: {player_ratings_id}")
    if ratings.role == "BATTER":
        return generate_batter_card_profile_from_ratings2(
            db,
            player_ratings_id=player_ratings_id,
            player_season_id=player_season_id,
        )
    if ratings.role == "PITCHER":
        return generate_pitcher_card_profile_from_ratings2(
            db,
            player_ratings_id=player_ratings_id,
            player_season_id=player_season_id,
        )
    raise ValueError(f"rol inesperado: {ratings.role}")
