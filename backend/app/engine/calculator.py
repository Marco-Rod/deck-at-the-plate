"""
Módulo: calculator
==================
Motor matemático del at-bat. Implementa la resolución de una jugada mediante
RNG ponderado calibrado con métricas reales de MLB (Statcast).

Flujo de resolución:
    1. TAKE:        El bateador no hace swing. Se evalúa si el pitcheo era strike
                    basándose en el control del pitcher y la visión del bateador.
    2. Whiff:       Si el bateador hace swing, se calcula la tasa de fallo (whiff%)
                    usando velocidad y movimiento del pitcher vs contacto del bateador.
    3. Foul:        Si hace contacto pero no conectó limpio, probabilidad de foul (~45%).
    4. BABIP:       Bola en juego. Se calcula un power_score que determina el tipo
                    de hit u out según umbrales empíricos de MLB.

Rangos de los eventos en bolas en juego (power_score 0–115 aprox.):
    > 96  → HOME_RUN   (~3%)
    93–96 → HIT_3B     (~2%)
    85–93 → HIT_2B     (~8%)
    63–85 → HIT_1B    (~22%)
    25–63 → OUT_GROUND (~42%)
    < 25  → OUT_FLY    (~23%)

Este módulo es PURAMENTE FUNCIONAL: recibe DTOs tipados de ``app.core`` y
retorna un ``PlayResult`` (NamedTuple), sin dependencias de la infraestructura
(no importa SQLAlchemy ni FastAPI) → cumple DIP (D de SOLID).
"""
import random

from app.core.enums import Event, PitchType, SwingType
from app.core.engine_types import (
    BatterAttrs,
    PitchSelection,
    PitcherAttrs,
    PlayResult,
    SwingSelection,
    TacticsModifiers,
)
from app.engine.stuff_policy import STUFF_BASELINE, stuff_power_suppression


# --- Política de producción del TAKE/contacto (002E-4 · PROMOTE) ---
# Calibración validada en las series 002C/002E y PROMOVIDA a producción en
# 002E-4. La API pública calculate_play_outcome() usa SIEMPRE estas constantes;
# los knobs LAB (take_bias / foul_chance / take_floor) sólo existen en
# _resolve_play_outcome(), el resolver que comparten producción y el harness de
# disciplina (scripts/simulate_fatigue_impact.py) — una sola fórmula, cero
# duplicación, y la API de gameplay queda sin knobs experimentales. Los knobs
# resuelven None → estas constantes productivas.
TAKE_BASE_STRIKE_CHANCE = 0.30      # Baseline de strike_chance en TAKE (002E-4)
TAKE_STRIKE_CHANCE_FLOOR = 0.20     # Piso del clamp (CLAMP-001: 0.25 → 0.20)
TAKE_STRIKE_CHANCE_CEILING = 0.85   # Techo del clamp (sin cambios desde 002C)
CONTROL_TAKE_WEIGHT = 0.003         # Peso del control del pitcher en strike_chance
VISION_TAKE_WEIGHT = 0.002          # Peso de la visión del bateador en strike_chance
_ZONE_MATCH_BONUS = 0.12            # Bono por anticipar la zona correcta en TAKE
FOUL_ON_CONTACT_CHANCE = 0.45       # Foul/contact en los contactos no-limpios (002E-4)

# La política de Stuff (GAMEPLAY-ENGINE-003B: STUFF_BASELINE,
# STUFF_POWER_SUPPRESSION, α) NO se re-declara aquí. Vive entera en
# app/engine/stuff_policy.py y este módulo la importa, para que el número
# congelado tenga una sola definición en todo el código productivo.


def calculate_play_outcome(
    pitcher_attrs: PitcherAttrs,
    batter_attrs: BatterAttrs,
    pitch_selected: PitchSelection,
    swing_selected: SwingSelection,
    tactics_modifiers: TacticsModifiers = None,
) -> PlayResult:
    """
    Calcula el resultado de la jugada aplicando RNG ponderado basado en atributos de Statcast.

    Args:
        pitcher_attrs: Atributos globales de la carta del pícher (claves en español).
        batter_attrs: Atributos globales de la carta del bateador (claves en español).
        pitch_selected: Diccionario con la zona y picheo lanzado.
                        Ejemplo: {
                            "zone": 5,
                            "pitch_type": "SLIDER",
                            "velocity": 85,  # (Opcional) Especifico del repertorio
                            "control": 88,   # (Opcional) Especifico del repertorio
                            "movement": 94   # (Opcional) Especifico del repertorio
                        }
        swing_selected: Diccionario con el tipo de swing y predicción.
        tactics_modifiers: Modificadores aplicados por cartas tácticas.

    Retorna: PlayResult(event, description)

    API pública de producción: NO acepta overrides experimentales. Los knobs
    LAB (take_bias / foul_chance) viven en _resolve_play_outcome(), al que
    ésta delega con los valores de producción.
    """
    return _resolve_play_outcome(
        pitcher_attrs, batter_attrs, pitch_selected, swing_selected, tactics_modifiers,
    )


