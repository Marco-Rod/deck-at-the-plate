"""
Servicio de telemetría del Matchup Engine V1
============================================
``build_pitch_event_log_payload`` es un builder PURO: valida y construye el
payload de un PitchEventLog a partir de lo que el engine ya conoce al resolver
un pitch. No toca la base de datos ni el estado de la partida.

Por qué está conectado (P5-A):
    ``resolve_swing`` llama a este builder y a ``record_pitch_event`` justo
    DESPUÉS de resolver el pitch, nunca antes (secretos del rival fuera del
    registro). La distribución final ex-ante y el ``rng_value`` provienen del
    trace aditivo del calculator: no se fabrica ningún dato. ``pitch_family_for_runtime``
    traduce el ``pitch_type`` del runtime a la familia del log.

Regla del modelo: el log se escribe post-resolución y no contiene secretos.
"""

from typing import Optional

from app.core.enums import BatterApproach, PitchFamily, PitchType, SwingType

# Tolerancia para que "la suma de la distribución ≈ 1" no falle por
# errores de coma flotante al normalizar pesos.
_DISTRIBUTION_TOLERANCE = 0.01

# Familia de cada PitchType del runtime (códigos del juego, no Statcast).
# La clasificación de códigos Statcast vive en el ETL (etl/normalizers/);
# esta es la del motor, que habla en valores propios de PitchType. IBB no es
# un lanzamiento real pero sí un pitch del log: se clasifica como OTHER.
_PITCH_FAMILY_BY_TYPE_V1: dict[PitchType, PitchFamily] = {
    PitchType.FOUR_SEAM: PitchFamily.FASTBALL,
    PitchType.SINKER: PitchFamily.FASTBALL,
    PitchType.CUTTER: PitchFamily.FASTBALL,
    PitchType.SLIDER: PitchFamily.BREAKING,
    PitchType.CURVE: PitchFamily.BREAKING,
    PitchType.CHANGE: PitchFamily.OFFSPEED,
    PitchType.IBB: PitchFamily.OTHER,
}


def pitch_family_for_runtime(pitch_type: str) -> PitchFamily:
    """Familia del lanzamiento para el log de telemetría del runtime.

    Un pitch_type desconocido (carta legacy fuera del repertorio V1) se
    normaliza a ``OTHER``: nunca se inventa una familia (regla idéntica a la
    del ETL, donde un código sin política → None con warning).
    """
    try:
        p_type = PitchType(pitch_type)
    except ValueError:
        return PitchFamily.OTHER
    return _PITCH_FAMILY_BY_TYPE_V1.get(p_type, PitchFamily.OTHER)


def batter_approach_for_runtime(
    swing_type: str, guessed_pitch: Optional[str]
) -> BatterApproach:
    """Traduce la decisión del bateador del runtime al dominio V1.

    El runtime decide con ``swing_type`` (NORMAL/POWER/TAKE/BUNT) y, opcionalmente,
    ``guessed_pitch`` (un código de lanzamiento concreto). El Matchup Engine V1
    abstrae esa apuesta al nivel de familia: sólo FASTBALL y BREAKING son
    "approaches" seleccionables (``PitchFamily.OTHER no es seleccionable``).

    Reglas:
      - ``swing_type == TAKE``                → ``TAKE`` (no hay swing).
      - apuesta a familia FASTBALL            → ``FASTBALL``.
      - apuesta a familia BREAKING            → ``BREAKING``.
      - sin apuesta, OFFSPEED o desconocido   → ``REACT``.

    No fabrica: deriva la etiqueta V1 de la propia decisión del bateador.
    """
    if swing_type == SwingType.TAKE:
        return BatterApproach.TAKE
    if not guessed_pitch:
        return BatterApproach.REACT
    family = pitch_family_for_runtime(guessed_pitch)
    if family == PitchFamily.FASTBALL:
        return BatterApproach.FASTBALL
    if family == PitchFamily.BREAKING:
        return BatterApproach.BREAKING
    return BatterApproach.REACT


def approach_match_for_runtime(
    approach: BatterApproach, actual_pitch: Optional[str]
) -> Optional[bool]:
    """Acierto del approach V1: ¿la familia del pitch real coincidió con la apuesta?

    ``None`` para ``REACT``/``TAKE``: no hay acierto binario (definición del
    modelo, igual que una zona no apostada no tiene ``zone_match``).
    Para ``FASTBALL``/``BREAKING`` compara FAMILIAS (nivel V1). El acierto exacto
    del motor pre-V1 (``guessed_pitch == pitch_type``) queda reconstruible desde
    ``matchup_inputs``; por eso NO se confunde con el premio del engine.
    """
    if approach == BatterApproach.FASTBALL:
        return pitch_family_for_runtime(actual_pitch) == PitchFamily.FASTBALL
    if approach == BatterApproach.BREAKING:
        return pitch_family_for_runtime(actual_pitch) == PitchFamily.BREAKING
    return None


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