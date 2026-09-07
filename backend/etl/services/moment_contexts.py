"""Persistencia idempotente de hechos de un momento, sin evaluarlos."""

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Mapping

from sqlalchemy.orm import Session

from app.models import (
    CardEdition,
    CardEditionType,
    MomentContext,
    MomentContextSourceType,
    Player,
)


MOMENT_CONTEXT_VERSION = "moment-context-1.0"
INTERPRETIVE_FACT_KEYS = frozenset(
    {
        "adjustment",
        "adjustments",
        "boost",
        "boosts",
        "evaluation",
        "performance_tier",
        "rarity",
        "rating",
        "ratings",
        "significance",
    }
)


@dataclass(frozen=True)
class MomentContextPersistenceResult:
    status: str
    moment_context_id: str
    input_hash: str


def _canonical(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"valor factual no serializable: {type(value).__name__}")


def _validate_facts(value, *, path="facts") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized_key = str(key).strip().lower()
            if normalized_key in INTERPRETIVE_FACT_KEYS:
                raise ValueError(f"{path}.{key} pertenece a una capa interpretativa")
            _validate_facts(item, path=f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _validate_facts(item, path=f"{path}[{index}]")
        return
    _canonical(value)


def _context_hash(payload: dict) -> str:
    encoded = json.dumps(
        _canonical(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def persist_moment_context(
    db: Session,
    *,
    player_id: str,
    card_edition_id: str,
    role: str,
    occurred_at: datetime,
    source_type: MomentContextSourceType,
    source_reference: str,
    facts: Mapping,
    context_version: str = MOMENT_CONTEXT_VERSION,
) -> MomentContextPersistenceResult:
    """Guarda hechos observados; nunca calcula importance, boosts o ratings."""
    player = db.get(Player, player_id)
    if player is None:
        raise ValueError(f"Player inexistente: {player_id}")
    edition = db.get(CardEdition, card_edition_id)
    if edition is None:
        raise ValueError(f"CardEdition inexistente: {card_edition_id}")
    if edition.edition_type != CardEditionType.MOMENT:
        raise ValueError("MomentContext solo puede pertenecer a una edición MOMENT")
    if role not in {"BATTER", "PITCHER"}:
        raise ValueError(f"rol no soportado: {role}")
    if occurred_at is None:
        raise ValueError("occurred_at es obligatorio")
    if not source_reference or not source_reference.strip():
        raise ValueError("source_reference es obligatorio")
    if not context_version or not context_version.strip():
        raise ValueError("context_version es obligatorio")
    if not isinstance(facts, Mapping) or not facts:
        raise ValueError("facts debe ser un objeto no vacío")
    _validate_facts(facts)

    normalized_facts = _canonical(facts)
    payload = {
        "player_id": player.id,
        "card_edition_id": edition.id,
        "role": role,
        "season": edition.season,
        "occurred_at": occurred_at,
        "source_type": source_type,
        "source_reference": source_reference.strip(),
        "context_version": context_version.strip(),
        "facts": normalized_facts,
    }
    input_hash = _context_hash(payload)
    identity = {
        "player_id": player.id,
        "card_edition_id": edition.id,
        "role": role,
        "context_version": context_version.strip(),
    }
    context = db.query(MomentContext).filter_by(**identity).one_or_none()
    if context is not None and context.input_hash == input_hash:
        return MomentContextPersistenceResult("UNCHANGED", context.id, input_hash)

    values = {
        "season": edition.season,
        "occurred_at": occurred_at,
        "source_type": source_type,
        "source_reference": source_reference.strip(),
        "facts": normalized_facts,
        "input_hash": input_hash,
    }
    if context is None:
        context = MomentContext(**identity, **values)
        db.add(context)
        status = "CREATED"
    else:
        for field_name, value in values.items():
            setattr(context, field_name, value)
        status = "UPDATED"
    db.commit()
    return MomentContextPersistenceResult(status, context.id, input_hash)
