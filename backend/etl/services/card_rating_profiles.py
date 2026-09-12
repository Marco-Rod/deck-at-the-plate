"""Adapta PlayerRatings a ratings de una carta concreta, sin recalcularlos."""

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Mapping

from sqlalchemy.orm import Session

from app.models import CardEdition, CardRatingProfile, PlayerRatings
from etl.services.base_evidence_policy import assess_base_evidence
from etl.services.card_rating_policies import (
    CardRatingPolicyResult,
    apply_card_rating_policy,
)


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
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Mapping):
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
    policy: CardRatingPolicyResult,
    calculation_metadata: Mapping | None,
    evidence_assessment: Mapping | None,
) -> dict:
    provenance = {
        "rating_policy_version": policy.policy_version,
        "transformation": policy.transformation,
        "reason": policy.reason,
        "base_ratings": policy.base_ratings,
        "transformed_ratings": policy.transformed_ratings,
        "adjustments": policy.adjustments,
        "overall_policy": {
            "policy_version": policy.overall_policy.policy_version,
            "source": policy.overall_policy.source,
            "component_ratings": policy.overall_policy.component_ratings,
            "weights": policy.overall_policy.weights,
            "raw_score": policy.overall_policy.raw_score,
            "rating": policy.overall_policy.rating,
        },
        "calculation_metadata": _canonical(calculation_metadata or {}),
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
    if evidence_assessment is not None:
        provenance["evidence_assessment"] = _canonical(evidence_assessment)
    return provenance


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
    policy_adjustments: dict[str, int] | None = None,
    policy_reason: str | None = None,
    calculation_metadata: Mapping | None = None,
    commit: bool = True,
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
    policy = apply_card_rating_policy(
        edition_type=edition.edition_type,
        role=ratings.role,
        base_ratings=_ratings_values(ratings),
        adjustments=policy_adjustments,
        reason=policy_reason,
    )
    values = policy.transformed_ratings
    evidence_assessment = None
    if edition.edition_type.value == "BASE":
        evidence_assessment = assess_base_evidence(
            role=ratings.role, player_ratings=ratings
        ).as_dict()
    provenance = _provenance(
        ratings,
        edition,
        policy,
        calculation_metadata,
        evidence_assessment,
    )
    input_hash = _input_hash(provenance, values)
    identity = {
        "player_id": ratings.player_id,
        "card_edition_id": edition.id,
        "role": ratings.role,
        "rating_policy_version": policy.policy_version,
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
    if commit:
        db.commit()
    else:
        db.flush()
    return CardRatingProfileResult(status, profile.id, ratings.id, input_hash)
