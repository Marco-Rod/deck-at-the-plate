"""Carga idempotente de RawPitchEvent (spec secciones 19 y 22, corrección §4).

Clave natural (game_pk, at_bat_number, pitch_number):

    same key + same hash  → no-op
    same key + diff hash  → UPDATE controlado
    new key               → INSERT

Estrategia bulk (aprobada en revisión):
    1. Por cada lote (BULK_UPSERT_BATCH_SIZE), se consultan los existentes de la
       clave natural de forma ACOTADA (nunca una query global).
    2. Se clasifica cada fila en insert / update / no-op por hash (o refresh).
    3. Los writes se ejecutan con un único `INSERT ... ON CONFLICT ... DO UPDATE`
       por lote (PostgreSQL en prod, SQLite en tests). La UNIQUE constraint sigue
       siendo la protección final.

Nunca se borra una ventana para reinsertarla en una ejecución incremental.
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Callable, Iterable

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models import RawPitchEvent
from etl.config import BULK_UPSERT_BATCH_SIZE

logger = logging.getLogger("etl.loaders.raw")


@dataclass
class RawUpsertResult:
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    rejected: int = 0
    details: list[str] = field(default_factory=list)


def _natural_key(row: dict) -> tuple:
    return (row["game_pk"], row["at_bat_number"], row["pitch_number"])


def _upsert_insert(db: Session) -> Callable:
    """Devuelve el `insert` con soporte ON CONFLICT según el dialecto."""
    dialect = db.get_bind().dialect.name
    if dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert

        return insert
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert

        return insert
    from sqlalchemy import insert

    return insert


def _to_write_row(row: dict) -> dict:
    """Aporta los campos con default Python-side a un dict para INSERT literal."""
    return {"id": str(uuid.uuid4()), "created_at": utcnow(), **row}


def upsert_raw_pitch_events(
    db: Session,
    *,
    import_run_id: str,
    rows: Iterable[dict],
    refresh: bool = False,
    batch_size: int = BULK_UPSERT_BATCH_SIZE,
) -> RawUpsertResult:
    """Upsert por lotes contra la clave natural. rows son dicts de normalize_row."""
    result = RawUpsertResult()
    rows = list(rows)
    if not rows:
        return result

    for idx in range(0, len(rows), batch_size):
        batch = rows[idx : idx + batch_size]
        result_at = _upsert_batch(db, import_run_id=import_run_id, batch=batch, refresh=refresh)
        result.inserted += result_at.inserted
        result.updated += result_at.updated
        result.unchanged += result_at.unchanged
        result.details.extend(result_at.details)

    if result.updated:
        logger.info("raw bulk: updated=%s inserted=%s unchanged=%s", result.updated, result.inserted, result.unchanged)
    else:
        logger.info("raw bulk: inserted=%s unchanged=%s", result.inserted, result.unchanged)
    return result


def _upsert_batch(
    db: Session,
    *,
    import_run_id: str,
    batch: list[dict],
    refresh: bool,
) -> RawUpsertResult:
    result = RawUpsertResult()

    # 1. Probe ACOTADO: solo las claves de este lote.
    existing = _fetch_existing_for_batch(db, batch)
    insert_rows: list[dict] = []
    update_rows: list[dict] = []
    for row in batch:
        key = _natural_key(row)
        event = existing.get(key)
        if event is None:
            insert_rows.append(_to_write_row({**row, "import_run_id": import_run_id}))
            result.inserted += 1
            continue

        if not refresh and event.raw_payload_hash == row["raw_payload_hash"]:
            result.unchanged += 1
            continue

        update_rows.append(_to_write_row({**row, "import_run_id": import_run_id}))
        result.updated += 1
        result.details.append(
            f"update game_pk={row['game_pk']} at_bat={row['at_bat_number']} pitch={row['pitch_number']}"
        )

    # 2. Bulk write: un único ON CONFLICT DO UPDATE por lote.
    write_rows = insert_rows + update_rows
    if not write_rows:
        return result

    table = RawPitchEvent.__table__
    values = list(write_rows)
    # En ON CONFLICT actualizamos los campos de negocio (no id/created_at).
    set_cols = [c for c in write_rows[0].keys() if c not in ("id", "created_at")]

    insert = _upsert_insert(db)
    stmt = insert(table).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=[
            table.c.game_pk,
            table.c.at_bat_number,
            table.c.pitch_number,
        ],
        set_={col: stmt.excluded[col] for col in set_cols},
    )
    db.execute(stmt)

    return result


def _fetch_existing_for_batch(db: Session, batch: list[dict]) -> dict[tuple, RawPitchEvent]:
    """Consulta existentes SOLO para las claves de este lote (acotado)."""
    from sqlalchemy import and_, or_

    conditions = []
    for row in batch:
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
    return {
        _natural_key({"game_pk": e.game_pk, "at_bat_number": e.at_bat_number, "pitch_number": e.pitch_number}): e
        for e in events
    }