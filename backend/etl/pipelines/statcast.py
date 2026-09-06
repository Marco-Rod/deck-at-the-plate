"""Pipeline de ingestión RAW Statcast (spec secciones 20-22, correcciones V1).

Create DataImportRun → split window → fetch CSV (chunking + threshold seguro) →
validate headers → parse → validate row → normalize → bulk upsert → update
counters, por chunk con commit. Los pedidos HTTP ocurren SIEMPRE fuera de
transacción abierta.

Correcciones V1:
- Los errores se propagan tras persistir `DataImportRun = FAILED`.
- `SUCCESS`/`PARTIAL`/`FAILED` semánticamente correctos (rejected > 0 → PARTIAL).
- `run_player` mueve la lógica de `import-statcast-player` fuera de la CLI.
"""

import logging
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from app.core.enums import ImportStatus
from app.core.time import utcnow
from app.models import DataImportRun
from etl.config import ETL_PIPELINE_VERSION
from etl.loaders.raw import upsert_raw_pitch_events
from etl.normalizers.raw_mapper import normalize_row
from etl.sources.statcast import StatcastSourceAdapter, split_date_ranges
from etl.validators.raw import validate_raw_row

logger = logging.getLogger("etl.pipelines.statcast")


@dataclass
class StatcastRunResult:
    rows_extracted: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_unchanged: int = 0
    rows_rejected: int = 0
    rejection_details: list[str] = field(default_factory=list)
    import_run_id: str = ""


class StatcastRawPipeline:
    def __init__(self, db: Session, adapter: StatcastSourceAdapter, *, chunk_days: int = 5) -> None:
        self._db = db
        self._adapter = adapter
        self._chunk_days = chunk_days

    def run(
        self,
        *,
        date_from: date,
        date_to: date,
        season: int | None = None,
        player_type: str = "pitcher",
        refresh: bool = False,
    ) -> StatcastRunResult:
        """Ingesta completa de una ventana (ruta segura con chunking interno)."""
        result = StatcastRunResult()
        run = self._create_run(date_from=date_from, date_to=date_to, season=season, player_type=player_type)
        result.import_run_id = run.id
        try:
            for window_from, window_to in split_date_ranges(date_from, date_to, self._chunk_days):
                records = self._adapter.fetch_date_range(
                    window_from, window_to, player_type=player_type, chunk_days=self._chunk_days
                )
                self._ingest_records(run, result, records, refresh=refresh)
        except Exception as exc:
            self._db.rollback()
            run.status = ImportStatus.FAILED
            run.error_summary = str(exc)[:2000]
            logger.exception("statcast pipeline falló")
            self._finalize_run(run)
            raise
        # Corrección V1: ejecución terminada con rechazos = PARTIAL.
        run.status = ImportStatus.PARTIAL if result.rows_rejected > 0 else ImportStatus.SUCCESS
        self._finalize_run(run)
        return result

    def run_player(
        self,
        *,
        mlb_id: int,
        role: str,
        date_from: date,
        date_to: date,
        season: int | None = None,
        refresh: bool = False,
    ) -> StatcastRunResult:
        """Ingesta RAW de un solo jugador como bater o pitcher (spec correcciones §7)."""
        if role not in ("batter", "pitcher"):
            raise ValueError(f"role inválido: {role}")
        result = StatcastRunResult()
        run = self._create_run(date_from=date_from, date_to=date_to, season=season, player_type=role)
        result.import_run_id = run.id
        try:
            if role == "batter":
                records = self._adapter.fetch_batter(mlb_id, date_from, date_to)
            else:
                records = self._adapter.fetch_pitcher(mlb_id, date_from, date_to)
            self._ingest_records(run, result, records, refresh=refresh)
        except Exception as exc:
            self._db.rollback()
            run.status = ImportStatus.FAILED
            run.error_summary = str(exc)[:2000]
            logger.exception("statcast run_player falló")
            self._finalize_run(run)
            raise
        run.status = ImportStatus.PARTIAL if result.rows_rejected > 0 else ImportStatus.SUCCESS
        self._finalize_run(run)
        return result

    # -------------------------------------------------------------- helpers

    def _ingest_records(self, run: DataImportRun, result: StatcastRunResult, records: list, *, refresh: bool) -> None:
        result.rows_extracted += len(records)

        rows = []
        for record in records:
            errors = validate_raw_row(record)
            if errors:
                result.rows_rejected += 1
                result.rejection_details.append(f"key={record.natural_key}: {errors}")
                logger.warning("raw rechazado key=%s errores=%s", record.natural_key, errors)
                continue
            rows.append(normalize_row(record))

        upsert = upsert_raw_pitch_events(
            self._db, import_run_id=run.id, rows=rows, refresh=refresh
        )
        result.rows_inserted += upsert.inserted
        result.rows_updated += upsert.updated
        result.rows_unchanged += upsert.unchanged
        result.rejection_details.extend(upsert.details)

        run.rows_extracted = result.rows_extracted
        run.rows_inserted = result.rows_inserted
        run.rows_updated = result.rows_updated
        run.rows_rejected = result.rows_rejected
        self._db.commit()
        logger.info(
            "chunk: extracted=%s inserted=%s updated=%s unchanged=%s",
            len(records),
            upsert.inserted,
            upsert.updated,
            upsert.unchanged,
        )

    def _create_run(self, *, date_from, date_to, season, player_type) -> DataImportRun:
        run = DataImportRun(
            source="STATCAST",
            pipeline_version=ETL_PIPELINE_VERSION,
            season=season or date_from.year,
            date_from=date_from,
            date_to=date_to,
            status=ImportStatus.RUNNING,
        )
        self._db.add(run)
        self._db.commit()
        logger.info("data_import_run creado id=%s source=STATCAST", run.id)
        return run

    def _finalize_run(self, run: DataImportRun) -> None:
        run.finished_at = utcnow()
        self._db.commit()