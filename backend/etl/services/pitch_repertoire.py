"""Adaptación explícita de arsenales Statcast al repertorio del motor.

Statcast identifica pitcheos con códigos como ``FF`` o ``SL``; el runtime usa
un vocabulario pequeño y estable (``4-SEAM``, ``SLIDER``, etc.). Esta política
convierte sólo los códigos que tienen una representación V1 clara y omite los
que aún no están soportados por el motor. Nunca inventa un pitch desconocido.

V1 materializa tipos y uso reales. Los atributos específicos de cada pitcheo
no se derivan todavía: ``game_actions`` cae deliberadamente en los atributos
globales del pitcher hasta que exista una política de escala por pitch.
"""

from __future__ import annotations

from typing import Iterable


# Statcast code -> PitchType del runtime. Variantes cercanas se agrupan en la
# opción jugable más próxima; los tipos sin equivalente se omiten por ahora.
STATCAST_TO_RUNTIME_PITCH: dict[str, str] = {
    "FF": "4-SEAM",
    "FA": "4-SEAM",
    "SL": "SLIDER",
    "ST": "SLIDER",
    "CH": "CHANGE",
    "FS": "CHANGE",
    "FO": "CHANGE",
    "SC": "CHANGE",
    "CU": "CURVE",
    "KC": "CURVE",
    "CS": "CURVE",
    "SV": "CURVE",
    "SI": "SINKER",
    "FT": "SINKER",
    "FC": "CUTTER",
}


def build_runtime_repertoire(profiles: Iterable[object], *, maximum_pitches: int = 4) -> list[dict]:
    """Devuelve hasta cuatro pitcheos utilizables, ordenados por uso real.

    Cuando varias variantes Statcast colapsan al mismo tipo del runtime, se
    conserva la de mayor uso. ``source_pitch_type`` mantiene la procedencia
    para auditoría y una futura política de atributos específicos.
    """
    candidates: list[dict] = []
    for profile in profiles:
        source_type = str(getattr(profile, "pitch_type", "") or "").upper()
        runtime_type = STATCAST_TO_RUNTIME_PITCH.get(source_type)
        pitch_count = int(getattr(profile, "pitch_count", 0) or 0)
        if runtime_type is None or pitch_count <= 0:
            continue
        family = getattr(profile, "pitch_family", None)
        candidates.append(
            {
                "pitch_type": runtime_type,
                "source_pitch_type": source_type,
                "pitch_family": getattr(family, "value", family),
                "usage": float(getattr(profile, "usage_rate", 0) or 0),
                "pitch_count": pitch_count,
            }
        )
    candidates.sort(key=lambda item: (-item["pitch_count"], item["pitch_type"], item["source_pitch_type"]))
    unique: list[dict] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate["pitch_type"] in seen:
            continue
        seen.add(candidate["pitch_type"])
        unique.append(candidate)
        if len(unique) == maximum_pitches:
            break
    return unique
