"""Adaptador de PlayerRatings pitcher a CardGenerationProfile, sin calcular ratings."""

import hashlib
import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import CardGenerationProfile, PlayerRatings, PlayerSeason
from app.models.card import CardRarity
from etl.config.ratings_2 import RATING_MODEL_VERSION


ADAPTER_VERSION = "pitcher-ratings2-card-profile-1.0"
TRANSITIONAL_RARITY_POLICY = "COMMON_PLACEHOLDER_PENDING_RARITY_2.0"


@dataclass(frozen=True)
class Ratings2CardProfileResult:
    status: str
    card_generation_profile_id: str
    player_ratings_id: str


def _adapter_input_hash(ratings: PlayerRatings) -> str:
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
        "rarity_policy": TRANSITIONAL_RARITY_POLICY,
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

    input_hash = _adapter_input_hash(ratings)
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
        "calculated_rarity": CardRarity.COMMON,
        "primary_batter_trait": None,
        "primary_pitcher_trait": None,
        "repertoire_payload": None,
        "calculation_metadata": {
            "adapter_version": ADAPTER_VERSION,
            "distribution_version": ratings.distribution_version,
            "rarity_policy": TRANSITIONAL_RARITY_POLICY,
            "traits_status": "PENDING_TRAITS_2.0",
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
