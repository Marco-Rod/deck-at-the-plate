"""Persistencia idempotente de resultados completos de ratings, sin recalcular."""

import hashlib
import json
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy.orm import Session

from app.models import Player, PlayerRatings, PlayerSeason
from etl.config.ratings_2 import BATTER_OVERALL_WEIGHTS, RATING_MODEL_VERSION
from etl.services.batter_ratings2 import BatterRatings2
from etl.services.pitcher_ratings2 import PitcherRatings2Result


@dataclass(frozen=True)
class PlayerRatingsPersistenceResult:
    status: str
    player_ratings_id: str | None
    input_hash: str | None
    skipped_components: tuple[str, ...] = ()


def _canonical(value):
    if is_dataclass(value):
        return {field.name: _canonical(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    return value


def _effective_input_hash(
    result: PitcherRatings2Result,
    *,
    season: int,
    data_start_date: date,
    data_end_date: date,
) -> str:
    payload = {
        "rating_model_version": result.rating_model_version,
        "distribution_version": result.velocity.distribution_version,
        "season": season,
        "data_start_date": data_start_date,
        "data_end_date": data_end_date,
        # Incluye métricas observadas, denominadores, baselines, scopes,
        # stabilization, valores ajustados, percentiles y resultados finales.
        "calculator_result": result,
    }
    encoded = json.dumps(
        _canonical(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def persist_pitcher_ratings2(
    db: Session,
    result: PitcherRatings2Result,
    *,
    season: int,
    data_start_date: date,
    data_end_date: date,
) -> PlayerRatingsPersistenceResult:
    """Persiste un resultado ya calculado; nunca invoca calculadoras."""
    if result.rating_model_version != RATING_MODEL_VERSION:
        raise ValueError(f"modelo inesperado: {result.rating_model_version}")
    component_ratings = (
        result.velocity.rating,
        result.control.rating,
        result.movement.rating,
        result.stuff.rating,
    )
    if result.overall is None or any(rating is None for rating in component_ratings):
        return PlayerRatingsPersistenceResult("SKIPPED_INCOMPLETE", None, None)

    player = db.query(Player).filter(Player.mlb_id == result.mlb_id).one_or_none()
    if player is None:
        raise ValueError(f"sin Player para mlb_id={result.mlb_id}")
    distribution_versions = {
        result.velocity.distribution_version,
        result.control.distribution_version,
        result.movement.distribution_version,
        result.stuff.distribution_version,
    }
    if len(distribution_versions) != 1:
        raise ValueError("los componentes usan distribution_version diferentes")
    distribution_version = distribution_versions.pop()
    input_hash = _effective_input_hash(
        result, season=season, data_start_date=data_start_date, data_end_date=data_end_date
    )
    identity = {
        "player_id": player.id,
        "season": season,
        "role": "PITCHER",
        "rating_model_version": result.rating_model_version,
        "distribution_version": distribution_version,
        "data_start_date": data_start_date,
        "data_end_date": data_end_date,
    }
    row = db.query(PlayerRatings).filter_by(**identity).one_or_none()
    ratings = {
        "velocity_rating": result.velocity.rating,
        "control_rating": result.control.rating,
        "movement_rating": result.movement.rating,
        "stuff_rating": result.stuff.rating,
        "overall_rating": result.overall,
    }
    if row is None:
        row = PlayerRatings(**identity, **ratings, input_hash=input_hash)
        db.add(row)
        db.commit()
        return PlayerRatingsPersistenceResult("CREATED", row.id, input_hash)
    if row.input_hash == input_hash:
        return PlayerRatingsPersistenceResult("UNCHANGED", row.id, input_hash)
    for field_name, value in ratings.items():
        setattr(row, field_name, value)
    row.input_hash = input_hash
    db.commit()
    return PlayerRatingsPersistenceResult("UPDATED", row.id, input_hash)


def _effective_batter_input_hash(
    result: BatterRatings2,
    *,
    player_season_id: str,
    season: int,
    data_start_date: date,
    data_end_date: date,
) -> str:
    payload = {
        "player_season_id": player_season_id,
        "season": season,
        "role": "BATTER",
        "rating_model_version": result.model_version,
        "distribution_version": result.contact.distribution_version,
        "data_start_date": data_start_date,
        "data_end_date": data_end_date,
        "overall_weights": BATTER_OVERALL_WEIGHTS,
        # Los subresultados incluyen observados, samples, shrinkage, baselines,
        # percentiles, ratings, IDs de distribución y provenance de Clutch.
        "calculator_result": result,
    }
    encoded = json.dumps(
        _canonical(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def persist_batter_ratings2(
    db: Session,
    result: BatterRatings2,
    *,
    season: int,
    data_start_date: date,
    data_end_date: date,
) -> PlayerRatingsPersistenceResult:
    """Persiste un BatterRatings2 completo sin recalcular sus componentes."""
    if result.model_version != RATING_MODEL_VERSION:
        raise ValueError(f"modelo inesperado: {result.model_version}")
    component_ratings = (
        result.contact.rating,
        result.power.rating,
        result.vision.rating,
        result.clutch.rating,
    )
    if result.overall_rating is None or any(rating is None for rating in component_ratings):
        return PlayerRatingsPersistenceResult(
            "SKIPPED_INCOMPLETE", None, None, result.skipped_components
        )

    player = db.query(Player).filter(Player.mlb_id == result.mlb_id).one_or_none()
    if player is None:
        raise ValueError(f"sin Player para mlb_id={result.mlb_id}")
    player_season = db.query(PlayerSeason).filter_by(
        player_id=player.id,
        season=season,
        data_start_date=data_start_date,
        data_end_date=data_end_date,
    ).one_or_none()
    if player_season is None:
        raise ValueError("sin PlayerSeason para el snapshot solicitado")
    distribution_versions = {
        result.contact.distribution_version,
        result.power.distribution_version,
        result.vision.distribution_version,
    }
    if len(distribution_versions) != 1:
        raise ValueError("los componentes usan distribution_version diferentes")
    distribution_version = distribution_versions.pop()
    input_hash = _effective_batter_input_hash(
        result,
        player_season_id=player_season.id,
        season=season,
        data_start_date=data_start_date,
        data_end_date=data_end_date,
    )
    identity = {
        "player_id": player.id,
        "season": season,
        "role": "BATTER",
        "rating_model_version": result.model_version,
        "distribution_version": distribution_version,
        "data_start_date": data_start_date,
        "data_end_date": data_end_date,
    }
    ratings = {
        "contact_rating": result.contact.rating,
        "power_rating": result.power.rating,
        "vision_rating": result.vision.rating,
        "clutch_rating": result.clutch.rating,
        "velocity_rating": None,
        "control_rating": None,
        "movement_rating": None,
        "stuff_rating": None,
        "overall_rating": result.overall_rating,
    }
    row = db.query(PlayerRatings).filter_by(**identity).one_or_none()
    if row is None:
        row = PlayerRatings(**identity, **ratings, input_hash=input_hash)
        db.add(row)
        db.commit()
        return PlayerRatingsPersistenceResult("CREATED", row.id, input_hash)
    if row.input_hash == input_hash:
        return PlayerRatingsPersistenceResult("UNCHANGED", row.id, input_hash)
    for field_name, value in ratings.items():
        setattr(row, field_name, value)
    row.input_hash = input_hash
    db.commit()
    return PlayerRatingsPersistenceResult("UPDATED", row.id, input_hash)
