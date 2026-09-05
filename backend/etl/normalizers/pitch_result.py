"""Normalización del resultado del pitch (spec sección 16).

El raw conserva SIEMPRE el `description` original; estos clasificadores solo
enriquecen. is_whiff NO se infiere de "S" porque un called strike también es
strike: la fuente de verdad es el `description` de Statcast.
"""

import enum
import logging
from typing import Optional

logger = logging.getLogger("etl.normalizers.pitch_result")


class PitchResult(str, enum.Enum):
    BALL = "BALL"
    CALLED_STRIKE = "CALLED_STRIKE"
    SWINGING_STRIKE = "SWINGING_STRIKE"
    FOUL = "FOUL"
    IN_PLAY = "IN_PLAY"
    HBP = "HBP"
    OTHER = "OTHER"


_PITCH_RESULT_BY_DESCRIPTION = {
    "ball": PitchResult.BALL,
    "blocked_ball": PitchResult.BALL,
    "pitchout": PitchResult.BALL,
    "auto_ball": PitchResult.BALL,
    "called_strike": PitchResult.CALLED_STRIKE,
    "swinging_strike": PitchResult.SWINGING_STRIKE,
    "swinging_strike_blocked": PitchResult.SWINGING_STRIKE,
    "foul": PitchResult.FOUL,
    "foul_tip": PitchResult.FOUL,
    "foul_bunt": PitchResult.FOUL,
    "bunt_foul_tip": PitchResult.FOUL,
    "foul_pitchout": PitchResult.FOUL,
    "hit_into_play": PitchResult.IN_PLAY,
    "hit_into_play_no_out": PitchResult.IN_PLAY,
    "hit_into_play_score": PitchResult.IN_PLAY,
    "hit_by_pitch": PitchResult.HBP,
    "hit_by_pitch_blocked": PitchResult.HBP,
}

_SWING_DESCRIPTIONS = {
    "swinging_strike",
    "swinging_strike_blocked",
    "foul",
    "foul_tip",
    "foul_bunt",
    "bunt_foul_tip",
    "foul_pitchout",
    "missed_bunt",
    "hit_into_play",
    "hit_into_play_no_out",
    "hit_into_play_score",
}

_WHIFF_DESCRIPTIONS = {
    "swinging_strike",
    "swinging_strike_blocked",
    "missed_bunt",
}


def _clean(description: Optional[str]) -> Optional[str]:
    if description is None:
        return None
    return description.strip().lower() or None


def normalize_pitch_result(description: Optional[str]) -> PitchResult:
    key = _clean(description)
    if key in _PITCH_RESULT_BY_DESCRIPTION:
        return _PITCH_RESULT_BY_DESCRIPTION[key]
    if key is not None:
        logger.debug("pitch description desconocida -> OTHER: %r", description)
    return PitchResult.OTHER


def is_swing(description: Optional[str]) -> bool:
    return _clean(description) in _SWING_DESCRIPTIONS


def is_whiff(description: Optional[str]) -> bool:
    return _clean(description) in _WHIFF_DESCRIPTIONS