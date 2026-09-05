"""Pipeline de ingestión RAW Statcast (spec secciones 20-22).

Create DataImportRun → split window → fetch CSV → validate headers → parse →
validate row → normalize → bulk upsert → update counters, por chunk con commit.
Los pedidos HTTP ocurren SIEMPRE fuera de transacción abierta.
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
        result = StatcastRunResult()
        run = self._create_run(date_from=date_from, date_to=date_to, season=season, player_type=player_type)
        result.import_run_id = run.id
        try:
            for window_from, window_to in split_date_ranges(date_from, date_to, self._chunk_days):
                records = self._adapter.fetch_date_range(window_from, window_to, player_type=player_type)
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

                self._update_run(run, result, include_extracted=True)
                self._db.commit()
                logger.info(
                    "chunk %s..%s: extracted=%s inserted=%s updated=%s unchanged=%s",
                    window_from,
                    window_to,
                    len(records),
                    upsert.inserted,
                    upsert.updated,
                    upsert.unchanged,
                )

            run.status = ImportStatus.SUCCESS
        except Exception as exc:
            self._db.rollback()
            run.status = ImportStatus.FAILED
            run.error_summary = str(exc)[:2000]
            logger.exception("statcast pipeline falló")
        finally:
            run.finished_at = utcnow()
            self._db.commit()
        return result

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

    def _update_run(self, run: DataImportRun, result: StatcastRunResult, *, include_extracted: bool) -> None:
        run.rows_extracted = result.rows_extracted if include_extracted else run.rows_extracted
        run.rows_inserted = result.rows_inserted
        run.rows_updated = result.rows_updated
        run.rows_rejected = result.rows_rejected