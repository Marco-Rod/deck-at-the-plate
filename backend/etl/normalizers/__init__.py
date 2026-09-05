"""Normalizadores del ETL (spec secciones 14-19).

Transforman el DTO de fuente en valores canónicos listos para RawPitchEvent y
para los agregados, separando los enriquecimientos derivados (familia, zona de
juego, hash) de la validación.
"""

from etl.normalizers.hash import canonical_hash
from etl.normalizers.pitch_families import map_pitch_family
from etl.normalizers.pitch_result import PitchResult, is_swing, is_whiff, normalize_pitch_result
from etl.normalizers.values import normalize_inning_topbot
from etl.normalizers.zones import game_zone_from_statcast

__all__ = [
    "canonical_hash",
    "map_pitch_family",
    "PitchResult",
    "is_swing",
    "is_whiff",
    "normalize_pitch_result",
    "normalize_inning_topbot",
    "game_zone_from_statcast",
]