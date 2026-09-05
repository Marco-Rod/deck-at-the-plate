"""Mapper que produce el registro normalizado de RawPitchEvent (spec 12-19).

Toma un PitchSourceRecord validado y devuelve el dict con los atributos del
ORM listo para insertar. Las columnas derivadas (pitch_family, game_zone,
raw_payload_hash) se calculan aquí y solo aquí.
"""

import logging
from typing import Optional

from app.core.enums import Handedness, ThrowHand
from etl.dto import PitchSourceRecord
from etl.normalizers.hash import canonical_hash, record_to_hash_payload
from etl.normalizers.pitch_families import map_pitch_family
from etl.normalizers.values import normalize_inning_topbot
from etl.normalizers.zones import game_zone_from_statcast

logger = logging.getLogger("etl.normalizers.raw_mapper")

_VALID_STAND = {"L", "R", "S"}
_VALID_THROWS = {"L", "R"}


def _coerce_stand(value: Optional[str]) -> Optional[Handedness]:
    if value is None:
        return None
    code = value.strip().upper()
    if code not in _VALID_STAND:
        logger.warning("stand inválido ignorado: %r", value)
        return None
    return Handedness(code)


def _coerce_throws(value: Optional[str]) -> Optional[ThrowHand]:
    if value is None:
        return None
    code = value.strip().upper()
    if code not in _VALID_THROWS:
        logger.warning("p_throws inválido ignorado: %r", value)
        return None
    return ThrowHand(code)


def normalize_row(record: PitchSourceRecord) -> dict:
    """dict listo para construir RawPitchEvent en el loader."""
    return {
        "source": "STATCAST",
        "game_pk": record.game_pk,
        "game_date": record.game_date,
        "season": record.season,
        "at_bat_number": record.at_bat_number,
        "pitch_number": record.pitch_number,
        "batter_mlb_id": record.batter_mlb_id,
        "pitcher_mlb_id": record.pitcher_mlb_id,
        "stand": _coerce_stand(record.stand),
        "p_throws": _coerce_throws(record.p_throws),
        "balls": record.balls,
        "strikes": record.strikes,
        "outs_when_up": record.outs_when_up,
        "inning": record.inning,
        "inning_topbot": normalize_inning_topbot(record.inning_topbot),
        "pitch_type": record.pitch_type.strip().upper() if record.pitch_type else None,
        "pitch_family": map_pitch_family(record.pitch_type),
        "release_speed": record.release_speed,
        "release_spin_rate": record.release_spin_rate,
        "pfx_x": record.pfx_x,
        "pfx_z": record.pfx_z,
        "plate_x": record.plate_x,
        "plate_z": record.plate_z,
        "statcast_zone": record.zone,
        "game_zone": game_zone_from_statcast(record.zone),
        "description": record.description.strip() if record.description else None,
        "event": record.events.strip() if record.events else None,
        "bb_type": record.bb_type.strip() if record.bb_type else None,
        "launch_speed": record.launch_speed,
        "launch_angle": record.launch_angle,
        "estimated_woba": record.estimated_woba_using_speedangle,
        "woba_value": record.woba_value,
        "home_team": record.home_team.strip().upper() if record.home_team else None,
        "away_team": record.away_team.strip().upper() if record.away_team else None,
        "raw_payload_hash": canonical_hash(record_to_hash_payload(record)),
    }