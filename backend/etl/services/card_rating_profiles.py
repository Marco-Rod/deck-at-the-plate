"""Adapta PlayerRatings a ratings de una carta concreta, sin recalcularlos."""

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum

from sqlalchemy.orm import Session

from app.models import CardEdition, CardRatingProfile, PlayerRatings


CARD_RATING_POLICY_VERSION = "card-ratings-1.0"
CARD_RATING_TRANSFORMATION = "IDENTITY_COPY"


@dataclass(frozen=True)
class CardRatingProfileResult:
    status: str
    card_rating_profile_id: str
    source_player_ratings_id: str
    input_hash: str


def _canonical(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    return value


def _ratings_values(ratings: PlayerRatings) -> dict[str, int | None]:
    return {
        "contact_rating": ratings.contact_rating,
        "power_rating": ratings.power_rating,
        "vision_rating": ratings.vision_rating,
        "clutch_rating": ratings.clutch_rating,
        "velocity_rating": ratings.velocity_rating,
        "control_rating": ratings.control_rating,
        "movement_rating": ratings.movement_rating,
        "stuff_rating": ratings.stuff_rating,
        "overall_rating": ratings.overall_rating,
    }


def _provenance(
    ratings: PlayerRatings,
    edition: CardEdition,
    rating_policy_version: str,
) -> dict:
    return {
        "rating_policy_version": rating_policy_version,
        "transformation": CARD_RATING_TRANSFORMATION,
        "source_player_ratings": {
            "id": ratings.id,
            "input_hash": ratings.input_hash,
            "rating_model_version": ratings.rating_model_version,
            "distribution_version": ratings.distribution_version,
            "season": ratings.season,
            "data_start_date": ratings.data_start_date,
            "data_end_date": ratings.data_end_date,
        },
        "card_edition": {
            "id": edition.id,
            "code": edition.code,
            "edition_type": edition.edition_type,
            "season": edition.season,
            "version": edition.version,
            "source_type": edition.source_type,
            "source_reference": edition.source_reference,
            "starts_at": edition.starts_at,
            "ends_at": edition.ends_at,
            "metadata": edition.metadata_payload,
        },
    }


def _input_hash(provenance: dict, ratings_values: dict) -> str:
    payload = {"provenance": provenance, "ratings": ratings_values}
    encoded = json.dumps(
        _canonical(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def generate_card_rating_profile(
    db: Session,
    *,
    source_player_ratings_id: str,
    card_edition_id: str,
    rating_policy_version: str = CARD_RATING_POLICY_VERSION,
) -> CardRatingProfileResult:
    """Crea o actualiza la proyección de ratings para una edición específica."""
    ratings = db.get(PlayerRatings, source_player_ratings_id)
    if ratings is None:
        raise ValueError(f"PlayerRatings inexistente: {source_player_ratings_id}")
    edition = db.get(CardEdition, card_edition_id)
    if edition is None:
        raise ValueError(f"CardEdition inexistente: {card_edition_id}")
    if edition.season != ratings.season:
        raise ValueError("CardEdition y PlayerRatings pertenecen a temporadas distintas")
    if not rating_policy_version or not rating_policy_version.strip():
        raise ValueError("rating_policy_version es obligatorio")

    values = _ratings_values(ratings)
    provenance = _provenance(ratings, edition, rating_policy_version)
    input_hash = _input_hash(provenance, values)
    identity = {
        "player_id": ratings.player_id,
        "card_edition_id": edition.id,
        "role": ratings.role,
        "rating_policy_version": rating_policy_version,
    }
    profile = db.query(CardRatingProfile).filter_by(**identity).one_or_none()
    if profile is not None and profile.input_hash == input_hash:
        return CardRatingProfileResult(
            "UNCHANGED", profile.id, ratings.id, input_hash
        )

    persisted_values = {
        **values,
        "source_player_ratings_id": ratings.id,
        "input_hash": input_hash,
        "metadata_payload": _canonical(provenance),
    }
    if profile is None:
        profile = CardRatingProfile(**identity, **persisted_values)
        db.add(profile)
        status = "CREATED"
    else:
        for field_name, value in persisted_values.items():
            setattr(profile, field_name, value)
        status = "UPDATED"
    db.commit()
    return CardRatingProfileResult(status, profile.id, ratings.id, input_hash)
