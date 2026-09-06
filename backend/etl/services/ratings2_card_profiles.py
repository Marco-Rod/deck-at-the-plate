"""Adaptador de PlayerRatings pitcher a CardGenerationProfile, sin calcular ratings."""

import hashlib
import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import CardGenerationProfile, PlayerRatings, PlayerSeason, RatingDistribution
from etl.config.rarity_2 import OVERALL_RATING_METRIC, RARITY_MODEL_VERSION
from etl.config.ratings_2 import RATING_MODEL_VERSION
from etl.services.pitcher_traits2 import (
    PITCHER_TRAIT_MODEL_VERSION,
    calculate_pitcher_trait,
)
from etl.services.rarity2 import RarityResult, calculate_rarity


ADAPTER_VERSION = "pitcher-ratings2-card-profile-2.0"


@dataclass(frozen=True)
class Ratings2CardProfileResult:
    status: str
    card_generation_profile_id: str | None
    player_ratings_id: str


def _adapter_input_hash(
    ratings: PlayerRatings,
    pitcher_trait: str | None,
    rating_distribution: RatingDistribution,
    rarity: RarityResult,
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
        "rarity_model_version": rarity.rarity_model_version,
        "rating_distribution_id": rating_distribution.id,
        "rating_distribution_population_size": rating_distribution.population_size,
        "rating_distribution_histogram": rating_distribution.population_histogram,
        "rarity": rarity.rarity.value,
        "rarity_percentile": rarity.percentile,
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
        rarity_model_version=RARITY_MODEL_VERSION,
        data_start_date=ratings.data_start_date,
        data_end_date=ratings.data_end_date,
    ).one_or_none()
    if rating_distribution is None:
        return Ratings2CardProfileResult(
            "SKIPPED_NO_RATING_DISTRIBUTION", None, ratings.id
        )
    rarity = calculate_rarity(ratings.overall_rating, rating_distribution)

    pitcher_trait = calculate_pitcher_trait(
        ratings.velocity_rating,
        ratings.control_rating,
        ratings.movement_rating,
        ratings.stuff_rating,
    )
    input_hash = _adapter_input_hash(
        ratings, pitcher_trait, rating_distribution, rarity
    )
    values = {
        "player_ratings_id": ratings.id,
        "input_hash": input_hash,
        # Compatibilidad temporal con el contrato legacy de CardGenerationProfile.
        "contact_rating": 0,
        "power_rating": 0,
        "vision_rating": 0,
        "clutch_rating": 0,
        "velocity_rating": ratings.velocity_rating,
        "control_rating": ratings.control_rating,
        "movement_rating": ratings.movement_rating,
        "stuff_rating": ratings.stuff_rating,
        "overall_rating": ratings.overall_rating,
        "calculated_rarity": rarity.rarity,
        "primary_batter_trait": None,
        "primary_pitcher_trait": pitcher_trait,
        "repertoire_payload": None,
        "calculation_metadata": {
            "adapter_version": ADAPTER_VERSION,
            "distribution_version": ratings.distribution_version,
            "rarity_model_version": rarity.rarity_model_version,
            "rating_distribution_id": rating_distribution.id,
            "rarity_percentile": rarity.percentile,
            "rarity": rarity.rarity.value,
            "pitcher_trait_model_version": PITCHER_TRAIT_MODEL_VERSION,
            "traits_status": "ASSIGNED" if pitcher_trait is not None else "NO_TRAIT",
        },
    }
    profile = db.query(CardGenerationProfile).filter_by(
        player_season_id=player_season.id,
        rating_model_version=ratings.rating_model_version,
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
