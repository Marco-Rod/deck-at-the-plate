"""
Servicio de telemetría del Matchup Engine V1
============================================
``build_pitch_event_log_payload`` es un builder PURO: valida y construye el
payload de un PitchEventLog a partir de lo que el engine ya conoce al resolver
un pitch. No toca la base de datos ni el estado de la partida.

Por qué NO está conectado a ``resolve_swing``:
    El motor actual no produce aún ``approach`` ni ``probability_distribution``
    (esos conceptos pertenecen al Matchup Engine V1). Escribir telemetría
    fabricando datos solo contaminaría el dataset que se usará para balancear.
    Cuando el V1 se active, el engine debe llamar a este builder y a
    ``record_pitch_event`` (repositories) justo DESPUÉS de resolver el pitch,
    nunca antes (secretos del rival fuera del registro).

Regla del modelo: el log se escribe post-resolución y no contiene secretos.
"""

from typing import Optional

from app.core.enums import BatterApproach, PitchFamily

# Tolerancia para que "la suma de la distribución ≈ 1" no falle por
# errores de coma flotante al normalizar pesos.
_DISTRIBUTION_TOLERANCE = 0.01


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _validate_zone(value: Optional[int], field: str) -> None:
    if value is not None and not (1 <= value <= 9):
        raise ValueError(f"{field} debe estar entre 1 y 9, se obtuvo {value}")


def build_pitch_event_log_payload(
    *,
    game_id: str,
    plate_appearance_id: str,
    pitch_number: int,
    batter_card_id: str,
    pitcher_card_id: str,
    batter_approach: BatterApproach,
    pitcher_zone_choice: int,
    pitch_type: str,
    pitch_family: PitchFamily,
    probability_distribution: dict,
    result: str,
    engine_version: str,
    batter_zone_choice: Optional[int] = None,
    zone_match: bool = False,
    approach_match: Optional[bool] = None,
    balls_before: int = 0,
    strikes_before: int = 0,
    outs_before: int = 0,
    pitcher_fatigue: Optional[float] = None,
    tactical_modifiers: Optional[dict] = None,
    matchup_inputs: Optional[dict] = None,
    rng_value: Optional[float] = None,
    batter_player_id: Optional[str] = None,
    pitcher_player_id: Optional[str] = None,
) -> dict:
    """Valida y construye el payload de un PitchEventLog.

    Todos los argumentos son keyword-only para que la llamada desde el engine
    sea explícita y no dependa del orden.

    Raises:
        ValueError: si algún invariante de dominio no se cumple
            (pitch_number >= 1, zonas 1-9, distribución ≈ 1, etc.).
    """
    _require(bool(game_id), "game_id es obligatorio")
    _require(bool(plate_appearance_id), "plate_appearance_id es obligatorio")
    _require(bool(batter_card_id), "batter_card_id es obligatorio")
    _require(bool(pitcher_card_id), "pitcher_card_id es obligatorio")
    _require(pitch_number >= 1, "pitch_number debe ser >= 1")
    _require(0 <= balls_before <= 3, "balls_before debe estar entre 0 y 3")
    _require(0 <= strikes_before <= 2, "strikes_before debe estar entre 0 y 2")
    _require(0 <= outs_before <= 2, "outs_before debe estar entre 0 y 2")
    _validate_zone(batter_zone_choice, "batter_zone_choice")
    _validate_zone(pitcher_zone_choice, "pitcher_zone_choice")
    _require(bool(pitch_type), "pitch_type es obligatorio")
    _require(bool(result), "result es obligatorio")
    _require(bool(engine_version), "engine_version es obligatorio")
    _require(isinstance(probability_distribution, dict) and probability_distribution,
             "probability_distribution debe ser un dict no vacío")
    _require(
        abs(sum(probability_distribution.values()) - 1.0) <= _DISTRIBUTION_TOLERANCE,
        f"probability_distribution debe sumar ≈ 1.0 (suma={sum(probability_distribution.values()):.4f})",
    )

    # REACT/TAKE no seleccionan zona (el MAE del V1 lo documenta). Un TAKE con
    # zona explícita es una contradicción de dominio.
    if batter_approach == BatterApproach.TAKE and batter_zone_choice is not None:
        raise ValueError("TAKE no define batter_zone_choice (la zona la impone el pitch)")

    # distribution es el corte final ANTES del RNG: rng_value es opcional y
    # nunca se exige (los logs de fallback de infraestructura pueden omitirlo).
    payload = {
        "game_id": game_id,
        "plate_appearance_id": plate_appearance_id,
        "pitch_number": pitch_number,
        "batter_card_id": batter_card_id,
        "pitcher_card_id": pitcher_card_id,
        "batter_player_id": batter_player_id,
        "pitcher_player_id": pitcher_player_id,
        "batter_zone_choice": batter_zone_choice,
        "batter_approach": batter_approach,
        "pitcher_zone_choice": pitcher_zone_choice,
        "pitch_type": pitch_type,
        "pitch_family": pitch_family,
        "zone_match": zone_match,
        "approach_match": approach_match,
        "balls_before": balls_before,
        "strikes_before": strikes_before,
        "outs_before": outs_before,
        "pitcher_fatigue": pitcher_fatigue,
        "tactical_modifiers": tactical_modifiers,
        "matchup_inputs": matchup_inputs,
        "probability_distribution": probability_distribution,
        "rng_value": rng_value,
        "result": result,
        "engine_version": engine_version,
    }
    return payload