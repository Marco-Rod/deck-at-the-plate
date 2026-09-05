"""Data quality report de cada run (spec §37-§42, §46).

Emite el resumen del run en consola/log estructurado; V1 puede ser orientativo
(§41 permite empezar en consola).
"""

import logging
from dataclasses import dataclass, field

from app.models import RawPitchEvent
from etl.pipelines.statcast import StatcastRunResult
from etl.aggregators.metrics import PitchView

logger = logging.getLogger("etl.services.quality")


@dataclass
class QualitySummary:
    run_id: str = ""
    source: str = ""
    window_from: str = ""
    window_to: str = ""
    rows_extracted: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_rejected: int = 0
    unknown_pitch_types: list[str] = field(default_factory=list)
    missing_velocity_pct: float = 0.0
    missing_spin_pct: float = 0.0
    missing_plate_location_pct: float = 0.0
    players_resolved: int = 0
    players_unresolved: int = 0


def collect_quality(
    *,
    run_result: StatcastRunResult | None = None,
    pitches: list[RawPitchEvent] | None = None,
    unknown_pitch_types: list[str] | None = None,
) -> QualitySummary:
    summary = QualitySummary()
    if run_result is not None:
        summary.run_id = run_result.import_run_id
        summary.source = "STATCAST"
        summary.rows_extracted = run_result.rows_extracted
        summary.rows_inserted = run_result.rows_inserted
        summary.rows_updated = run_result.rows_updated
        summary.rows_rejected = run_result.rows_rejected

    if unknown_pitch_types:
        summary.unknown_pitch_types = sorted(set(unknown_pitch_types))

    if pitches:
        n = len(pitches)
        speed_missing = sum(1 for p in pitches if p.release_speed is None)
        spin_missing = sum(1 for p in pitches if p.release_spin_rate is None)
        location_missing = sum(1 for p in pitches if p.plate_x is None or p.plate_z is None)
        summary.missing_velocity_pct = round(speed_missing / n * 100, 2)
        summary.missing_spin_pct = round(spin_missing / n * 100, 2)
        summary.missing_plate_location_pct = round(location_missing / n * 100, 2)

    return summary


def emit_quality_report(summary: QualitySummary) -> None:
    logger.info(
        "quality run=%s source=%s extracted=%s inserted=%s updated=%s rejected=%s "
        "unknown_pitch_types=%s missing_velocity%%=%s missing_spin%%=%s missing_location%%=%s",
        summary.run_id,
        summary.source,
        summary.rows_extracted,
        summary.rows_inserted,
        summary.rows_updated,
        summary.rows_rejected,
        summary.unknown_pitch_types,
        summary.missing_velocity_pct,
        summary.missing_spin_pct,
        summary.missing_plate_location_pct,
    )