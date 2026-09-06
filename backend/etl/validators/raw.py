"""Validación de filas raw (spec secciones 6 y 22).

Cada fila inválida se cuenta como rechazo; los campos con CHECK en la DB se
validan aquí ANTES de intentar insertar para producir errores legibles.
"""

from typing import Optional

from etl.dto import PitchSourceRecord


VALID_STATCAST_ZONES = frozenset((*range(1, 10), *range(11, 15)))


def _err(messages: list[str], field: str, value, expectation: str) -> None:
    messages.append(f"{field}={value!r}: {expectation}")


def validate_raw_row(record: PitchSourceRecord) -> list[str]:
    errors: list[str] = []

    if not record.game_pk or record.game_pk <= 0:
        _err(errors, "game_pk", record.game_pk, "obligatorio > 0")
    if record.game_date is None:
        _err(errors, "game_date", record.game_date, "obligatorio")
    if record.at_bat_number is None or record.at_bat_number < 1:
        _err(errors, "at_bat_number", record.at_bat_number, "obligatorio >= 1")
    if record.pitch_number is None or record.pitch_number < 1:
        _err(errors, "pitch_number", record.pitch_number, "obligatorio >= 1")
    if not record.batter_mlb_id or record.batter_mlb_id <= 0:
        _err(errors, "batter", record.batter_mlb_id, "obligatorio > 0")
    if not record.pitcher_mlb_id or record.pitcher_mlb_id <= 0:
        _err(errors, "pitcher", record.pitcher_mlb_id, "obligatorio > 0")

    _check_count(errors, "balls", record.balls, 0, 3)
    _check_count(errors, "strikes", record.strikes, 0, 2)
    _check_count(errors, "outs_when_up", record.outs_when_up, 0, 2)
    if record.inning is not None and record.inning < 1:
        _err(errors, "inning", record.inning, ">= 1")

    if record.stand is not None and record.stand.strip().upper() not in {"L", "R", "S"}:
        _err(errors, "stand", record.stand, "L/R/S")
    if record.p_throws is not None and record.p_throws.strip().upper() not in {"L", "R"}:
        _err(errors, "p_throws", record.p_throws, "L/R")

    if record.zone is not None and record.zone not in VALID_STATCAST_ZONES:
        _err(errors, "zone(statcast)", record.zone, "None, 1..9 o 11..14")

    return errors


def _check_count(errors: list[str], field: str, value: Optional[int], lower: int, upper: int) -> None:
    if value is None:
        return
    if not (lower <= value <= upper):
        _err(errors, field, value, f"{lower}..{upper}")
