"""Mapping pitch_type → pitch_family (spec sección 15).

Versión V1 centralizada aquí: el pipeline nunca repite estas clasificaciones.
Códigos sin política explícita se normalizan a None (con warning) y nunca a
una familia inventada: si un día llega un código nuevo, aparece en los logs.
"""

import logging

from app.core.enums import PitchFamily

logger = logging.getLogger("etl.normalizers.pitch_families")


def _build_mapping_v1() -> dict[str, PitchFamily]:
    fastball = {"FF", "SI", "FT", "FC", "FA"}
    breaking = {"SL", "ST", "CU", "KC", "CS", "SV"}
    offspeed = {"CH", "FS", "FO", "SC"}
    mapping: dict[str, PitchFamily] = {}
    for code in fastball:
        mapping[code] = PitchFamily.FASTBALL
    for code in breaking:
        mapping[code] = PitchFamily.BREAKING
    for code in offspeed:
        mapping[code] = PitchFamily.OFFSPEED
    for code in ("KN", "EP", "IN", "PO"):
        mapping[code] = PitchFamily.OTHER
    return mapping


PITCH_FAMILY_MAPPING_V1: dict[str, PitchFamily] = _build_mapping_v1()


def map_pitch_family(pitch_type: str | None) -> PitchFamily | None:
    """Devuelve la familia V1 del código Statcast o None si es desconocido."""
    if pitch_type is None:
        return None
    code = pitch_type.strip().upper()
    if not code:
        return None
    family = PITCH_FAMILY_MAPPING_V1.get(code)
    if family is None:
        logger.warning("pitch_type sin familia V1: %r", pitch_type)
        return None
    return family