def _resolve_play_outcome(
    pitcher_attrs: PitcherAttrs,
    batter_attrs: BatterAttrs,
    pitch_selected: PitchSelection,
    swing_selected: SwingSelection,
    tactics_modifiers: TacticsModifiers = None,
    take_bias: float = None,
    foul_chance: float = None,
    take_floor: float = None,
) -> PlayResult:
    """Resolución completa de una jugada con knobs LAB (002C-B / 002C-C / 002E-4).

    take_bias:   baseline de strike_chance en TAKE; None → producción
                 (TAKE_BASE_STRIKE_CHANCE = 0.30).
    foul_chance: fracción de FOUL sobre contactos no-limpios; None →
                 producción (FOUL_ON_CONTACT_CHANCE = 0.45).
    take_floor:  piso inferior del clamp de strike_chance en TAKE; None →
                 producción (TAKE_STRIKE_CHANCE_FLOOR = 0.20).
                 0.0 → sin piso inferior (solo cap superior 0.85).

    LAB overrides (SÓLO para el harness experimental): producen los mismos
    valores históricos que el engine ya validó (PROD histórico 0.65/0.35,
    B3-C1 0.30/0.45, FLOOR-25/20/15/NO-FLOOR) sin duplicar la fórmula.
    gameplay llama a calculate_play_outcome(), que delega aquí sin overrides.
    """
    take_bias = TAKE_BASE_STRIKE_CHANCE if take_bias is None else take_bias
    foul_chance = FOUL_ON_CONTACT_CHANCE if foul_chance is None else foul_chance
    take_floor = TAKE_STRIKE_CHANCE_FLOOR if take_floor is None else take_floor

    tactics: TacticsModifiers = tactics_modifiers or {
        "batter_con": 1.0,
        "batter_pwr": 1.0,
        "batter_vis": 1.0,
        "pitcher_mov": 1.0,
        "pitcher_vel": 1.0,
        "pitcher_ctl": 1.0
    }

    # --- ATRIBUTOS DEL BATEADOR ---
    con = batter_attrs.get("contacto", 50) * tactics.get("batter_con", 1.0)
    pwr = batter_attrs.get("poder", 50) * tactics.get("batter_pwr", 1.0)
    vis = batter_attrs.get("vision", 50) * tactics.get("batter_vis", 1.0)

    # --- ATRIBUTOS DEL PICHEO (Prioriza el repertorio específico, si no usa los globales) ---
    vel = pitch_selected.get("velocity", pitcher_attrs.get("velocidad", 50)) * tactics.get("pitcher_vel", 1.0)
    ctl = pitch_selected.get("control", pitcher_attrs.get("control", 50)) * tactics.get("pitcher_ctl", 1.0)
    mov = pitch_selected.get("movement", pitcher_attrs.get("movimiento", 50)) * tactics.get("pitcher_mov", 1.0)

    # Stuff EFECTIVO (003B-6A). Llega YA fatigado desde fatigue_manager; este
    # módulo no conoce fatigue_factor ni lo necesita. Si el diccionario no trae
    # la clave (llamadas legacy, objetos de test) se asume el baseline: supresión
    # 0 y comportamiento idéntico al previo a 003B.
    stuff = pitcher_attrs.get("stuff", STUFF_BASELINE)

    swing_type = swing_selected.get("swing_type", "NORMAL")
    guessed_zone = swing_selected.get("guessed_zone")
    guessed_pitch = swing_selected.get("guessed_pitch")

    actual_zone = pitch_selected["zone"]
    actual_pitch = pitch_selected["pitch_type"]

    # Manejo especial de Base por Bolas Intencional
    if actual_pitch == PitchType.IBB:
        return PlayResult(Event.BALL, "Base por bolas intencional.")

    zone_matched = (guessed_zone == actual_zone)
    pitch_matched = (guessed_pitch == actual_pitch)

    # --- FASE 1: BATEADOR NO HACE SWING (TAKE) ---
    if swing_type == SwingType.TAKE:
        return _calculate_take_outcome(take_bias, ctl, vis, zone_matched, take_floor)

    # --- FASE 2/3: SWING → whiff / foul / bola en juego ---
    return _calculate_contact_outcome(
        foul_chance, swing_type, con, pwr, vel, mov, zone_matched, pitch_matched, stuff,
    )


