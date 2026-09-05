"""Carga idempotente de RawPitchEvent (spec secciones 19 y 22).

Clave natural (game_pk, at_bat_number, pitch_number):

    same key + same hash  → no-op
    same key + diff hash  → UPDATE controlado
    new key               → INSERT

Nunca se borra una ventana para reinsertarla en una ejecución incremental.
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Iterable

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models import RawPitchEvent

logger = logging.getLogger("etl.loaders.raw")


@dataclass
class RawUpsertResult:
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    rejected: int = 0
    details: list[str] = field(default_factory=list)


def upsert_raw_pitch_events(
    db: Session,
    *,
    import_run_id: str,
    rows: Iterable[dict],
    refresh: bool = False,
) -> RawUpsertResult:
    """Upsert por lotes contra la clave natural. rows son dicts de normalize_row."""
    result = RawUpsertResult()
    rows = list(rows)
    if not rows:
        return result

    existing = _fetch_existing(db, rows)
    for row in rows:
        key = (row["game_pk"], row["at_bat_number"], row["pitch_number"])
        event = existing.get(key)
        if event is None:
            db.add(
                RawPitchEvent(
                    id=str(uuid.uuid4()),
                    import_run_id=import_run_id,
                    **row,
                )
            )
            result.inserted += 1
            continue

        if not refresh and event.raw_payload_hash == row["raw_payload_hash"]:
            result.unchanged += 1
            continue

        for field_name, value in row.items():
            setattr(event, field_name, value)
        event.import_run_id = import_run_id
        result.updated += 1
        result.details.append(
            f"update game_pk={row['game_pk']} at_bat={row['at_bat_number']} pitch={row['pitch_number']}"
        )

    db.flush()
    if result.updated:
        logger.info("raw updated=%s inserted=%s unchanged=%s", result.updated, result.inserted, result.unchanged)
    else:
        logger.info("raw inserted=%s unchanged=%s", result.inserted, result.unchanged)
    return result


def _fetch_existing(db: Session, rows: list[dict]) -> dict[tuple, RawPitchEvent]:
    conditions = []
    for row in rows:
        conditions.append(
            and_(
                RawPitchEvent.game_pk == row["game_pk"],
                RawPitchEvent.at_bat_number == row["at_bat_number"],
                RawPitchEvent.pitch_number == row["pitch_number"],
            )
        )
    if not conditions:
        return {}
    events = db.query(RawPitchEvent).filter(or_(*conditions)).all()
    return {(e.game_pk, e.at_bat_number, e.pitch_number): e for e in events}