def _calculate_take_outcome(
    take_bias: float, ctl: float, vis: float, zone_matched: bool, take_floor: float,
) -> PlayResult:
    """FASE 1 — TAKE: strike cantado vs bola (002C-B: take_bias LAB, CLAMP-001)."""
    if random.random() < _take_strike_probability(take_bias, ctl, vis,
                                                  zone_matched, take_floor):
        return PlayResult(Event.STRIKE_LOOKING, "Lanzamiento en la zona. ¡Strike cantado!")
    return PlayResult(Event.BALL, "Lanzamiento fuera de la zona. ¡Bola!")


def _calculate_contact_outcome(
    foul_chance: float,
    swing_type: SwingType,
    con: float,
    pwr: float,
    vel: float,
    mov: float,
    zone_matched: bool,
    pitch_matched: bool,
    effective_stuff: float = STUFF_BASELINE,
) -> PlayResult:
    """FASE 2/3 — SWING: whiff → foul (002C-C) → BABIP.

    ``effective_stuff`` es el Stuff YA fatigado. Stuff sólo actúa sobre el
    power_score (BABIP): no toca el whiff ni la disciplina, que es exactamente
    el aislamiento de mecanismo que 003B fijó al elegir el brazo S2 y que el
    contrato T7 vuelve a verificar.
    """
    # Base Whiff%: ~24.5% en MLB para un duelo neutro (50 vs 50)
    # Un picheo con alto movimiento (ej. Slider/Sweeper de 95 MOV) incrementa el whiff%
    whiff_base = 24.5 + (vel * 0.25 + mov * 0.25) - (con * 0.35)

    if zone_matched:
        whiff_base -= 10.0
    if pitch_matched:
        whiff_base -= 8.0

    if swing_type == SwingType.POWER:
        whiff_base += 8.0  # El swing de poder aumenta la tasa de abanicado
        pwr *= 1.20

    whiff_chance = max(5.0, min(65.0, whiff_base))

    # Evaluación de contacto
    if random.uniform(0, 100) < whiff_chance:
        return PlayResult(Event.STRIKE_SWINGING, "Swing abanicado. ¡Strike!")

    # De los contactos que no abanican, ~45% son Fouls (002E-4: foul_chance LAB
    # ahora en fracción 0–1). El draw se evalúa SIEMPRE (orden de RNG preservado);
    # acertar zona + tipo deja la probabilidad en 0 → contacto limpio garantizado.
    if random.random() < _contact_foul_probability(foul_chance, zone_matched, pitch_matched):
        return PlayResult(Event.FOUL, "Batazo de foul.")

    # --- BOLA PUESTA EN JUEGO (BABIP MLB REAL) ---
    power_score = (pwr - 50) * 0.4 + random.uniform(0, 100)

    if zone_matched and pitch_matched:
        power_score += 15.0

    # --- Stuff: contact-quality suppression (GAMEPLAY-ENGINE-003B, k=.30) ---
    # El punto de inserción NO es arbitrario: es el último antes de los umbrales,
    # y es donde el LAB lo tenía. Move el offset antes o después del bono de
    # zona+pitch y las dos rutas dejan de ser comparables (y la comparación es
    # justo el contrato S1). Stuff alto resta poder; Stuff bajo lo suma.
    power_score += stuff_power_suppression(effective_stuff)

    if power_score > 96.0:
        return PlayResult(Event.HOME_RUN, "¡Enorme batazo por todo el jardín central! ¡HOME RUN!")
    elif power_score > 93.0:
        return PlayResult(Event.HIT_3B, "¡Batazo pegado a la barda! El corredor llega a tercera base. ¡Triple!")
    elif power_score > 85.0:
        return PlayResult(Event.HIT_2B, "Batazo profundo contra la barda. Doble base.")
    elif power_score > 63.0:
        return PlayResult(Event.HIT_1B, "Contacto limpio sobre el cuadro. Hit sencillo.")
    elif power_score > 25.0:
        return PlayResult(Event.OUT_GROUND, "Roletazo suave al cuadro para out.")
    else:
        return PlayResult(Event.OUT_FLY, "Elevado de rutina atrapado en el jardín.")


def _take_strike_probability(take_bias: float, ctl: float, vis: float,
                             zone_matched: bool, take_floor: float) -> float:
    """Probabilidad de strike en TAKE (pura; clamp [piso, techo] 002E-4)."""
    strike_chance = (
        take_bias
        + (ctl - 50) * CONTROL_TAKE_WEIGHT
        - (vis - 50) * VISION_TAKE_WEIGHT
    )
    if zone_matched:
        strike_chance -= _ZONE_MATCH_BONUS  # Bono por anticipar la zona correcta
    return max(take_floor, min(TAKE_STRIKE_CHANCE_CEILING, strike_chance))


def _contact_foul_probability(foul_chance: float, zone_matched: bool, pitch_matched: bool) -> float:
    """Probabilidad de FOUL sobre un contacto no-limpio (fracción 0–1, pura)."""
    if zone_matched and pitch_matched:
        return 0.0
    return foul_chance
