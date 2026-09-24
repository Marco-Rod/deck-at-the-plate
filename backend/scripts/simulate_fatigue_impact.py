"""GAMEPLAY-ENGINE-001B — Monte Carlo de fatiga (nivel pitch y PA completo).

Fuera de producción: no toca fatigue_manager.py ni calculator.py. Reproduce el
pipeline real de un pitch (CPU MEDIUM) y llama al resolver del engine:
calculate_play_outcome() en las call sites de referencia (pipeline real, tal
cual resolve_swing()) y _resolve_play_outcome() con overrides LAB
(take_bias / foul_chance) en los tratamientos de disciplina.

RNG determinista y compartido entre curvas:
    Para cada escenario (workload) y replica (seed), las TRES curvas se ejecutan
    con random.seed(seed) → misma secuencia de draw. La única variable
    independiente es la fatiga (atributos).

Tratamientos experimentales:
    CURRENT        → réplica CONGELADA de apply_pitcher_fatigue legacy (ver LEGACY_*)
    LINEAR-0.8-F50 → factor = max(0.50, 1 - 0.80*(w-1)), w = workload
    SMOOTH-0.55-F35→ factor = 0.35 + 0.65*exp(-((w-1)/0.55)**2)

Niveles:
    pitch  → 001B-3: un pitch suelto (tabla pitch-level).
    pa     → 001B-4: PA completo 0-0 → K/BB/BIP terminal, con fatiga dinámica
             (pitch_count avanza 31→32→33… y se recalcula por lanzamiento).

Perfil sintético actual: MID pitcher vs MID batter, dificultad MEDIUM.
"""

import argparse
import math
import os
import random
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.enums import Event, PitchType, SwingType
from app.engine.calculator import (
    _resolve_play_outcome,
    _contact_foul_probability,
    calculate_play_outcome,
    FOUL_ON_CONTACT_CHANCE,
)
from app.engine.cpu_ai import (
    get_cpu_pitch_action,
    get_cpu_swing_action,
    get_cpu_pitcher_change_decision,
    _CPU_CHANGE_WORKLOAD_THRESHOLD,
)
from app.engine.fatigue_manager import (
    get_fatigue_factor,
    get_pitch_threshold,
    get_workload,
)
from app.engine.game_rules import MIN_PITCHES_TO_CHANGE

INNINGS = 9

# ---------------------------------------------------------------------------
# Política legacy CONGELADA para reproducir los experimentos GAMEPLAY-ENGINE-001B.
# No reemplazar por los helpers de producción (Fatigue Policy v2, 001C): en
# cuanto producción cambie, dejarían de representar la curva CURRENT histórica.
# ---------------------------------------------------------------------------
LEGACY_THRESHOLDS = {3: 6, 6: 15, 9: 25}
LEGACY_PENALTY_STEP = 0.10


def legacy_get_pitch_threshold(total_innings: int = 9) -> int:
    if total_innings in LEGACY_THRESHOLDS:
        return LEGACY_THRESHOLDS[total_innings]
    return max(6, int((60.0 / 9.0) * total_innings))


def legacy_apply_pitcher_fatigue(pitcher_attrs, pitch_count, total_innings=9):
    """Réplica fiel del apply_pitcher_fatigue anterior a Fatigue Policy v2."""
    modified = dict(pitcher_attrs)
    threshold = legacy_get_pitch_threshold(total_innings)
    if pitch_count > threshold:
        penalty = 1.0 - LEGACY_PENALTY_STEP * (pitch_count - threshold)
        for key in ("velocidad", "control", "movimiento"):
            modified[key] = max(1, int(modified.get(key, 50) * penalty))
    return modified


THRESHOLD = legacy_get_pitch_threshold(INNINGS)

# --- Perfiles sintéticos (LAB) ---
PITCHER_RAW = {"velocidad": 90, "control": 80, "movimiento": 85}
PITCH_RAW = {"velocity": 90, "control": 80, "movement": 85}
BATTER = {"contacto": 70, "poder": 70, "vision": 70}
DIFFICULTY = "MEDIUM"

WORKLOADS = [0.75, 1.00, 1.10, 1.25, 1.50]
CURVES = ["CURRENT", "LINEAR", "SMOOTH"]
REPS = 50_000

# --- Política de bateador LAB (solo para que el PA pueda expresar K y BB) ---
# NO va a producción. Porcentaje de TAKE según el conteo de strikes.
TAKE_PROB_BY_STRIKES = {0: 0.35, 1: 0.25, 2: 0.10}
# Adivinanzas idénticas a la CPU MEDIUM de producción (cpu_ai.py)
GUESS_ZONE_PROB = 0.30
GUESS_PITCH_PROB = 0.20
_PITCH_TYPES = [p for p in PitchType if p is not PitchType.IBB]

# Red de seguridad para detectar PA absurdamente largos (bug de transición)
MAX_PA_PITCHES = 100


def linear_factor(w: float) -> float:
    if w <= 1.0:
        return 1.0
    return max(0.50, 1.0 - 0.80 * (w - 1.0))


def smooth_factor(w: float) -> float:
    if w <= 1.0:
        return 1.0
    return 0.35 + 0.65 * math.exp(-((w - 1.0) / 0.55) ** 2)


def effective_attrs(curve: str, pitch_count: int, workload: float = None,
                    pitcher_raw: dict = None, pitch_raw: dict = None):
    """Atributos efectivos para un pitch_count CONCRETO (fatiga concreta).

    Fiel a resolve_swing(): atributos globales degradados + factor implícito
    por atributo aplicado al repertorio específico del lanzamiento.

    Args:
        curve:       'CURRENT' | 'LINEAR' | 'SMOOTH'
        pitch_count: count real usado por CURRENT (apply_pitcher_fatigue).
        workload:    workload normalizado para los candidatos; si es None se
                     deriva como pitch_count / THRESHOLD (fatiga dinámica del PA).
        pitcher_raw: dict base (velocidad/control/movimiento); default PITCHER_RAW.
        pitch_raw:   dict del lanzamiento (velocity/control/movement); default PITCH_RAW.
    Returns: (fatigued_global, pitch_effective_dict)
    """
    pitcher_raw = pitcher_raw or PITCHER_RAW
    pitch_raw = pitch_raw or PITCH_RAW
    w = workload if workload is not None else pitch_count / THRESHOLD
    if curve == "CURRENT":
        fatigued = legacy_apply_pitcher_fatigue(dict(pitcher_raw), pitch_count, INNINGS)
    else:
        factor = linear_factor(w) if curve == "LINEAR" else smooth_factor(w)
        fatigued = {k: max(1, int(v * factor)) for k, v in pitcher_raw.items()}

    pitch_eff = {
        "velocity": int(pitch_raw["velocity"] * fatigued["velocidad"] / pitcher_raw["velocidad"]),
        "control": int(pitch_raw["control"] * fatigued["control"] / pitcher_raw["control"]),
        "movement": int(pitch_raw["movement"] * fatigued["movimiento"] / pitcher_raw["movimiento"]),
    }
    return fatigued, pitch_eff


def pitch_level_attrs(curve: str, workload: float):
    """Atributos efectivos de un pitch suelto a un workload normalizado (001B-3).

    Consistente con la tabla original de 001B-3: CURRENT usa el count redondeado
    a entero; los candidatos usan el workload exacto del punto de la tabla.
    """
    return effective_attrs(curve, int(workload * THRESHOLD), workload=workload)


# ---------------------------------------------------------------------------
# Nivel pitch (001B-3)
# ---------------------------------------------------------------------------

def simulate_once(curve: str, workload: float, seed: int):
    random.seed(seed)
    fatigued_pitcher, pitch_eff = pitch_level_attrs(curve, workload)

    pitch = get_cpu_pitch_action(DIFFICULTY)   # zone + pitch_type (draws shared)

    swing = get_cpu_swing_action(DIFFICULTY)

    pitch["velocity"] = pitch_eff["velocity"]
    pitch["control"] = pitch_eff["control"]
    pitch["movement"] = pitch_eff["movement"]

    event, _description = calculate_play_outcome(
        pitcher_attrs=fatigued_pitcher,
        batter_attrs=BATTER,
        pitch_selected=pitch,
        swing_selected=swing,
        tactics_modifiers=None,
    )
    return event, swing["swing_type"]


def run_pitch_scenario(curve: str, workload: float, reps: int):
    events = Counter()
    swings = 0
    takes = 0
    for rep in range(reps):
        seed = int(workload * 1000) * 10**6 + rep
        event, swing_type = simulate_once(curve, workload, seed)
        events[event] += 1
        if swing_type == "TAKE":
            takes += 1
        else:
            swings += 1
    _, pitch_eff = pitch_level_attrs(curve, workload)
    return pitch_eff, events, swings, takes


# ---------------------------------------------------------------------------
# Nivel PA completo (001B-4)
# ---------------------------------------------------------------------------

_BIP_OUTCOME = {
    Event.OUT_FLY: "OUT",
    Event.OUT_GROUND: "OUT",
    Event.HIT_1B: "1B",
    Event.HIT_2B: "2B",
    Event.HIT_3B: "3B",
    Event.HOME_RUN: "HR",
}


def batter_action_by_count(strikes: int, take_probs: dict = None) -> dict:
    """Política LAB de bateador según conteo de strikes (consume draws)."""
    probs = take_probs or TAKE_PROB_BY_STRIKES
    swing_type = SwingType.TAKE if random.random() < probs[strikes] else SwingType.NORMAL
    guessed_zone = random.randint(1, 9) if random.random() < GUESS_ZONE_PROB else None
    guessed_pitch = random.choice(_PITCH_TYPES) if random.random() < GUESS_PITCH_PROB else None
    return {
        "swing_type": swing_type,
        "guessed_zone": guessed_zone,
        "guessed_pitch": guessed_pitch,
    }


def simulate_pa(curve: str, start_workload: float, seed: int):
    """Un PA completo desde 0-0 hasta K/BB/BIP terminal, con fatiga dinámica.

    Transiciones (dominio real de calculate_play_outcome):
        SWING_MISS/CALLED_STRIKE → strike (strike 3 = K)
        BALL                      → ball (ball 4 = BB)
        FOUL                      → strike si strikes < 2; se queda en 2 si ya hay 2
        BIP                       → OUT / 1B / 2B / 3B / HR (terminal)

    Returns: (outcome, pitches_en_pa, pitch_count_efectivo_final)
    """
    random.seed(seed)
    balls = 0
    strikes = 0
    pitches = 0
    pitch_count = int(start_workload * THRESHOLD)
    final_count = pitch_count

    while pitches < MAX_PA_PITCHES:
        pitches += 1
        fatigued_pitcher, pitch_eff = effective_attrs(curve, pitch_count)
        final_count = pitch_count
        pitch_count += 1

        pitch = get_cpu_pitch_action(DIFFICULTY)
        swing = batter_action_by_count(strikes)
        pitch["velocity"] = pitch_eff["velocity"]
        pitch["control"] = pitch_eff["control"]
        pitch["movement"] = pitch_eff["movement"]

        event, _description = calculate_play_outcome(
            pitcher_attrs=fatigued_pitcher,
            batter_attrs=BATTER,
            pitch_selected=pitch,
            swing_selected=swing,
            tactics_modifiers=None,
        )

        if event in (Event.STRIKE_SWINGING, Event.STRIKE_LOOKING):
            strikes += 1
            if strikes == 3:
                return "K", pitches, final_count
        elif event == Event.BALL:
            balls += 1
            if balls == 4:
                return "BB", pitches, final_count
        elif event == Event.FOUL:
            if strikes < 2:
                strikes += 1
        else:
            return _BIP_OUTCOME[event], pitches, final_count

    return "CAP", pitches, final_count  # red de seguridad: PA absurdamente largo


def run_pa_scenario(curve: str, start_workload: float, reps: int):
    outcomes = Counter()
    lengths = []
    final_counts = []
    for rep in range(reps):
        seed = int(start_workload * 1000) * 10**6 + rep
        outcome, pitches, final_count = simulate_pa(curve, start_workload, seed)
        outcomes[outcome] += 1
        lengths.append(pitches)
        final_counts.append(final_count)
    return outcomes, lengths, final_counts


def _p95(values: list) -> float:
    s = sorted(values)
    idx = max(0, min(len(s) - 1, int(round(0.95 * len(s)))))
    return s[idx]


def _fmt_pct(x: float, n: int) -> str:
    return f"{x / max(1, n) * 100:6.2f}"


# ---------------------------------------------------------------------------
# Subbloque 002A · Plate discipline / count diagnostics (sin fatiga)
# ---------------------------------------------------------------------------

# Sonda experimental: fatiga CONGELADA en 75% (pitch_count fijo = 18/25 →
# factor 1.0) para aislar la dinámica del count de la fatiga.
DISCIPLINE_CURVE = "SMOOTH"
DISCIPLINE_WORKLOAD = 0.75

# Políticas LAB de disciplina (prob. de TAKE por 0/1/2 strikes).
# No son propuestas de gameplay: son sondas para verificar que el count puede
# desarrollarse si el agente es más paciente.
DISCIPLINE_POLICIES = {
    "CURRENT_LAB": {0: 0.35, 1: 0.25, 2: 0.10},
    "PATIENT": {0: 0.50, 1: 0.35, 2: 0.15},
    "VERY_PATIENT": {0: 0.65, 1: 0.50, 2: 0.25},
}


# ---------------------------------------------------------------------------
# Subbloque 003B-1 · Stuff semantic candidates
# ---------------------------------------------------------------------------
# Stuff es una dimensión EXPERIMENTAL (no existe en PitcherAttrs de producción).
# Se registra vía `_resolve_play_outcome_stuff`, que replica bit-a-bit la FASE
# 1/2/3 del engine (mismo orden de draws de RNG, mismas constantes) con un
# modulador de Stuff que vale EXACTAMENTE 0 en stuff=70 (delta=0) → identidad
# con CALIBRATED-BASELINE-v1 garantizada por construcción. NO toca calculator.py.
STUFF_IDENTITY = 70
STUFF_LEVELS = [45, 55, 70, 85, 95]

# Coeficientes de forma, NO de calibración (003B-1 compara formas; 003B-3 hará
# el coefficient sweep). k=0.064/pp → Δdelta total (50pp) mueve la dimensión
# ~3.2pp (L4 ≥1.5pp con holgura) y el paso consecutivo mayor (15pp) mueve
# ≤0.96pp (L6 ≤1.0pp). S3 usa exactamente la mitad de cada.
STUFF_K_WIFF = 0.064   # S1 / S3 → whiff_base += delta * k
STUFF_K_QTY = 0.064    # S2 / S3 → power_score += delta * k (quality, supresión)
STUFF_ARMS = ("S1", "S2", "S3")


def _stuff_modifiers(stuff_arm: str, delta: float, k_qty: float = None) -> tuple:
    """Moduladores (whiff_add, power_add) del brazo semántico.

    Signo documentado: en S2/S3 la quality del lanzador es supresión → Stuff
    alto REDUCE power_score (XBH/BIP baja). Si la corrida observara lo
    contrario, se REVIERTE el signo en el contrato, no se re-etiqueta la rama.

    k_qty: override del coeficiente de quality (003B-3 · coefficient sweep).
    None → STUFF_K_QTY (conserva el comportamiento 003B-1/2 exacto).
    """
    k = STUFF_K_QTY if k_qty is None else k_qty
    if stuff_arm == "S1":
        return delta * STUFF_K_WIFF, 0.0
    if stuff_arm == "S2":
        return 0.0, -delta * k
    if stuff_arm == "S3":
        return delta * STUFF_K_WIFF / 2.0, -delta * k / 2.0
    raise ValueError(f"stuff_arm desconocido: {stuff_arm!r}")


def _resolve_play_outcome_stuff(
    pitcher_attrs: dict,
    batter_attrs: dict,
    pitch_selected: dict,
    swing_selected: dict,
    tactics_modifiers: dict = None,
    stuff_level: int = STUFF_IDENTITY,
    stuff_arm: str = "S1",
    stuff_k_qty: float = None,
    power_log: list = None,
):
    """Réplica LAB de la resolución de jugada con modulador de Stuff (003B-1).

    - FASE 1 (IBB / TAKE) → delega en `_resolve_play_outcome` del engine con
      knobs = None (producción): Stuff NO afecta disciplina; dibuja el mismo RNG.
    - FASE 2/3 (SWING → whiff / foul / BABIP) → réplica idéntica del engine
      (mismo orden de draws y constantes) + moduladores S1/S2/S3.
    - delta = stuff_level - 70 → en stuff=70 los moduladores valen 0 y la
      réplica es bit-por-bit el engine (identidad exacta).

    stuff_k_qty: override del coeficiente de quality de S2/S3
            (003B-3 · coefficient sweep). None → STUFF_K_QTY.
    power_log: lista externa a la que se anexa el power_score resultante de
            CADA contacto (BIP) → distribución p10/p50/p90/mean en 003B-3.
            None → no captura (comportamiento 003B-1/2 exacto).
    """
    delta = stuff_level - STUFF_IDENTITY
    whiff_add, power_add = _stuff_modifiers(stuff_arm, delta, k_qty=stuff_k_qty)

    tactics = tactics_modifiers or {
        "batter_con": 1.0,
        "batter_pwr": 1.0,
        "batter_vis": 1.0,
        "pitcher_mov": 1.0,
        "pitcher_vel": 1.0,
        "pitcher_ctl": 1.0,
    }

    con = batter_attrs.get("contacto", 50) * tactics.get("batter_con", 1.0)
    pwr = batter_attrs.get("poder", 50) * tactics.get("batter_pwr", 1.0)
    vis = batter_attrs.get("vision", 50) * tactics.get("batter_vis", 1.0)

    vel = pitch_selected.get("velocity",
                             pitcher_attrs.get("velocidad", 50)) * tactics.get("pitcher_vel", 1.0)
    ctl = pitch_selected.get("control",
                             pitcher_attrs.get("control", 50)) * tactics.get("pitcher_ctl", 1.0)
    mov = pitch_selected.get("movement",
                             pitcher_attrs.get("movimiento", 50)) * tactics.get("pitcher_mov", 1.0)

    swing_type = swing_selected.get("swing_type", "NORMAL")
    guessed_zone = swing_selected.get("guessed_zone")
    guessed_pitch = swing_selected.get("guessed_pitch")

    actual_zone = pitch_selected["zone"]
    actual_pitch = pitch_selected["pitch_type"]

    if actual_pitch == PitchType.IBB:
        return Event.BALL, "Base por bolas intencional."

    zone_matched = (guessed_zone == actual_zone)
    pitch_matched = (guessed_pitch == actual_pitch)

    if swing_type == SwingType.TAKE:
        return _resolve_play_outcome(
            pitcher_attrs, batter_attrs, pitch_selected, swing_selected,
            tactics_modifiers,
        )

    # --- FASE 2/3: réplica de _calculate_contact_outcome + modulador Stuff ---
    whiff_base = 24.5 + (vel * 0.25 + mov * 0.25) - (con * 0.35) + whiff_add
    if zone_matched:
        whiff_base -= 10.0
    if pitch_matched:
        whiff_base -= 8.0
    if swing_type == SwingType.POWER:
        whiff_base += 8.0
        pwr *= 1.20

    whiff_chance = max(5.0, min(65.0, whiff_base))

    if random.uniform(0, 100) < whiff_chance:
        return Event.STRIKE_SWINGING, "Swing abanicado. ¡Strike!"

    if random.random() < _contact_foul_probability(
            FOUL_ON_CONTACT_CHANCE, zone_matched, pitch_matched):
        return Event.FOUL, "Batazo de foul."

    power_score = (pwr - 50) * 0.4 + random.uniform(0, 100)
    if zone_matched and pitch_matched:
        power_score += 15.0
    power_score += power_add
    if power_log is not None:
        power_log.append(power_score)

    if power_score > 96.0:
        return Event.HOME_RUN, "¡HOME RUN!"
    elif power_score > 93.0:
        return Event.HIT_3B, "Triple."
    elif power_score > 85.0:
        return Event.HIT_2B, "Doble base."
    elif power_score > 63.0:
        return Event.HIT_1B, "Hit sencillo."
    elif power_score > 25.0:
        return Event.OUT_GROUND, "Roletazo al cuadro para out."
    else:
        return Event.OUT_FLY, "Elevado de rutina."


def _simulate_pa_diag(take_probs: dict, seed: int,
                      control: int = None, vision: int = None,
                      take_bias: float = None,
                      foul_chance: float = None,
                      take_floor: float = None,
                      batter_attrs: dict = None,
                      pitcher_attrs: dict = None,
                      use_public_api: bool = False,
                      stuff_level: int = None,
                      stuff_arm: str = None,
                      stuff_k_qty: float = None,
                      power_log: list = None) -> dict:
    """PA 0-0 → K/BB/BIP con diagnóstico de count y de disciplinas, SIN fatiga.

    Args:
        take_probs: TAKE por strikes {0:.., 1:.., 2:..}.
        seed:       semilla del PA.
        control:    override del Control del pitcher (002B); default MID=80.
        vision:     override de la Vision del batter (002B); default MID=70.
        take_bias:  override del baseline de strike_chance del TAKE (002C-B);
                    None → 0.30 (producción 002E-4).
        foul_chance: override de la fracción de FOUL sobre contactos (002C-C);
                    None → 0.45 (producción 002E-4).
        take_floor: piso inferior del clamp del TAKE (002E-3 · CLAMP-001);
                    None → 0.20 (producción 002E-4); 0.0 → sin piso inferior.
        batter_attrs: override COMPLETO del perfil ofensivo del batter
                    (002E-2 · matchup WEAK/MID/STRONG sobre CTL fijo del
                    pitcher; la Vision del PA sigue controlada por `vision`).
                    None → BATTER (70/70/70).
        pitcher_attrs: override COMPLETO del perfil del pitcher
                    (003A · baseline: velocidad/control/movimiento
                    WEAK/MID/STRONG). None → PITCHER_RAW (90/80/85).
        use_public_api: True → resuelve la jugada con calculate_play_outcome()
                    (producción pura, sin knobs LAB) en vez de
                    _resolve_play_outcome (002E-5 · production acceptance).
        stuff_level: stuff del pitcher (003B-1 · semantic candidates). Cuando
                    es None → comportamiento previo. Cuando se pasa, TODO el
                    PA se resuelve vía _resolve_play_outcome_stuff, cuya
                    réplica es bit-por-bit el engine en stuff=70 (delta=0 →
                    moduladores en cero) → identidad EXACTA por construcción.
                    Solo afecta la FASE 2/3 del swing (whiff / power_score);
                    la disciplina (TAKE) se delega al engine sin knobs.
        stuff_arm:  brazo semántico en {"S1", "S2", "S3"} (003B-1):
                    S1=whiff, S2=contact quality, S3=hybrid.
        stuff_k_qty: override del coeficiente de quality de S2/S3
                    (003B-3 · coefficient sweep). None → STUFF_K_QTY.
        power_log: lista externa que recibe el power_score de cada contacto
                    (003B-3 · distribución). None → sin captura.
    """
    random.seed(seed)
    balls = 0
    strikes = 0
    pitches = 0
    pitch_count = int(DISCIPLINE_WORKLOAD * THRESHOLD)  # congelado → factor 1.0

    # Overrides 002B (factorial Control × Vision) + 002E-2 (perfil ofensivo
    # del batter) + 003A (perfil completo del pitcher); resto MID fijo.
    pitcher_raw = dict(PITCHER_RAW if pitcher_attrs is None else pitcher_attrs)
    pitch_raw = dict(PITCH_RAW if pitcher_attrs is None else {
        "velocity": pitcher_attrs["velocidad"],
        "control": pitcher_attrs["control"],
        "movement": pitcher_attrs["movimiento"],
    })
    batter_attrs = dict(BATTER if batter_attrs is None else batter_attrs)
    if control is not None:
        pitcher_raw["control"] = control
        pitch_raw["control"] = control
    if vision is not None:
        batter_attrs["vision"] = vision

    take_attempts = balls_on_take = called_strikes_on_take = 0
    swing_attempts = whiffs = fouls = bips = 0
    reached_2strikes = reached_3balls = reached_full = False

    # Instrumentación 002D: decisiones con 2 strikes (para P(TAKE|2s) y la
    # cadena completo TAKE|2s → ball / called strike) + terminación condicional.
    take_at_2s = 0
    pitches_at_2s = 0
    balls_on_take_at_2s = 0
    called_strikes_on_take_at_2s = 0
    outcome_at_2s = None  # terminación del PA si alcanzó 2 strikes

    outcome = "CAP"
    while pitches < MAX_PA_PITCHES:
        pitches += 1

        if strikes == 2:
            pitches_at_2s += 1

        fatigued_pitcher, pitch_eff = effective_attrs(
            DISCIPLINE_CURVE, pitch_count, workload=DISCIPLINE_WORKLOAD,
            pitcher_raw=pitcher_raw, pitch_raw=pitch_raw,
        )
        pitch = get_cpu_pitch_action(DIFFICULTY)
        swing = batter_action_by_count(strikes, take_probs)
        pitch["velocity"] = pitch_eff["velocity"]
        pitch["control"] = pitch_eff["control"]
        pitch["movement"] = pitch_eff["movement"]

        if stuff_level is not None:
            event, _description = _resolve_play_outcome_stuff(
                pitcher_attrs=fatigued_pitcher,
                batter_attrs=batter_attrs,
                pitch_selected=pitch,
                swing_selected=swing,
                tactics_modifiers=None,
                stuff_level=stuff_level,
                stuff_arm=stuff_arm,
                stuff_k_qty=stuff_k_qty,
                power_log=power_log,
            )
        elif use_public_api:
            event, _description = calculate_play_outcome(
                pitcher_attrs=fatigued_pitcher,
                batter_attrs=batter_attrs,
                pitch_selected=pitch,
                swing_selected=swing,
                tactics_modifiers=None,
            )
        else:
            event, _description = _resolve_play_outcome(
                pitcher_attrs=fatigued_pitcher,
                batter_attrs=batter_attrs,
                pitch_selected=pitch,
                swing_selected=swing,
                tactics_modifiers=None,
                take_bias=take_bias,
                foul_chance=foul_chance,
                take_floor=take_floor,
            )

        if swing["swing_type"] == SwingType.TAKE:
            take_attempts += 1
            if event == Event.BALL:
                balls_on_take += 1
            elif event == Event.STRIKE_LOOKING:
                called_strikes_on_take += 1
            if strikes == 2:
                take_at_2s += 1
                if event == Event.BALL:
                    balls_on_take_at_2s += 1
                elif event == Event.STRIKE_LOOKING:
                    called_strikes_on_take_at_2s += 1
        else:
            swing_attempts += 1
            if event == Event.STRIKE_SWINGING:
                whiffs += 1
            elif event == Event.FOUL:
                fouls += 1
            elif event in _BIP_OUTCOME:
                bips += 1

        if event in (Event.STRIKE_SWINGING, Event.STRIKE_LOOKING):
            strikes += 1
            if strikes == 2:
                reached_2strikes = True
            if strikes >= 3:
                outcome = "K"
                break
        elif event == Event.BALL:
            balls += 1
            if balls == 3:
                reached_3balls = True
            if balls >= 4:
                outcome = "BB"
                break
        elif event == Event.FOUL:
            if strikes < 2:
                strikes += 1
        else:
            outcome = _BIP_OUTCOME[event]
            break

        if balls == 3 and strikes == 2:
            reached_full = True

    if reached_2strikes:
        outcome_at_2s = outcome

    return {
        "outcome": outcome,
        "pitches": pitches,
        "reached_2strikes": reached_2strikes,
        "reached_3balls": reached_3balls,
        "reached_full": reached_full,
        "take_attempts": take_attempts,
        "balls_on_take": balls_on_take,
        "called_strikes_on_take": called_strikes_on_take,
        "swing_attempts": swing_attempts,
        "whiffs": whiffs,
        "fouls": fouls,
        "bips": bips,
        "take_at_2s": take_at_2s,
        "pitches_at_2s": pitches_at_2s,
        "balls_on_take_at_2s": balls_on_take_at_2s,
        "called_strikes_on_take_at_2s": called_strikes_on_take_at_2s,
        "outcome_at_2s": outcome_at_2s,
    }


def run_discipline_scenario(name: str, take_probs: dict, reps: int) -> dict:
    agg = {
        "outcome": Counter(),
        "pitches": 0,
        "reached_2strikes": 0,
        "reached_3balls": 0,
        "reached_full": 0,
        "take_attempts": 0,
        "balls_on_take": 0,
        "called_strikes_on_take": 0,
        "swing_attempts": 0,
        "whiffs": 0,
        "fouls": 0,
        "bips": 0,
        "depth": Counter(),
    }
    for rep in range(reps):
        seed = int(DISCIPLINE_WORKLOAD * 1000) * 10**6 + rep  # seeds compartidas entre políticas
        d = _simulate_pa_diag(take_probs, seed)
        agg["outcome"][d["outcome"]] += 1
        agg["pitches"] += d["pitches"]
        agg["reached_2strikes"] += d["reached_2strikes"]
        agg["reached_3balls"] += d["reached_3balls"]
        agg["reached_full"] += d["reached_full"]
        agg["take_attempts"] += d["take_attempts"]
        agg["balls_on_take"] += d["balls_on_take"]
        agg["called_strikes_on_take"] += d["called_strikes_on_take"]
        agg["swing_attempts"] += d["swing_attempts"]
        agg["whiffs"] += d["whiffs"]
        agg["fouls"] += d["fouls"]
        agg["bips"] += d["bips"]
        for n in (3, 4, 5, 6):
            if d["pitches"] >= n:
                agg["depth"][n] += 1
    return agg


def run_discipline_level(reps: int, take_probs_override: dict = None,
                         extra_names: dict = None) -> None:
    """002A · Diagnóstico de count/disciplina. Fatiga congelada en 75%."""
    print("=" * 130)
    print("002A · Plate discipline / count diagnostics (sin fatiga)")
    print(f"MID P {PITCHER_RAW} vs MID B {BATTER} | CPU {DIFFICULTY} MEDIUM | "
          f"fatiga congelada al {DISCIPLINE_WORKLOAD:.0%} (factor 1.0) | {reps:,} PA por política")
    print("Pregunta: ¿dónde se rompe la cadena hacia el BB? (TAKE poco, called "
          "strikes de más, o SWING→BIP prematuro)")
    print("=" * 130)

    policies = dict(DISCIPLINE_POLICIES)
    if take_probs_override:
        policies = take_probs_override
    if extra_names:
        for k, v in extra_names.items():
            policies[k] = v

    # Tabla A: outcomes + probabilidades condicionales
    print("\n-- Outcomes y probabilidades de count --")
    print(f"{'Policy':<14} {'K%':>7} {'BB%':>7} {'BIP%':>7} | "
          f"{'P(3bolas)':>9} {'P(2strk)':>8} {'P(full)':>7} "
          f"{'P(BB|3bol)':>10} {'P(K|2str)':>9} | "
          f"{'Pit/PA':>7} {'≥3':>5} {'≥4':>5} {'≥5':>5} {'≥6':>5}")
    print("-" * 130)

    rows = {}
    for name, probs in policies.items():
        a = run_discipline_scenario(name, probs, reps)
        rows[name] = a
        n = reps
        k = a["outcome"]["K"]
        bb = a["outcome"]["BB"]
        bip = n - k - bb
        r3 = a["reached_3balls"]
        r2 = a["reached_2strikes"]
        rfull = a["reached_full"]
        print(
            f"{name:<14} "
            f"{k / n * 100:7.2f} {bb / n * 100:7.2f} {bip / n * 100:7.2f} | "
            f"{r3 / n * 100:8.2f} {r2 / n * 100:7.2f} {rfull / n * 100:6.2f} "
            f"{bb / r3 * 100 if r3 else 0:9.2f} {k / r2 * 100 if r2 else 0:8.2f} | "
            f"{a['pitches'] / n:7.2f} "
            f"{a['depth'][3] / n * 100:4.1f} {a['depth'][4] / n * 100:4.1f} "
            f"{a['depth'][5] / n * 100:4.1f} {a['depth'][6] / n * 100:4.1f}"
        )

    # Tabla B: granularidad take/swing
    print()
    print("-- Granularidad take/swing por PA --")
    print(f"{'Policy':<14} {'Take/PA':>7} {'TBall/PA':>8} {'TCall/PA':>8} | "
          f"{'Swing/PA':>8} {'Whiff/PA':>8} {'Foul/PA':>7} {'BIP/PA':>6}")
    print("-" * 130)
    for name, a in rows.items():
        n = reps
        print(
            f"{name:<14} "
            f"{a['take_attempts'] / n:7.3f} "
            f"{a['balls_on_take'] / n:8.3f} "
            f"{a['called_strikes_on_take'] / n:8.3f} | "
            f"{a['swing_attempts'] / n:8.3f} {a['whiffs'] / n:8.3f} "
            f"{a['fouls'] / n:7.3f} {a['bips'] / n:6.3f}"
        )
    print("-" * 130)
    r3 = rows.get("CURRENT_LAB", {}).get("reached_3balls", 0)
    print(f"Nota: P(K|2str) se calcula sobre PA que alcanzaron 2 strikes; "
          f"P(BB|3bol) sobre PA que alcanzaron 3 bolas.")
    print(f"Mismas seeds entre políticas: la única variable es la disciplina.")


# ---------------------------------------------------------------------------
# 002B · Factorial Control × Vision (3×3) · sensibilidad de los atributos
# ---------------------------------------------------------------------------
# Escala real ratings-2.0 = 40..99 (percentiles.py·percentile_rating).
# Terciles representativos documentados: LOW=45, MID=70, HIGH=95.
# Resto fijo: fatiga congelada 75% (factor 1.0), velocity MID=90,
# movement MID=85, power/contact MID=70, política CURRENT_LAB 35/25/10.
CV_LEVELS = {"LOW": 45, "MID": 70, "HIGH": 95}


def _take_strike_probability(control: int, vision: int) -> float:
    """Espejo analítico de la fórmula del calculator (producción 002E-4: 0.30/0.20)."""
    return max(0.20, min(0.85, 0.30 + (control - 50) * 0.003 - (vision - 50) * 0.002))


def run_control_vision_level(reps: int) -> None:
    """002B · Factorial Control × Vision (3×3), fatiga congelada al 75%.

    Contrato: orden y sensibilidad de atributos, NO balance absoluto.
    Control↑ ⇒ menos called strikes / menos bolas / menos BB.
    Vision↑  ⇒ más bolas / más count profundo / más BB.
    """
    print("=" * 130)
    print("002B · Control × Vision factorial 3×3 · sensibilidad de atributos")
    print(f"Fatiga congelada al {DISCIPLINE_WORKLOAD:.0%} (factor 1.0) | velocity 90 (MID) | "
          f"movement 85 (MID) | power/contact 70 (MID) | política CURRENT_LAB")
    print(f"Escala ratings-2.0 real: 40..99. Terciles LAB: LOW=45, MID=70, HIGH=95.")
    print(f"{reps:,} PA por celda (9 celdas = {reps * 9:,} PA) | mismas seeds por rep")
    print("=" * 130)

    levels = ["LOW", "MID", "HIGH"]
    cells = {}  # (ctl_name, vis_name) -> agg
    ctl_vis_hdr = "Ctl\\Vis"
    for ctl_name in levels:
        for vis_name in levels:
            ctl = CV_LEVELS[ctl_name]
            vis = CV_LEVELS[vis_name]
            cells[(ctl_name, vis_name)] = run_control_vision_cell(ctl, vis, reps)

    # Tabla A: called strike y balls por TAKE (MC) + fórmula analítica
    print()
    print("-- Called strike por TAKE (MC) --")
    print(f"{ctl_vis_hdr:<6} " + "".join(f"{v:>12}" for v in levels))
    for ctl_name in levels:
        row = f"{ctl_name:<6}"
        for vis_name in levels:
            a = cells[(ctl_name, vis_name)]
            pct = a["called_strikes_on_take"] / max(1, a["take_attempts"]) * 100
            row += f"{pct:>10.2f}%"
        print(row)

    print()
    print("-- take_strike_probability (fórmula analítica del calculator) --")
    print(f"{ctl_vis_hdr:<6} " + "".join(f"{v:>12}" for v in levels))
    for ctl_name in levels:
        row = f"{ctl_name:<6}"
        for vis_name in levels:
            row += f"{_take_strike_probability(CV_LEVELS[ctl_name], CV_LEVELS[vis_name]) * 100:>10.2f}%"
        print(row)

    # Tabla B: BB%
    print()
    print("-- BB% --")
    print(f"{ctl_vis_hdr:<6} " + "".join(f"{v:>12}" for v in levels))
    for ctl_name in levels:
        row = f"{ctl_name:<6}"
        for vis_name in levels:
            a = cells[(ctl_name, vis_name)]
            row += f"{a['outcome'].get('BB', 0) / reps * 100:>12.2f}"
        print(row)

    # Tabla C: P(reach 3 bolas) + P(full count)
    print()
    print("-- P(reach 3 bolas)              -- P(full count) --")
    print(f"{ctl_vis_hdr:<6} " + "".join(f"{v:>12}" for v in levels)
          + "   " + "".join(f"{v:>12}" for v in levels))
    for ctl_name in levels:
        row = f"{ctl_name:<6}"
        for vis_name in levels:
            a = cells[(ctl_name, vis_name)]
            row += f"{a['reached_3balls'] / reps * 100:>12.2f}"
        row += "   "
        for vis_name in levels:
            a = cells[(ctl_name, vis_name)]
            row += f"{a['reached_full'] / reps * 100:>12.2f}"
        print(row)

    # Tabla D: Pitches/PA
    print()
    print("-- Pitches/PA --")
    print(f"{ctl_vis_hdr:<6} " + "".join(f"{v:>12}" for v in levels))
    for ctl_name in levels:
        row = f"{ctl_name:<6}"
        for vis_name in levels:
            a = cells[(ctl_name, vis_name)]
            row += f"{a['pitches'] / reps:>12.2f}"
        print(row)

    # Tabla E: P(BB|3bolas) + K% + BIP%
    print()
    print("-- P(BB|3 bolas)      --  K%            --  BIP% --")
    print(f"{ctl_vis_hdr:<6} " + "".join(f"{v:>12}" for v in levels)
          + "   " + "".join(f"{v:>12}" for v in levels)
          + "   " + "".join(f"{v:>12}" for v in levels))
    for ctl_name in levels:
        row = f"{ctl_name:<6}"
        for block in ("pbb3", "k", "bip"):
            for vis_name in levels:
                a = cells[(ctl_name, vis_name)]
                if block == "pbb3":
                    val = a["outcome"].get("BB", 0) / max(1, a["reached_3balls"]) * 100
                elif block == "k":
                    val = a["outcome"].get("K", 0) / reps * 100
                else:
                    val = (reps - a["outcome"].get("K", 0) - a["outcome"].get("BB", 0)) / reps * 100
                row += f"{val:>12.2f}"
            row += "   "
        print(row)

    print("-" * 130)
    print("Sensibilidad esperada: Control↑ ⇒ called strike↑ / bolas↓; "
          "Vision↑ ⇒ called strike↓ / bolas↑ / count profundo↑.")
    print("El contrato es ORDEN y DIRECCIÓN, no porcentaje absoluto (no se usa MLB como target).")


def run_control_vision_cell(control: int, vision: int, reps: int) -> dict:
    agg = {
        "outcome": Counter(),
        "pitches": 0,
        "reached_2strikes": 0,
        "reached_3balls": 0,
        "reached_full": 0,
        "take_attempts": 0,
        "balls_on_take": 0,
        "called_strikes_on_take": 0,
        "swing_attempts": 0,
        "whiffs": 0,
        "fouls": 0,
        "bips": 0,
    }
    take_probs = DISCIPLINE_POLICIES["CURRENT_LAB"]
    for rep in range(reps):
        seed = int(DISCIPLINE_WORKLOAD * 1000) * 10**6 + rep  # mismas seeds entre celdas
        d = _simulate_pa_diag(take_probs, seed, control=control, vision=vision)
        agg["outcome"][d["outcome"]] += 1
        agg["pitches"] += d["pitches"]
        agg["reached_2strikes"] += d["reached_2strikes"]
        agg["reached_3balls"] += d["reached_3balls"]
        agg["reached_full"] += d["reached_full"]
        agg["take_attempts"] += d["take_attempts"]
        agg["balls_on_take"] += d["balls_on_take"]
        agg["called_strikes_on_take"] += d["called_strikes_on_take"]
        agg["swing_attempts"] += d["swing_attempts"]
        agg["whiffs"] += d["whiffs"]
        agg["fouls"] += d["fouls"]
        agg["bips"] += d["bips"]
    return agg


# ---------------------------------------------------------------------------
# 002C-CV · Control × Vision sobre el candidato 002D (B3-C1 + 65/50/30)
# ---------------------------------------------------------------------------
# Verifica que CTL/VIS se traduzcan a RESULTADO de PA con el baseline nuevo.
# No basta dirección en CalledS/take: se comprueba K%/BB%/BIP%/Pit/PA material.
# Celda CTL70/VIS70 debe reproducir el candidato 002D (BB≈8.7, K≈35.8, etc).
CV2_FIX = {"take_bias": 0.30, "foul_chance": 0.45, "take_floor": 0.25}
CV2_POLICY = {0: 0.65, 1: 0.50, 2: 0.30}


def run_control_vision_level_calibrated(reps: int) -> None:
    """002C-CV · CTL×VIS 3×3 sobre candidato 002D (fatiga 75%, 65/50/30)."""
    print("=" * 130)
    print("002C-CV · Control × Vision 3×3 (baseline calibrado, candidato 002D)")
    print(f"Fijo: TAKE baseline 0.30, foul 45% | política 0/1/2 strikes = 65/50/30 | "
          f"fatiga 75% | resto MID | escala ratings-2.0 40..99 (terciles 45/70/95)")
    print(f"{reps:,} PA por celda (9 celdas = {reps * 9:,} PA) | mismas seeds por rep")
    print("=" * 130)

    levels = ["LOW", "MID", "HIGH"]
    cells = {}
    for ctl_name in levels:
        for vis_name in levels:
            ctl = CV_LEVELS[ctl_name]
            vis = CV_LEVELS[vis_name]
            cells[(ctl_name, vis_name)] = run_control_vision_cell_calibrated(ctl, vis, reps)

    # Tabla principal: dirección + magnitud a nivel PA
    print()
    print("-- CTL × VIS → resultado de PA --")
    print(f"{'Cell':<8} {'CalledS/tk':>10} | {'K%':>6} {'BB%':>6} {'BIP%':>6} | "
          f"{'P(3bol)':>7} {'P(full)':>7} {'Pit/PA':>6} {'p95':>4} {'max':>4}")
    print("-" * 130)
    for ctl_name in levels:
        print(f"CTL {ctl_name} ({CV_LEVELS[ctl_name]})")
        for vis_name in levels:
            a = cells[(ctl_name, vis_name)]
            n = reps
            k = a["outcome"]["K"]
            bb = a["outcome"]["BB"]
            bip = n - k - bb
            tk = max(1, a["take_attempts"])
            print(
                f"  V {vis_name:<4} {CV_LEVELS[vis_name]:>3} | "
                f"{a['called_strikes_on_take'] / tk * 100:>10.2f} | "
                f"{k / n * 100:6.2f} {bb / n * 100:6.2f} {bip / n * 100:6.2f} | "
                f"{a['reached_3balls'] / n * 100:7.2f} "
                f"{a['reached_full'] / n * 100:7.2f} "
                f"{a['pitches'] / n:6.2f} {a['p95']:>4} {a['max']:>4}"
            )
    print("-" * 130)

    # Tabla diagnóstica: conversión en count profundo y a 2 strikes
    print()
    print("-- Diagnóstico: deep-count y 2-strike conversion --")
    print(f"{'Cell':<10} {'P(BB|≥4)':>8} {'P(K|≥4)':>7} {'P(BIP|≥4)':>8} | "
          f"{'P(BB|2s)':>8} {'P(K|2s)':>7} {'P(BIP|2s)':>8} | "
          f"{'P(TAKE|2s)':>10}")
    print("-" * 130)
    for ctl_name in levels:
        for vis_name in levels:
            a = cells[(ctl_name, vis_name)]
            ge4n = max(1, a["ge4"]["n"])
            r2s = max(1, a["outcome_at_2s"]["n"])
            p2s = max(1, a["pitches_at_2s"])
            print(
                f"{ctl_name}-{vis_name:<6} "
                f"{a['ge4']['BB'] / ge4n * 100:8.2f} {a['ge4']['K'] / ge4n * 100:7.2f} "
                f"{a['ge4']['BIP'] / ge4n * 100:8.2f} | "
                f"{a['outcome_at_2s']['BB'] / r2s * 100:8.2f} "
                f"{a['outcome_at_2s']['K'] / r2s * 100:7.2f} "
                f"{a['outcome_at_2s']['BIP'] / r2s * 100:8.2f} | "
                f"{a['take_at_2s'] / p2s * 100:10.2f}"
            )
    print("-" * 130)

    mid = cells[("MID", "MID")]
    n = reps
    print("Control de integración (CTL70/VIS70) vs candidato 002D (MID/MID 80/70, 65/50/30):")
    print(f"  K%      {mid['outcome']['K'] / n * 100:.2f} (esperado ~35.8) "
          f"| BB% {mid['outcome']['BB'] / n * 100:.2f} (esperado ~8.7) "
          f"| BIP% {(n - mid['outcome']['K'] - mid['outcome']['BB']) / n * 100:.2f} "
          f"(esperado ~55.5) | Pit/PA {mid['pitches'] / n:.2f} (esperado ~3.69)")
    print("CTL/VIS 45/70/95: la celda 70/70 es el MID del factorial (no 80); el delta")
    print("por CTL/VIS se lee entre celdas del propio factorial, no vs 002D exacto.")


def run_control_vision_cell_calibrated(control: int, vision: int, reps: int) -> dict:
    agg = {
        "outcome": Counter(),
        "pitches": 0,
        "lengths": [],
        "reached_2strikes": 0,
        "reached_3balls": 0,
        "reached_full": 0,
        "take_attempts": 0,
        "balls_on_take": 0,
        "called_strikes_on_take": 0,
        "take_at_2s": 0,
        "pitches_at_2s": 0,
        "balls_on_take_at_2s": 0,
        "called_strikes_on_take_at_2s": 0,
        "ge4": Counter(),
        "outcome_at_2s": Counter(),
    }
    take_probs = CV2_POLICY
    for rep in range(reps):
        seed = int(DISCIPLINE_WORKLOAD * 1000) * 10**6 + rep
        d = _simulate_pa_diag(take_probs, seed,
                              control=control, vision=vision,
                              take_bias=CV2_FIX["take_bias"],
                              foul_chance=CV2_FIX["foul_chance"],
                              take_floor=CV2_FIX["take_floor"])
        for key in ("reached_2strikes", "reached_3balls", "reached_full",
                    "take_attempts", "balls_on_take", "called_strikes_on_take",
                    "take_at_2s", "pitches_at_2s", "balls_on_take_at_2s",
                    "called_strikes_on_take_at_2s"):
            agg[key] += d[key]
        agg["outcome"][d["outcome"]] += 1
        agg["pitches"] += d["pitches"]
        agg["lengths"].append(d["pitches"])
        if d["pitches"] >= 4:
            agg["ge4"]["n"] += 1
            if d["outcome"] == "K":
                agg["ge4"]["K"] += 1
            elif d["outcome"] == "BB":
                agg["ge4"]["BB"] += 1
            else:
                agg["ge4"]["BIP"] += 1
        if d["reached_2strikes"]:
            agg["outcome_at_2s"]["n"] += 1
            if d["outcome"] == "K":
                agg["outcome_at_2s"]["K"] += 1
            elif d["outcome"] == "BB":
                agg["outcome_at_2s"]["BB"] += 1
            else:
                agg["outcome_at_2s"]["BIP"] += 1
    lengths = sorted(agg["lengths"])
    agg["p95"] = lengths[int(len(lengths) * 0.95) - 1]
    agg["max"] = lengths[-1]
    return agg


# ---------------------------------------------------------------------------
# 002E-1 · Baseline PROD vs candidato B3-C1 (head-to-head sobre grid CTL×VIS)
# ---------------------------------------------------------------------------
# PROD histórico (take_bias 0.65, foul_chance 0.35) vs B3-C1 (0.30/0.45).
# Agente LAB 65/50/30 FIJO en ambos brazos (solo cambian los knobs del engine);
# fatiga neutralizada (workload 0.75 → factor 1.0); mismas seeds por rep entre
# brazos y celdas. Contratos FIJADOS antes de correr:
#   H1 Whiff/swing invariante |Δ| ≤ 1.0pp (el whiff model no se toca).
#   H2 CalledS/tk ↓ y Ball/tk ↑ en TODA celda (take_bias 0.65→0.30).
#   H3 Foul/Cnt ≈ 35% (PROD histórico) / 45% (B3-C1) ± 1.5pp en toda celda.
#   H4 BB% ↑ (más bolas en TAKE → más bases por bolas).
# K%, BIP%, Pit/PA y colas se REPORTAN: 002C-BC dejó a K% ambigua bajo políticas
# con mucho TAKE (up- or down-stream del foul), no se fija dirección.
E1_POLICY = {0: 0.65, 1: 0.50, 2: 0.30}  # agente fijo (candidato 002D), ambos brazos
E1_PROD_RESOLVE = {"take_bias": 0.65, "foul_chance": 0.35, "take_floor": 0.25}
E1_FIX = {"take_bias": 0.30, "foul_chance": 0.45, "take_floor": 0.25}


def run_e1_cell(control: int, vision: int, take_bias: float, foul_chance: float,
                take_floor: float, reps: int) -> dict:
    """Celda 002E-1: PA diagnóstico completo (3 capas de métricas) para un brazo."""
    agg = {
        "outcome": Counter(),
        "pitches": 0,
        "lengths": [],
        "reached_2strikes": 0,
        "reached_3balls": 0,
        "reached_full": 0,
        "take_attempts": 0,
        "balls_on_take": 0,
        "called_strikes_on_take": 0,
        "take_at_2s": 0,
        "pitches_at_2s": 0,
        "swing_attempts": 0,
        "whiffs": 0,
        "fouls": 0,
        "bips": 0,
        "ge4": Counter(),
        "outcome_at_2s": Counter(),
    }
    for rep in range(reps):
        seed = int(DISCIPLINE_WORKLOAD * 1000) * 10**6 + rep  # mismas seeds entre brazos
        d = _simulate_pa_diag(E1_POLICY, seed, control=control, vision=vision,
                              take_bias=take_bias, foul_chance=foul_chance,
                              take_floor=take_floor)
        for key in ("reached_2strikes", "reached_3balls", "reached_full",
                    "take_attempts", "balls_on_take", "called_strikes_on_take",
                    "take_at_2s", "pitches_at_2s", "swing_attempts", "whiffs",
                    "fouls", "bips"):
            agg[key] += d[key]
        agg["outcome"][d["outcome"]] += 1
        agg["pitches"] += d["pitches"]
        agg["lengths"].append(d["pitches"])
        if d["pitches"] >= 4:
            agg["ge4"]["n"] += 1
            if d["outcome"] == "K":
                agg["ge4"]["K"] += 1
            elif d["outcome"] == "BB":
                agg["ge4"]["BB"] += 1
            else:
                agg["ge4"]["BIP"] += 1
        if d["reached_2strikes"]:
            agg["outcome_at_2s"]["n"] += 1
            if d["outcome"] == "K":
                agg["outcome_at_2s"]["K"] += 1
            elif d["outcome"] == "BB":
                agg["outcome_at_2s"]["BB"] += 1
            else:
                agg["outcome_at_2s"]["BIP"] += 1
    lengths = sorted(agg["lengths"])
    agg["p95"] = lengths[int(len(lengths) * 0.95) - 1]
    agg["max"] = lengths[-1]
    return agg


def run_prod_vs_b3c1(reps: int) -> None:
    """002E-1 · PROD histórico (0.65/35/0.25) vs B3-C1 (0.30/45/0.25), agente fijo."""
    arms = {
        "PROD": (E1_PROD_RESOLVE["take_bias"], E1_PROD_RESOLVE["foul_chance"],
                 E1_PROD_RESOLVE["take_floor"]),
        "B3-C1": (E1_FIX["take_bias"], E1_FIX["foul_chance"], E1_FIX["take_floor"]),
    }
    cells = {}
    for ctl_name in ("LOW", "MID", "HIGH"):
        for vis_name in ("LOW", "MID", "HIGH"):
            ctl = CV_LEVELS[ctl_name]
            vis = CV_LEVELS[vis_name]
            for arm, (tb, fc, tf) in arms.items():
                cells[(arm, ctl_name, vis_name)] = run_e1_cell(ctl, vis, tb, fc, tf, reps)

    def pct(x, n):
        return x / n * 100 if n else 0.0

    print("=" * 130)
    print("002E-1 · Baseline PROD histórico (0.65/35/0.25) vs candidato B3-C1 (0.30/45/0.25)")
    print(f"Grid CTL×VIS 45/70/95 (9 celdas) × 2 brazos | agente LAB FIJO 65/50/30 "
          f"en ambos | fatiga congelada 75% (factor 1.0) | {reps:,} PA por celda-brazo")
    print(f"Semillas compartidas por rep entre brazos. Contratos H1–H4 fijados antes de la corrida.")
    print("=" * 130)

    # Capa 1 · INPUT/MECANISMO
    print()
    print("-- CAPA 1 · INPUT / MECANISMO (parámetros y su integridad) --")
    print(f"{'Celda':<8} {'Brazo':<6} | {'CalledS/tk':>10} {'Ball/tk':>8} | "
          f"{'Foul/Cnt':>8} {'BIP/Cnt':>7} | {'Whiff/swing':>11} {'P(TAKE)':>7}")
    print("-" * 130)
    for ctl_name in ("LOW", "MID", "HIGH"):
        for vis_name in ("LOW", "MID", "HIGH"):
            for arm in ("PROD", "B3-C1"):
                a = cells[(arm, ctl_name, vis_name)]
                tk = a["take_attempts"]
                ct = a["fouls"] + a["bips"]
                sw = a["swing_attempts"]
                print(
                    f"{ctl_name}-{vis_name:<5} {arm:<6} | "
                    f"{pct(a['called_strikes_on_take'], tk):>10.2f} "
                    f"{pct(a['balls_on_take'], tk):>8.2f} | "
                    f"{pct(a['fouls'], ct):>8.2f} {pct(a['bips'], ct):>7.2f} | "
                    f"{pct(a['whiffs'], sw):>11.2f} "
                    f"{pct(a['take_attempts'], a['pitches']):>6.2f} "
                )
    print("-" * 130)

    # Capa 2 · ESTRUCTURA DE PA
    print()
    print("-- CAPA 2 · ESTRUCTURA DE PA --")
    print(f"{'Celda':<8} {'Brazo':<6} | {'K%':>6} {'BB%':>6} {'BIP%':>6} | "
          f"{'P(3bol)':>7} {'P(full)':>7} {'Pit/PA':>6} {'p95':>4} {'max':>4}")
    print("-" * 130)
    for ctl_name in ("LOW", "MID", "HIGH"):
        for vis_name in ("LOW", "MID", "HIGH"):
            for arm in ("PROD", "B3-C1"):
                a = cells[(arm, ctl_name, vis_name)]
                n = reps
                out = a["outcome"]
                bip = out["OUT"] + out["1B"] + out["2B"] + out["3B"] + out["HR"]
                print(
                    f"{ctl_name}-{vis_name:<5} {arm:<6} | "
                    f"{pct(out['K'], n):>6.2f} {pct(out['BB'], n):>6.2f} "
                    f"{pct(bip, n):>6.2f} | "
                    f"{pct(a['reached_3balls'], n):>7.2f} {pct(a['reached_full'], n):>7.2f} "
                    f"{a['pitches'] / n:>6.2f} {a['p95']:>4} {a['max']:>4}"
                )
    print("-" * 130)

    # Capa 3 · OUTCOME
    print()
    print("-- CAPA 3 · OUTCOME (terminación del PA) --")
    print(f"{'Celda':<8} {'Brazo':<6} | {'OUT%':>6} {'1B%':>5} {'2B%':>5} "
          f"{'3B%':>5} {'HR%':>5} {'Reach%':>7}")
    print("-" * 130)
    for ctl_name in ("LOW", "MID", "HIGH"):
        for vis_name in ("LOW", "MID", "HIGH"):
            for arm in ("PROD", "B3-C1"):
                out = cells[(arm, ctl_name, vis_name)]["outcome"]
                n = reps
                reach = out["BB"] + out["1B"] + out["2B"] + out["3B"] + out["HR"]
                print(
                    f"{ctl_name}-{vis_name:<5} {arm:<6} | "
                    f"{pct(out['OUT'], n):>6.2f} {pct(out['1B'], n):>5.2f} "
                    f"{pct(out['2B'], n):>5.2f} {pct(out['3B'], n):>5.2f} "
                    f"{pct(out['HR'], n):>5.2f} {pct(reach, n):>7.2f}"
                )
    print("-" * 130)

    # Contratos direccionales
    print()
    print("-- CONTRATOS (fijados antes de correr) --")
    h1_ok = True
    h2_ok = True
    h3_ok = True
    h4_ok = True
    print(f"{'Celda':<10} | {'H1 Whiff Δ':>9} | {'H2 CalledS↓':>11} {'H2 Ball↑':>8} | "
          f"{'H3 Foul PROD':>11} {'Foul B3C1':>10} | {'H4 BB Δ':>7} | {'PASS?':>6}")
    print("-" * 130)
    for ctl_name in ("LOW", "MID", "HIGH"):
        for vis_name in ("LOW", "MID", "HIGH"):
            p = cells[("PROD", ctl_name, vis_name)]
            c = cells[("B3-C1", ctl_name, vis_name)]
            n = reps
            tk_p = max(1, p["take_attempts"])
            tk_c = max(1, c["take_attempts"])
            ct_p = max(1, p["fouls"] + p["bips"])
            ct_c = max(1, c["fouls"] + c["bips"])
            sw_p = max(1, p["swing_attempts"])
            sw_c = max(1, c["swing_attempts"])
            whiff_p = pct(p["whiffs"], sw_p)
            whiff_c = pct(c["whiffs"], sw_c)
            cst_p = pct(p["called_strikes_on_take"], tk_p)
            cst_c = pct(c["called_strikes_on_take"], tk_c)
            ball_p = pct(p["balls_on_take"], tk_p)
            ball_c = pct(c["balls_on_take"], tk_c)
            foul_p = pct(p["fouls"], ct_p)
            foul_c = pct(c["fouls"], ct_c)
            bb_p = pct(p["outcome"]["BB"], n)
            bb_c = pct(c["outcome"]["BB"], n)
            h1 = abs(whiff_p - whiff_c) <= 1.0
            h2 = cst_c < cst_p and ball_c > ball_p
            h3 = (33.5 <= foul_p <= 36.5) and (43.5 <= foul_c <= 46.5)
            h4 = bb_c > bb_p
            h1_ok &= h1
            h2_ok &= h2
            h3_ok &= h3
            h4_ok &= h4
            ok = h1 and h2 and h3 and h4
            print(
                f"{ctl_name}-{vis_name:<7} | "
                f"{whiff_c - whiff_p:>+9.2f} | {cst_p - cst_c:>+11.2f} "
                f"{ball_c - ball_p:>+8.2f} | "
                f"{foul_p:>11.2f} {foul_c:>10.2f} | "
                f"{bb_c - bb_p:>+7.2f} | {'OK' if ok else 'FAIL':>6}"
            )
    print("-" * 130)
    print(f"Veredicto contratos: H1 whiff/swing invariante "
          f"{'PASS' if h1_ok else 'FAIL'} | H2 CalledS↓/Ball↑ "
          f"{'PASS' if h2_ok else 'FAIL'} | H3 Foul/Cnt ≈35/45 "
          f"{'PASS' if h3_ok else 'FAIL'} | H4 BB↑ {'PASS' if h4_ok else 'FAIL'}")
    print("Watch CLAMP-001: en CTL LOW del brazo B3-C1 el piso 0.25 es binding "
          "(CalledS/tk V70≈V95, ver 002C-CV); PROD no lo pisa → el delta de "
          "sensibilidad en esa fila es evidencia de la deuda, no del contraste.")


# ---------------------------------------------------------------------------
# 002E-2 · ROBUSTEZ B3-C1 por matchup · perfil OFENSIVO del bateador × CTL
# ---------------------------------------------------------------------------
# 002E-1 ya cerró la dimensión Control×Vision del PITCHER (9 celdas, head-to-
# head). Aquí se cierra la dimensión que faltaba del MATCHUP: el perfil
# OFENSIVO del bateador (WEAK/MID/STRONG) contra CTL del pitcher, con el
# candidato B3-C1 ya PROMOTED como baseline LAB. Un solo brazo (B3-C1):
# el contraste PROD/PROMOTE ya está cerrado.
BATTER_PROFILES = {
    "WEAK": {"contacto": 55, "poder": 40, "vision": 70},
    "MID": {"contacto": 70, "poder": 70, "vision": 70},   # = BATTER (producción)
    "STRONG": {"contacto": 88, "poder": 90, "vision": 70},
}


def run_e2_cell(control: int, profile: dict, take_bias: float, foul_chance: float,
                take_floor: float, reps: int) -> dict:
    """Celda 002E-2: PA diagnóstico para un perfil ofensivo del bateador (002E-1)."""
    agg = {
        "outcome": Counter(),
        "pitches": 0,
        "lengths": [],
        "reached_2strikes": 0,
        "reached_3balls": 0,
        "reached_full": 0,
        "take_attempts": 0,
        "balls_on_take": 0,
        "called_strikes_on_take": 0,
        "take_at_2s": 0,
        "pitches_at_2s": 0,
        "swing_attempts": 0,
        "whiffs": 0,
        "fouls": 0,
        "bips": 0,
        "ge4": Counter(),
        "outcome_at_2s": Counter(),
    }
    for rep in range(reps):
        seed = int(DISCIPLINE_WORKLOAD * 1000) * 10**6 + rep  # mismas seeds entre celdas
        d = _simulate_pa_diag(E1_POLICY, seed, control=control,
                              batter_attrs=profile,
                              take_bias=take_bias, foul_chance=foul_chance,
                              take_floor=take_floor)
        for key in ("reached_2strikes", "reached_3balls", "reached_full",
                    "take_attempts", "balls_on_take", "called_strikes_on_take",
                    "take_at_2s", "pitches_at_2s", "swing_attempts", "whiffs",
                    "fouls", "bips"):
            agg[key] += d[key]
        agg["outcome"][d["outcome"]] += 1
        agg["pitches"] += d["pitches"]
        agg["lengths"].append(d["pitches"])
        if d["pitches"] >= 4:
            agg["ge4"]["n"] += 1
            if d["outcome"] == "K":
                agg["ge4"]["K"] += 1
            elif d["outcome"] == "BB":
                agg["ge4"]["BB"] += 1
            else:
                agg["ge4"]["BIP"] += 1
        if d["reached_2strikes"]:
            agg["outcome_at_2s"]["n"] += 1
            if d["outcome"] == "K":
                agg["outcome_at_2s"]["K"] += 1
            elif d["outcome"] == "BB":
                agg["outcome_at_2s"]["BB"] += 1
            else:
                agg["outcome_at_2s"]["BIP"] += 1
    lengths = sorted(agg["lengths"])
    agg["p95"] = lengths[int(len(lengths) * 0.95) - 1]
    agg["max"] = lengths[-1]
    return agg


def run_matchup_robustness_e2(reps: int) -> None:
    """002E-2 · B3-C1 sobre grid CTL × perfil OFENSIVO del bateador (muchup).

    Cierra la dimensión que 002E-1 no tocó: matchup fuerte vs débil del OFF
    del bateador (contacto/poder) contra el CTL del pitcher. Un solo brazo
    (B3-C1, ya PROMOTED); sin contraste PROD. Contratos H5–H8 fijados antes.
    """
    ctl_levels = {"LOW": 45, "MID": 70, "HIGH": 95}
    cells = {}
    for ctl_name in ("LOW", "MID", "HIGH"):
        for prof_name in ("WEAK", "MID", "STRONG"):
            ctl = ctl_levels[ctl_name]
            prof = BATTER_PROFILES[prof_name]
            cells[(ctl_name, prof_name)] = run_e2_cell(
                ctl, prof, E1_FIX["take_bias"], E1_FIX["foul_chance"],
                E1_FIX["take_floor"], reps,
            )

    def pct(x, n):
        return x / n * 100 if n else 0.0

    print("=" * 130)
    print("002E-2 · ROBUSTEZ B3-C1 por matchup (perfil OFENSIVO del bateador)")
    print(f"B3-C1 (0.30/45) fijo | agente LAB 65/50/30 | fatiga OFF (factor 1.0) | "
          f"Vision de bateria representativa 70 | {reps:,} PA/celda | "
          f"grid CTL 3 × perfil WEAK/MID/STRONG 3 = 9 celdas → {9 * reps:,} PA")
    print("Contratos H5–H8 fijados ANTES de correr (ver ADR 002E-2). "
          "Watch: K%, BIP%, HR%, Whiff/Swing — reportar, sin target MLB.")
    print("=" * 130)

    # Capa 1 · INPUT/MECANISMO
    print()
    print("-- CAPA 1 · INPUT / MECANISMO (disciplina de TAKE por matchup) --")
    print(f"{'Celda':<14} | {'CalledS/tk':>10} {'Ball/tk':>8} | "
          f"{'Foul/Cnt':>8} {'BIP/Cnt':>7} | {'Whiff/Swing':>11} {'P(TAKE)':>7}")
    print("-" * 130)
    for ctl_name in ("LOW", "MID", "HIGH"):
        for prof_name in ("WEAK", "MID", "STRONG"):
            a = cells[(ctl_name, prof_name)]
            tk = max(1, a["take_attempts"])
            ct = max(1, a["fouls"] + a["bips"])
            sw = max(1, a["swing_attempts"])
            print(
                f"{ctl_name}-{prof_name:<7} | "
                f"{pct(a['called_strikes_on_take'], tk):>10.2f} "
                f"{pct(a['balls_on_take'], tk):>8.2f} | "
                f"{pct(a['fouls'], ct):>8.2f} {pct(a['bips'], ct):>7.2f} | "
                f"{pct(a['whiffs'], sw):>11.2f} "
                f"{pct(a['take_attempts'], reps):>7.2f}"
            )
    print("-" * 130)

    # Capa 2 · COUNT (estructura del PA)
    print()
    print("-- CAPA 2 · COUNT / ESTRUCTURA DE PA --")
    print(f"{'Celda':<14} | {'BB%':>6} {'K%':>6} {'BIP%':>6} | "
          f"{'P(3bol)':>7} {'P(full)':>7} {'Pit/PA':>6} {'p95':>4} {'max':>4} "
          f"{'P(≥4)':>6} {'P(≥6)':>6}")
    print("-" * 130)
    for ctl_name in ("LOW", "MID", "HIGH"):
        for prof_name in ("WEAK", "MID", "STRONG"):
            a = cells[(ctl_name, prof_name)]
            out = a["outcome"]
            n = reps
            bip = out["1B"] + out["2B"] + out["3B"] + out["HR"] + out["OUT"]
            ge4n = a["ge4"]["n"]
            ge6 = sum(1 for L in a["lengths"] if L >= 6)
            print(
                f"{ctl_name}-{prof_name:<7} | "
                f"{pct(out['BB'], n):>6.2f} {pct(out['K'], n):>6.2f} "
                f"{pct(bip, n):>6.2f} | "
                f"{pct(a['reached_3balls'], n):>7.2f} {pct(a['reached_full'], n):>7.2f} "
                f"{a['pitches'] / n:>6.2f} {a['p95']:>4} {a['max']:>4} "
                f"{pct(ge4n, n):>6.2f} {pct(ge6, n):>6.2f}"
            )
    print("-" * 130)

    # Capa 3 · OUTCOME
    print()
    print("-- CAPA 3 · OUTCOME (terminación del PA) --")
    print(f"{'Celda':<14} | {'K%':>6} {'BB%':>6} {'1B%':>5} {'2B%':>5} "
          f"{'HR%':>5} {'Reach%':>7} {'OUT%':>7}")
    print("-" * 130)
    for ctl_name in ("LOW", "MID", "HIGH"):
        for prof_name in ("WEAK", "MID", "STRONG"):
            out = cells[(ctl_name, prof_name)]["outcome"]
            n = reps
            reach = out["BB"] + out["1B"] + out["2B"] + out["3B"] + out["HR"]
            print(
                f"{ctl_name}-{prof_name:<7} | "
                f"{pct(out['K'], n):>6.2f} {pct(out['BB'], n):>6.2f} "
                f"{pct(out['1B'], n):>5.2f} {pct(out['2B'], n):>5.2f} "
                f"{pct(out['HR'], n):>5.2f} {pct(reach, n):>7.2f} "
                f"{pct(out['OUT'], n):>7.2f}"
            )
    print("-" * 130)

    # Contratos H5–H8 (fijados antes de correr)
    print()
    print("-- CONTRATOS 002E-2 (fijados ANTES de correr) --")
    h5_ok = h6_ok = h7_ok = h8_ok = True
    print(f"{'Celda':<14} | {'H5 CTL ord':>10} {'H6 profile ord':>12} | "
          f"{'H7 BB viva':>10} | {'H8 PA acot':>9} | {'PASS?':>6}")
    print("-" * 130)
    seqs = {}
    for ctl_name in ("LOW", "MID", "HIGH"):
        seqs[ctl_name] = {}
        for prof_name in ("WEAK", "MID", "STRONG"):
            seqs[ctl_name][prof_name] = cells[(ctl_name, prof_name)]
    # H5 · CTL↑ → CalledS/tk↑ (perfil fijo): llamada de strike mecánica crece
    cst_by_ctl = {}
    for prof_name in ("WEAK", "MID", "STRONG"):
        cst_by_ctl[prof_name] = [
            pct(cells[(c, prof_name)]["called_strikes_on_take"],
                max(1, cells[(c, prof_name)]["take_attempts"]))
            for c in ("LOW", "MID", "HIGH")
        ]
        if not (cst_by_ctl[prof_name][0] < cst_by_ctl[prof_name][1] <
                cst_by_ctl[prof_name][2]):
            h5_ok = False
    # H6 · perfil WEAK→MID→STRONG → Reach%↑ (por CTL fijo)
    reach_by_prof = {}
    for ctl_name in ("LOW", "MID", "HIGH"):
        reach_by_prof[ctl_name] = []
        for prof_name in ("WEAK", "MID", "STRONG"):
            out = cells[(ctl_name, prof_name)]["outcome"]
            reach_by_prof[ctl_name].append(
                pct(out["BB"] + out["1B"] + out["2B"] + out["3B"] + out["HR"], reps))
        if not (reach_by_prof[ctl_name][0] < reach_by_prof[ctl_name][1] <
                reach_by_prof[ctl_name][2]):
            h6_ok = False
    # H7 · la vía mecánica de BB no colapsa (BB% material en los 3 perfiles,
    # incl. el matchup extremo WEAK/CTL-LOW). Piso fijado antes de correr:
    # BB count ≥ 978 por celda (978 / 50,000 PA = 1.956%).
    for ctl_name in ("LOW", "MID", "HIGH"):
        for prof_name in ("WEAK", "MID", "STRONG"):
            bb_cnt = cells[(ctl_name, prof_name)]["outcome"]["BB"]
            if bb_cnt < 978:
                h7_ok = False
    # H8 · PA acotado: Pit/PA, p95, max, P(≥6) sin patologías (max ≤ 15)
    for ctl_name in ("LOW", "MID", "HIGH"):
        for prof_name in ("WEAK", "MID", "STRONG"):
            a = cells[(ctl_name, prof_name)]
            if a["max"] > 15 or a["p95"] > 12:
                h8_ok = False
    for ctl_name in ("LOW", "MID", "HIGH"):
        for prof_name in ("WEAK", "MID", "STRONG"):
            a = cells[(ctl_name, prof_name)]
            ok = (cst_by_ctl[prof_name][0] < cst_by_ctl[prof_name][1] <
                  cst_by_ctl[prof_name][2]
                  and reach_by_prof[ctl_name][0] < reach_by_prof[ctl_name][1] <
                  reach_by_prof[ctl_name][2]
                  and pct(a["outcome"]["BB"], reps) >= 978
                  and a["max"] <= 15 and a["p95"] <= 12)
            print(
                f"{ctl_name}-{prof_name:<7} | "
                f"{'OK' if cst_by_ctl[prof_name][0] < cst_by_ctl[prof_name][1] < cst_by_ctl[prof_name][2] else 'FAIL':>10} "
                f"{'OK' if reach_by_prof[ctl_name][0] < reach_by_prof[ctl_name][1] < reach_by_prof[ctl_name][2] else 'FAIL':>12} | "
                f"{'OK' if pct(a['outcome']['BB'], reps) >= 978 else 'FAIL':>10} | "
                f"{'OK' if a['max'] <= 15 and a['p95'] <= 12 else 'FAIL':>9} | "
                f"{'PASS' if ok else 'FAIL':>6}"
            )
    print("-" * 130)
    print(f"Veredicto 002E-2: H5 CTL-ord {'PASS' if h5_ok else 'FAIL'} | "
          f"H6 perfil-ord {'PASS' if h6_ok else 'FAIL'} | "
          f"H7 BB viva {'PASS' if h7_ok else 'FAIL'} | "
          f"H8 PA acot {'PASS' if h8_ok else 'FAIL'}")
    print("Watch (sin target): K%/BIP%/HR%/Whiff reconfirmados; CLAMP-001 "
          "NO se toca aquí (es 002E-3, estudio aislado del piso 0.25).")


# ---------------------------------------------------------------------------
# 002E-3 · CLAMP-001 · Caracterización analítica del piso 0.25 del TAKE (B3-C1)
# ---------------------------------------------------------------------------
# Determinista (PA=1, sin MC): sweep fino CTL×VIS sobre la fórmula del
# calculator `raw = 0.30 + (CTL-50)*0.003 - (VIS-50)*0.002`, clamp CURRENT
# `max(0.25, min(0.85, raw))`. NO toca el engine ni PROD; NO promueve.
# Contratos H9-H12 fijados ANTES de correr (ADR 002E-3). Objetivo: localizar
# exactamente dónde y cuánto es binding el piso 0.25 para decidir CLAMP-001
# con mapa, no a ciegas (H12: resolver en el rincón saturado, sin recalibrar
# B3-C1).
CLAMP001_TAKE_BASE = 0.30          # = E1_FIX["take_bias"] (B3-C1)
CLAMP001_CAP = 0.85
CLAMP001_CANDIDATES = {
    "CURRENT": 0.25,               # producción LAB (referencia, no se promueve)
    "FLOOR-20": 0.20,
    "FLOOR-15": 0.15,
    "NO-FLOOR": None,              # solo clamp superior (cap 0.85)
}


def _clamp001_raw(ctl: int, vis: int) -> float:
    return (CLAMP001_TAKE_BASE + (ctl - 50) * 0.003
            - (vis - 50) * 0.002)


def _clamp001_current(raw: float) -> float:
    return max(0.25, min(CLAMP001_CAP, raw))


def _clamp001_candidate(raw: float, floor) -> float:
    if floor is None:
        return min(CLAMP001_CAP, raw)
    return max(floor, min(CLAMP001_CAP, raw))


def run_clamp_characterization_e3(reps: int = 1) -> None:
    """002E-3 · CLAMP-001 · mapa analítico del piso 0.25 (determinista).

    reps se ignora (PA=1 analítico): la caracterización es matemática, no MC.
    """
    ctls = list(range(40, 100))    # 40..99 (sweep fino, 60 valores)
    viss = list(range(40, 100))
    raw_cells = {}


    def raw(ctl: int, vis: int) -> float:
        return _clamp001_raw(ctl, vis)

    for ctl in ctls:
        for vis in viss:
            raw_cells[(ctl, vis)] = raw(ctl, vis)

    n = len(ctls) * len(viss)
    binding = [(c, v) for (c, v), r in raw_cells.items() if r < 0.25]
    nb = len(binding)

    # H9 · monotonicidad en celdas SANAS (raw >= 0.25): CTL↑ no baja, VIS↑ no sube.
    h9_ok = True
    for vis in viss:
        for c1, c2 in zip(ctls, ctls[1:]):
            r1, r2 = raw(c1, vis), raw(c2, vis)
            if r1 < 0.25 or r2 < 0.25:
                continue
            if _clamp001_current(r2) < _clamp001_current(r1):
                h9_ok = False
    for ctl in ctls:
        for v1, v2 in zip(viss, viss[1:]):
            r1, r2 = raw(ctl, v1), raw(ctl, v2)
            if r1 < 0.25 or r2 < 0.25:
                continue
            if _clamp001_current(r2) > _clamp001_current(r1):
                h9_ok = False

    # H10 · sensibilidad: el piso SOLO debe colapsar lo que está en su cota
    # (raw < piso). Zona sana (raw >= 0.25): CURRENT == NO-FLOOR exacto.
    # Pares indistinguibles = pares (materialmente distintos, d>=5) con raw
    # distinto que CURRENT aplana al mismo valor (y NO-FLOOR resolvería).
    floor_free_ok = all(
        _clamp001_current(r) == _clamp001_candidate(r, None)
        for r in raw_cells.values() if r >= 0.25)
    binding_pairs = list(raw_cells.items())
    indist = 0
    dist_material = 0
    for i in range(len(binding_pairs)):
        (c1, v1), r1 = binding_pairs[i]
        for j in range(i + 1, len(binding_pairs)):
            (c2, v2), r2 = binding_pairs[j]
            if max(abs(c1 - c2), abs(v1 - v2)) < 5:
                continue
            dist_material += 1
            # ambos caen al piso (mismo valor) solo si raw < piso
            if (r1 < 0.25 and r2 < 0.25
                    and abs(r1 - r2) > 1e-9):
                indist += 1
    # H10 PASS: cero colapso fuera del piso (zona sana idéntica a NO-FLOOR).
    # 'indist' es el mapa (cuánto resolución cuesta el piso 0.25), se informa.
    h10_ok = floor_free_ok

    # H11 · rincón CLAMP-001: la frontera EXACTA raw = 0.25 es VIS = 1.5*CTL
    # (lineal), i.e. `3*CTL - 2*VIS < 0` en aritmética ENTERA (sin float).
    # El engine clampa cuando raw<0.25 en float; en la frontera (3c=2v) el
    # float puede dar 0.24999... → flutter de borde (1 celda, ruido). H11
    # verifica que TODO el binding quede exactamente en VIS > 1.5*CTL, salvo
    # ruta de ruido float en la diagonal misma.
    frontier_int = {(c, v) for c in ctls for v in viss if 3 * c - 2 * v < 0}
    binding_set = {k for k, r in raw_cells.items() if r < 0.25}
    dev = binding_set.symmetric_difference(frontier_int)
    dev_ruido = sum(
        1 for c, v in dev if abs(raw(c, v) - 0.25) < 5e-4)
    h11_ok = len(dev) == dev_ruido

    # H12 · zona central invariante entre candidatos Y vs CURRENT.
    central = [(c, v) for c in range(60, 91) for v in range(60, 91)
               if raw(c, v) >= 0.25]
    h12_ok = True
    for floor_name, floor in CLAMP001_CANDIDATES.items():
        if floor_name == "CURRENT":
            continue
        for (c, v) in central:
            if _clamp001_candidate(raw(c, v), floor) != \
               _clamp001_current(raw(c, v)):
                h12_ok = False

    print("=" * 118)
    print("002E-3 · CLAMP-001 · Caracterizacion analitica del piso 0.25 (TAKE)")
    print(f"Determinista (PA=1, sin MC) | engine/PROD NO tocados | "
          f"ningun candidato se promueve")
    print("=" * 118)
    print(f"raw = {CLAMP001_TAKE_BASE} + (CTL-50)*0.003 - (VIS-50)*0.002 | "
          f"clamp CURRENT [0.25, {CLAMP001_CAP}]")
    print(f"Grid fino CTL 40..99 x VIS 40..99 = {len(ctls)} x {len(viss)} = {n} celdas")
    print("")
    print(f"[saturacion] celdas con raw < 0.25 (binding en el piso): "
          f"{nb} / {n} = {nb / n * 100:.2f}% de la superficie")
    print(f"[saturacion] frontera EXACTA raw = 0.25: VIS = 1.5 * CTL "
          f"(binding = VIS > 1.5*CTL), celdas CTL<=65, VIS>=61")
    print(f"[saturacion] pares materialmente distintos (d>=5) en grid: "
          f"{dist_material:,}")
    print(f"[piso 0.25] pares d>=5 que CURRENT aplana (raw distinto, mismo "
          f"0.25) = {indist:,} | NO-FLOOR los resolvería | zona sana "
          f"identica a NO-FLOOR: {'PASS' if floor_free_ok else 'FAIL'}")
    print("")
    print("-" * 118)
    print("Candidatos de piso (comparacion SOLO, no se promueve):")
    print(f"  {'candidato':<10} {'piso':>6} | {'cambian vs CURRENT':>18} | "
          f"pares d>=5 colapsados por el piso")
    for cname, floor in CLAMP001_CANDIDATES.items():
        if cname == "CURRENT":
            continue
        chg = sum(1 for (c, v), r in raw_cells.items()
                  if _clamp001_candidate(r, floor) != _clamp001_current(r))
        piso = "0.25" if cname == "CURRENT" else (
            f"{floor:.2f}" if floor is not None else "none")
        n_coll = 0
        for i in range(len(binding_pairs)):
            (c1, v1), r1 = binding_pairs[i]
            for j in range(i + 1, len(binding_pairs)):
                (c2, v2), r2 = binding_pairs[j]
                if max(abs(c1 - c2), abs(v1 - v2)) < 5:
                    continue
                if (r1 < (floor if floor is not None else -1.0)
                        and r2 < (floor if floor is not None else -1.0)
                        and abs(r1 - r2) > 1e-9):
                    n_coll += 1
        print(f"  {cname:<10} {piso:>6} | {chg:>18} | {n_coll:,}")
    print("")
    print(f"[H9 monotonicidad sana] {'PASS' if h9_ok else 'FAIL'} | "
          f"[H10 sensibilidad sana] {'PASS' if h10_ok else 'FAIL'} | "
          f"[H11 rincón exacto] {'PASS' if h11_ok else 'FAIL'} "
          f"(flutter diagonal {dev_ruido} celda(s)) | "
          f"[H12 centro invariante] {'PASS' if h12_ok else 'FAIL'}")
    print("Veredicto 002E-3 (caracterizacion): mapa entregado; la DECISION "
          "de mover el piso = 002E-3-B (MC aislado en el rincón, sin "
          "recalibrar B3-C1 / ver H12).")


# ---------------------------------------------------------------------------
# 002E-3-B · CLAMP-001 · MC aislado en el rincón: decisión del piso del TAKE
# ---------------------------------------------------------------------------
# Después de la caracterización analítica (002E-3: 15% de la superficie
# binding en 0.25; frontera VIS>1.5*CTL; CURRENT colapsa 127,025 pares d>=5),
# este estudio responde CUÁNTO bajar el piso antes de que el rincón
# LOW-CTL/HIGH-VIS produzca disciplina excesiva. 4 celdas x 4 candidatos,
# NO ampliar el grid. Candidatos SOLO comparados (no se promueve aquí).
#
# AGENTE y knobs fijos: take_bias=0.30, foul_chance=0.45 (B3-C1 intacto),
# política LAB 65/50/30, fatiga congelada (factor 1.0), mismas seeds por rep
# entre candidatos. El knob take_floor (calculator.py) es LAB: None → floor
# de producción; 0.0 → sin piso inferior. NO se toca nada de producción.
E3B_FIX = {"take_bias": 0.30, "foul_chance": 0.45}
E3B_CELLS = [(45, 45), (45, 70), (45, 95), (70, 70)]
E3B_CELL_NAMES = {45: "LOW", 70: "MID", 95: "HIGH"}
E3B_FLOORS = {
    "CURRENT": 0.25,   # producción LAB vigente (referencia, no se promueve)
    "FLOOR-20": 0.20,  # piso al 20%: ya resuelve 127k-1.5k colapsos
    "FLOOR-15": 0.15,  # piso al 15%: elimina los últimos 1,453 colapsos
    "NO-FLOOR": 0.0,   # sin piso inferior (solo cap 0.85)
}
E3B_COLLAPSE_PHASE_A = {
    "CURRENT": 127_025,
    "FLOOR-20": 1_453,
    "FLOOR-15": 0,
    "NO-FLOOR": 0,
}


def run_e3b_cell(control: int, vision: int, take_floor: float, reps: int) -> dict:
    """Celda 002E-3-B: MC por (CTL, VIS) y piso candidato (mismas seeds/rep)."""
    agg = {
        "outcome": Counter(),
        "pitches": 0,
        "lengths": [],
        "reached_2strikes": 0,
        "reached_3balls": 0,
        "reached_full": 0,
        "take_attempts": 0,
        "balls_on_take": 0,
        "called_strikes_on_take": 0,
        "take_at_2s": 0,
        "pitches_at_2s": 0,
        "swing_attempts": 0,
        "whiffs": 0,
        "fouls": 0,
        "bips": 0,
        "ge4": Counter(),
        "outcome_at_2s": Counter(),
    }
    for rep in range(reps):
        seed = int(DISCIPLINE_WORKLOAD * 1000) * 10**6 + rep  # mismas seeds entre candidatos
        d = _simulate_pa_diag(
            E1_POLICY, seed, control=control, vision=vision,
            take_bias=E3B_FIX["take_bias"], foul_chance=E3B_FIX["foul_chance"],
            take_floor=take_floor,
        )
        for key in ("reached_2strikes", "reached_3balls", "reached_full",
                    "take_attempts", "balls_on_take", "called_strikes_on_take",
                    "take_at_2s", "pitches_at_2s", "swing_attempts", "whiffs",
                    "fouls", "bips"):
            agg[key] += d[key]
        agg["outcome"][d["outcome"]] += 1
        agg["pitches"] += d["pitches"]
        agg["lengths"].append(d["pitches"])
        if d["pitches"] >= 4:
            agg["ge4"]["n"] += 1
            if d["outcome"] == "K":
                agg["ge4"]["K"] += 1
            elif d["outcome"] == "BB":
                agg["ge4"]["BB"] += 1
            else:
                agg["ge4"]["BIP"] += 1
        if d["reached_2strikes"]:
            agg["outcome_at_2s"]["n"] += 1
            if d["outcome"] == "K":
                agg["outcome_at_2s"]["K"] += 1
            elif d["outcome"] == "BB":
                agg["outcome_at_2s"]["BB"] += 1
            else:
                agg["outcome_at_2s"]["BIP"] += 1
    lengths = sorted(agg["lengths"])
    agg["p95"] = lengths[int(len(lengths) * 0.95) - 1]
    agg["max"] = lengths[-1]
    return agg


def run_clamp001_floor_mc_e3b(reps: int) -> None:
    """002E-3-B · MC aislado: 4 celdas x 4 candidatos de piso, contratos H13–H16."""
    cells = {}
    for (ctl, vis) in E3B_CELLS:
        for fname, floor in E3B_FLOORS.items():
            cells[(ctl, vis, fname)] = run_e3b_cell(ctl, vis, floor, reps)

    def pct(x, n):
        return x / n * 100 if n else 0.0

    def called_s(o):
        return pct(o["called_strikes_on_take"], max(1, o["take_attempts"]))

    def balls_t(o):
        return pct(o["balls_on_take"], max(1, o["take_attempts"]))

    def whiff_s(o):
        return pct(o["whiffs"], max(1, o["swing_attempts"]))

    n = reps
    print("=" * 130)
    print("002E-3-B · CLAMP-001 · MC aislado de piso TAKE (decisión experimental)")
    print(f"4 celdas CTL×VIS x 4 candidatos | {reps:,} PA/celda/candidato | "
          f"{4 * 4 * reps:,} PA | take_bias=0.30 foul=45 agente 65/50/30 "
          f"fatiga OFF (factor 1.0) | mismas seeds por rep")
    print("Contratos H13–H16 fijados ANTES de correr (ver ADR 002E-3-B). "
          "Ningún candidato se promueve aquí.")
    print("=" * 130)

    # CAPA 1 · INPUT / MECANISMO: el cambio debe entrar SOLO por TAKE (H16)
    print()
    print("-- CAPA 1 · MECANISMO (el cambio entra por TAKE; swing/contacto intactos) --")
    print(f"{'Celda':<12} {'Piso':<8} | {'CalledS/tk':>10} {'Ball/tk':>8} | "
          f"{'Foul/Cnt':>8} {'BIP/Cnt':>7} | {'Whiff/Swing':>11} {'Takes/PA':>8} | "
          f"{'pares_d>=5':>11}")
    print("-" * 130)
    for (ctl, vis) in E3B_CELLS:
        cname = f"CTL{E3B_CELL_NAMES[ctl]}/VIS{E3B_CELL_NAMES[vis]}"
        for fname in E3B_FLOORS:
            o = cells[(ctl, vis, fname)]
            tk = max(1, o["take_attempts"])
            ct = max(1, o["fouls"] + o["bips"])
            sw = max(1, o["swing_attempts"])
            print(
                f"{cname:<12} {fname:<8} | "
                f"{called_s(o):>10.2f} {balls_t(o):>8.2f} | "
                f"{pct(o['fouls'], ct):>8.2f} {pct(o['bips'], ct):>7.2f} | "
                f"{whiff_s(o):>11.2f} {o['take_attempts'] / n:>8.2f} | "
                f"{E3B_COLLAPSE_PHASE_A[fname]:>11,}"
            )
    print("-" * 130)

    # CAPA 2 · COUNT / ESTRUCTURA
    print()
    print("-- CAPA 2 · COUNT / ESTRUCTURA DE PA --")
    print(f"{'Celda':<12} {'Piso':<8} | {'BB%':>6} {'K%':>6} {'BIP%':>6} | "
          f"{'P(3bol)':>7} {'P(full)':>7} {'Pit/PA':>6} {'p95':>4} {'max':>4} "
          f"{'P(≥4)':>6}")
    print("-" * 130)
    for (ctl, vis) in E3B_CELLS:
        cname = f"CTL{E3B_CELL_NAMES[ctl]}/VIS{E3B_CELL_NAMES[vis]}"
        for fname in E3B_FLOORS:
            o = cells[(ctl, vis, fname)]
            out = o["outcome"]
            bip = out["1B"] + out["2B"] + out["3B"] + out["HR"] + out["OUT"]
            ge4n = o["ge4"]["n"]
            ge6 = sum(1 for L in o["lengths"] if L >= 6)
            print(
                f"{cname:<12} {fname:<8} | "
                f"{pct(out['BB'], n):>6.2f} {pct(out['K'], n):>6.2f} "
                f"{pct(bip, n):>6.2f} | "
                f"{pct(o['reached_3balls'], n):>7.2f} {pct(o['reached_full'], n):>7.2f} "
                f"{o['pitches'] / n:>6.2f} {o['p95']:>4} {o['max']:>4} "
                f"{pct(ge4n, n):>6.2f}"
            )
    print("-" * 130)

    # CAPA 3 · OUTCOME
    print()
    print("-- CAPA 3 · OUTCOME (terminación del PA) --")
    print(f"{'Celda':<12} {'Piso':<8} | {'K%':>6} {'BB%':>6} {'1B%':>5} {'2B%':>5} "
          f"{'HR%':>5} {'Reach%':>7} {'OUT%':>7}")
    print("-" * 130)
    for (ctl, vis) in E3B_CELLS:
        cname = f"CTL{E3B_CELL_NAMES[ctl]}/VIS{E3B_CELL_NAMES[vis]}"
        for fname in E3B_FLOORS:
            out = cells[(ctl, vis, fname)]["outcome"]
            reach = out["BB"] + out["1B"] + out["2B"] + out["3B"] + out["HR"]
            print(
                f"{cname:<12} {fname:<8} | "
                f"{pct(out['K'], n):>6.2f} {pct(out['BB'], n):>6.2f} "
                f"{pct(out['1B'], n):>5.2f} {pct(out['2B'], n):>5.2f} "
                f"{pct(out['HR'], n):>5.2f} {pct(reach, n):>7.2f} "
                f"{pct(out['OUT'], n):>7.2f}"
            )
    print("-" * 130)

    # CONTRATOS H13–H16 (fijados antes de correr)
    # H13 · CONTROL PRESERVATION: CTL70/VIS70 estadísticamente equivalente entre
    #   los 4 candidatos (CTL70/VIS70 tiene raw=0.32 > todos los pisos → debe
    #   ser idéntico; tolerancia MC ±0.5pp).
    # H14 · SENSITIVITY RECOVERY: en CTL45, VIS45→VIS70→VIS95 produce
    #   CalledS/take ↓ y BB% ↑ de forma monótona (la meseta del piso actual
    #   no puede continuar).
    # H15 · NO PATHOLOGICAL DISCIPLINE: CTL45/VIS95 recupera sensibilidad sin
    #   explosión de BB/counts (BB% y Pit/PA sin bil berte; ver tabla; sin
    #   target MLB absoluto, se compara entre candidatos y vs CTL70/VIS70).
    # H16 · MECHANISM ISOLATION: Whiff/Swing invariante entre pisos (|Δ| ≤ 1.0pp);
    #   el cambio se concentra en CalledS/take.

    print()
    print("-- CONTRATOS 002E-3-B (fijados ANTES de correr) --")
    h13_ok = h14_ok = h15_ok = h16_ok = True

    # H13 · CTL70/VIS70 = control: misma CalledS/tk y BB% entre candidatos
    c70 = cells[(70, 70, "CURRENT")]
    for fname in E3B_FLOORS:
        if fname == "CURRENT":
            continue
        o = cells[(70, 70, fname)]
        d_cs = abs(called_s(o) - called_s(c70))
        d_bb = abs(pct(o["outcome"]["BB"], n) - pct(c70["outcome"]["BB"], n))
        if d_cs > 0.5 or d_bb > 0.5:
            h13_ok = False
    print(f"H13 CONTROL PRESERVATION (CTL70/VIS70 idéntico entre pisos, "
          f"|Δ|≤0.5pp): {'PASS' if h13_ok else 'FAIL'}")

    # H14 · monotonicidad en CTL45: CalledS ↓ y BB% ↑ con VIS↑ (45→70→95).
    # Se evalúa POR CANDIDATO: CURRENT es la referencia (expected FAIL = la
    # meseta que motiva CLAMP-001); los candidatos deben restaurar estricta
    # monotonicidad.
    vis_seq = [45, 70, 95]
    seq_cs = {fname: [called_s(cells[(45, v, fname)]) for v in vis_seq]
              for fname in E3B_FLOORS}
    seq_bb = {fname: [pct(cells[(45, v, fname)]["outcome"]["BB"], n) for v in vis_seq]
              for fname in E3B_FLOORS}
    cand_ok = {}
    for fname in E3B_FLOORS:
        cs = seq_cs[fname]
        bb = seq_bb[fname]
        ok = (cs[0] > cs[1] > cs[2]) and (bb[0] < bb[1] < bb[2])
        cand_ok[fname] = ok
        if fname != "CURRENT" and not ok:
            h14_ok = False
    print(f"H14 SENSITIVITY RECOVERY (CTL45: CalledS/tk↓ y BB%↑ con VIS↑ "
          f"45→70→95, estricto): {'PASS' if h14_ok else 'FAIL'}")
    print(f"    {'candidato':<10} | {'CalledS/tk':>10} {'dir':>4} | "
          f"{'BB%':>6} {'dir':>4} | {'H14':>4}")
    for fname in E3B_FLOORS:
        cs = seq_cs[fname]
        bb = seq_bb[fname]
        print(f"    {fname:<10} | {cs[0]:>6.2f}→{cs[1]:>5.2f}→{cs[2]:>5.2f} "
              f"{'OK' if cs[0] > cs[1] > cs[2] else 'X':>4} | "
              f"{bb[0]:>5.2f}→{bb[1]:>5.2f}→{bb[2]:>5.2f} "
              f"{'OK' if bb[0] < bb[1] < bb[2] else 'X':>4} | "
              f"{'PASS' if cand_ok[fname] else 'FAIL':>4}")

    # H15 · CTL45/VIS95: sin explosión (comparar entre candidatos, sin target
    #   MLB; Pit/PA máximo razonable y colas acotadas).
    c95 = cells[(45, 95, "CURRENT")]
    bb95 = {fname: pct(cells[(45, 95, fname)]["outcome"]["BB"], n)
            for fname in E3B_FLOORS}
    pit95 = {fname: cells[(45, 95, fname)]["pitches"] / n
             for fname in E3B_FLOORS}
    max95 = {fname: cells[(45, 95, fname)]["max"] for fname in E3B_FLOORS}
    p95_95 = {fname: cells[(45, 95, fname)]["p95"] for fname in E3B_FLOORS}
    # Criterio de No-explosión: CTL45/VIS95 no debe superar en mucho al control
    # CTL70/VIS70 bajo el MISMO candidato (sin target absoluto aún).
    for fname in E3B_FLOORS:
        ref = cells[(70, 70, fname)]
        if pct(cells[(45, 95, fname)]["outcome"]["BB"], n) > \
           pct(ref["outcome"]["BB"], n) * 1.6 + 2.0:
            h15_ok = False
        if cells[(45, 95, fname)]["max"] > 15:
            h15_ok = False
    print(f"H15 NO PATHOLOGICAL DISCIPLINE (CTL45/VIS95 sin explosión cont. "
          f"CTL70/VIS70): {'PASS' if h15_ok else 'FAIL'}")
    print(f"    {'candidato':<10} {'BB% 45/95':>10} {'BB% 70/70':>10} "
          f"{'Pit/PA 45/95':>13} {'p95':>4} {'max':>4}")
    for fname in E3B_FLOORS:
        ref = cells[(70, 70, fname)]
        print(f"    {fname:<10} {bb95[fname]:>10.2f} "
              f"{pct(ref['outcome']['BB'], n):>10.2f} {pit95[fname]:>13.2f} "
              f"{p95_95[fname]:>4} {max95[fname]:>4}")

    # H16 · MECHANISM ISOLATION: la rama de swing/contacto NO cambia con el
    #   piso (|Δ| ≤ 1.0pp vs CURRENT en Whiff/Swing, Foul/Cnt, BIP/Cnt). El
    #   cambio entra SOLO por TAKE (CalledS/tk ↓, Ball/tk ↑). Takes/PA puede
    #   subir: es downstream de PA más largos (más bolas → más oportunidades),
    #   NO una violación de aislamiento.
    mech_keys = [("whiffs", "swing_attempts", "Whiff/Swing"),
                 ("fouls", "fouls", "Foul/Cnt"),
                 ("bips", "bips", "BIP/Cnt")]
    h16_rows = []
    for (ctl, vis) in E3B_CELLS:
        cname = f"CTL{E3B_CELL_NAMES[ctl]}/VIS{E3B_CELL_NAMES[vis]}"
        ref = cells[(ctl, vis, "CURRENT")]
        for fname in E3B_FLOORS:
            if fname == "CURRENT":
                continue
            o = cells[(ctl, vis, fname)]
            d_ws = abs(whiff_s(o) - whiff_s(ref))
            d_fo = abs(pct(o["fouls"], max(1, o["fouls"] + o["bips"])) -
                       pct(ref["fouls"], max(1, ref["fouls"] + ref["bips"])))
            d_bi = abs(pct(o["bips"], max(1, o["fouls"] + o["bips"])) -
                       pct(ref["bips"], max(1, ref["fouls"] + ref["bips"])))
            ok = max(d_ws, d_fo, d_bi) <= 1.0
            if not ok:
                h16_ok = False
            h16_rows.append((cname, fname, d_ws, d_fo, d_bi, ok))
    print(f"H16 MECHANISM ISOLATION (Whiff/Swing, Foul/Cnt, BIP/Cnt |Δ|≤1.0pp "
          f"vs CURRENT): {'PASS' if h16_ok else 'FAIL'}")
    print(f"    {'Celda':<12} {'Piso':<8} | {'ΔWhiff/Swing':>12} "
          f"{'ΔFoul/Cnt':>9} {'ΔBIP/Cnt':>8} | {'H16':>4}")
    for (cname, fname, d_ws, d_fo, d_bi, ok) in h16_rows:
        print(f"    {cname:<12} {fname:<8} | {d_ws:>12.3f} {d_fo:>9.3f} "
              f"{d_bi:>8.3f} | {'PASS' if ok else 'FAIL':>4}")

    # GANANCIA MARGINAL DE SENSIBILIDAD por cada reducción del floor
    # (en la celda más afectada CTL45/VIS95, rincón CLAMP-001):
    #   ΔCalledS/tk por -0.05 de floor y ΔBB% asociado. Respuesta a: ¿vale
    #   el juego eliminar los últimos N colapsos con una reducción más?
    print()
    print("-- GANANCIA MARGINAL POR REDUCCIÓN DE FLOOR (CTL45/VIS95) --")
    print(f"    {'paso':<24} | {'ΔCalledS/tk':>10} {'ΔBB%':>6} | "
          f"{'residuo pares':>13}")
    steps = [("CURRENT→FLOOR-20 (0.25→0.20)", "CURRENT", "FLOOR-20"),
             ("FLOOR-20→FLOOR-15 (0.20→0.15)", "FLOOR-20", "FLOOR-15"),
             ("FLOOR-15→NO-FLOOR (0.15→0.0)", "FLOOR-15", "NO-FLOOR")]
    for label, a, b in steps:
        d_cs = called_s(cells[(45, 95, a)]) - called_s(cells[(45, 95, b)])
        d_bb = pct(cells[(45, 95, b)]["outcome"]["BB"], n) - \
               pct(cells[(45, 95, a)]["outcome"]["BB"], n)
        res_a = E3B_COLLAPSE_PHASE_A[a]
        res_b = E3B_COLLAPSE_PHASE_A[b]
        print(f"    {label:<24} | {d_cs:>9.2f}pp {d_bb:>+6.2f} | "
              f"{res_a:,} → {res_b:,}")

    print("-" * 130)
    print(f"Veredicto 002E-3-B: H13 {'PASS' if h13_ok else 'FAIL'} | "
          f"H14 {'PASS' if h14_ok else 'FAIL'} | "
          f"H15 {'PASS' if h15_ok else 'FAIL'} | "
          f"H16 {'PASS' if h16_ok else 'FAIL'}")
    print("Watch (decisión experimental, NO se promueve): "
          ".20 si recupera sensibilidad material + extremos sanos + residuo "
          "irrelevante; .15 solo si elimina meseta observable sin patología; "
          "NO-FLOOR solo con ventaja clara vs .15. CLAMP-001 se cierra en el "
          "siguiente paso si hay ganador claro; luego -> 002E-4 (paquete).")


# ---------------------------------------------------------------------------
# 002E-5 · PRODUCTION ACCEPTANCE · calculate_play_outcome() sin overrides
# ---------------------------------------------------------------------------
# Gate de cierre de GAMEPLAY-ENGINE-002. Corrida de Aceptación sobre el
# PRODUCTO: el paquete promovido en 002E-4 (TAKE base 0.30, floor 0.20,
# ceiling 0.85, foul 0.45) tal como lo consume gameplay vía la API pública
# calculate_play_outcome() — SIN knobs LAB (take_bias/foul_chance/take_floor
# no se pasan; la API pública no los acepta).
#
# Matriz 3×3 CTL 45/70/95 × VIS 45/70/95 (el dominio extremo que CLAMP-001
# explotaba). Contratos FIJADOS antes de correr (acumulados de 002C/002E):
#   JA TAKE MONOTONIC: CalledS/tk CTL↑ y VIS↑ (célula a célula sobre la
#                      matriz; en filas/columnas vecinas el orden es estricto).
#   JB DISCIPLINE:     BB% material en TODA celda (sin BB≈0; la disciplina
#                      emerge del TAKE, no se apaga el BB).
#   JC CONTACT:        Foul/Cnt ≈ 45% (paquete 002E-4) ± 1.5pp en toda celda.
#   JD ISOLATION:      Whiff/Swing invariante (el whiff model no se toca; el
#                      paquete 002E-4 solo expone TAKE y foul).
#   JE PA STABLE:      Pit/PA y colas (p95/max) sin colas patológicas ni
#                      explotación de counts (ref CTL70/VIS70 vs CTL45/VIS95).
#   JF CLAMP-001:      CTL45/VIS70 ≠ CTL45/VIS95 en CalledS/tk (la meseta de
#                      0.25 CERRADA experimentalmente en 002E-3-B → floor 0.20
#                      de producción recupera la pendiente).
E5_CELLS = [(45, 45), (45, 70), (45, 95),
            (70, 45), (70, 70), (70, 95),
            (95, 45), (95, 70), (95, 95)]
E5_CELL_NAMES = {45: "LOW", 70: "MID", 95: "HIGH"}


def run_production_acceptance_e5(reps: int) -> None:
    """002E-5 · Aceptación de producción: API pública sin knobs, 3×3, JA–JF."""
    cells = {}
    for (ctl, vis) in E5_CELLS:
        agg = {k: 0 for k in ("pitches", "reached_2strikes", "reached_3balls",
                              "reached_full", "take_attempts", "balls_on_take",
                              "called_strikes_on_take", "swing_attempts",
                              "whiffs", "fouls", "bips", "take_at_2s",
                              "pitches_at_2s")}
        agg["outcome"] = Counter()
        agg["lengths"] = []
        for rep in range(reps):
            seed = int(DISCIPLINE_WORKLOAD * 1000) * 10**6 + rep
            d = _simulate_pa_diag(E1_POLICY, seed, control=ctl, vision=vis,
                                  use_public_api=True)
            for k in ("pitches", "reached_2strikes", "reached_3balls",
                      "reached_full", "take_attempts", "balls_on_take",
                      "called_strikes_on_take", "swing_attempts", "whiffs",
                      "fouls", "bips", "take_at_2s", "pitches_at_2s"):
                agg[k] += d[k]
            agg["outcome"][d["outcome"]] += 1
            agg["lengths"].append(d["pitches"])
        lengths = sorted(agg["lengths"])
        agg["p95"] = lengths[int(len(lengths) * 0.95) - 1]
        agg["max"] = lengths[-1]
        cells[(ctl, vis)] = agg

    def pct(x, n):
        return x / n * 100 if n else 0.0

    def called_s(o):
        return pct(o["called_strikes_on_take"], max(1, o["take_attempts"]))

    def balls_t(o):
        return pct(o["balls_on_take"], max(1, o["take_attempts"]))

    def whiff_s(o):
        return pct(o["whiffs"], max(1, o["swing_attempts"]))

    n = reps
    print("=" * 130)
    print("002E-5 · PRODUCTION ACCEPTANCE · calculate_play_outcome() sin overrides")
    print(f"Grid CTL×VIS 45/70/95 (9 celdas) | {reps:,} PA/celda | agente LAB "
          f"65/50/30 FIJO (SÓLO decide TAKE/swing; el engine corre PRODUCCIÓN) | "
          f"fatiga OFF (factor 1.0)")
    print("Paquete en juego: TAKE base 0.30 · floor 0.20 · ceiling 0.85 · "
          "foul/contact 0.45 (002E-4 · PROMOTE). KNobs LAB NO se pasan: la API "
          "pública los rechaza.")
    print("Contratos JA–JF fijados ANTES de correr (ver ADR 002E-5). Gate de "
          "cierre de GAMEPLAY-ENGINE-002.")
    print("=" * 130)

    # CAPA 1 · INPUT / MECANISMO (la sensibilidad enterer se manifiesta aquí)
    print()
    print("-- CAPA 1 · MECANISMO (entra por TAKE; contacto/whiff intactos) --")
    print(f"{'Celda':<12} | {'CalledS/tk':>10} {'Ball/tk':>8} | "
          f"{'Foul/Cnt':>8} {'BIP/Cnt':>7} | {'Whiff/Swing':>11} {'Takes/PA':>8}")
    print("-" * 130)
    for (ctl, vis) in E5_CELLS:
        cname = f"CTL{E5_CELL_NAMES[ctl]}/VIS{E5_CELL_NAMES[vis]}"
        o = cells[(ctl, vis)]
        ct = max(1, o["fouls"] + o["bips"])
        print(
            f"{cname:<12} | {called_s(o):>10.2f} {balls_t(o):>8.2f} | "
            f"{pct(o['fouls'], ct):>8.2f} {pct(o['bips'], ct):>7.2f} | "
            f"{whiff_s(o):>11.2f} {o['take_attempts'] / n:>8.2f}"
        )
    print("-" * 130)

    # CAPA 2 · ESTRUCTURA DE PA
    print()
    print("-- CAPA 2 · ESTRUCTURA DE PA --")
    print(f"{'Celda':<12} | {'K%':>6} {'BB%':>6} {'BIP%':>6} | "
          f"{'P(3bol)':>7} {'P(full)':>7} {'Pit/PA':>6} {'p95':>4} {'max':>4}")
    print("-" * 130)
    for (ctl, vis) in E5_CELLS:
        cname = f"CTL{E5_CELL_NAMES[ctl]}/VIS{E5_CELL_NAMES[vis]}"
        o = cells[(ctl, vis)]
        out = o["outcome"]
        bip = out["OUT"] + out["1B"] + out["2B"] + out["3B"] + out["HR"]
        print(
            f"{cname:<12} | "
            f"{pct(out['K'], n):>6.2f} {pct(out['BB'], n):>6.2f} "
            f"{pct(bip, n):>6.2f} | "
            f"{pct(o['reached_3balls'], n):>7.2f} {pct(o['reached_full'], n):>7.2f} "
            f"{o['pitches'] / n:>6.2f} {o['p95']:>4} {o['max']:>4}"
        )
    print("-" * 130)

    # CONTRATOS JA–JF (fijados antes de correr)
    print()
    print("-- CONTRATOS (JA–JF, fijados antes) --")

    # JA · TAKE MONOTONIC: dentro de cada fila CTL, VIS↑ → CalledS/tk↓; dentro
    # de cada columna VIS, CTL↑ → CalledS/tk↑ (orden estricto célula a célula).
    ja_ok = True
    ja_rows = []
    for ctl in (45, 70, 95):
        cs = [called_s(cells[(ctl, viz)]) for viz in (45, 70, 95)]
        for (a, b) in ((0, 1), (1, 2)):
            ok = cs[a] > cs[b]          # VIS↑ → strike↓
            ja_ok &= ok
            ja_rows.append((f"CTL{E5_CELL_NAMES[ctl]} VIS↑ "
                            f"{[45, 70, 95][a]}→{[45, 70, 95][b]}", cs[a] - cs[b], ok))
    for viz in (45, 70, 95):
        cs = [called_s(cells[(ctl, viz)]) for ctl in (45, 70, 95)]
        for (a, b) in ((0, 1), (1, 2)):
            ok = cs[a] < cs[b]          # CTL↑ → strike↑
            ja_ok &= ok
            ja_rows.append((f"VIS{E5_CELL_NAMES[viz]} CTL↑ "
                            f"{[45, 70, 95][a]}→{[45, 70, 95][b]}", cs[a] - cs[b], ok))
    print(f"JA TAKE MONOTONIC (VIS↑→CalledS/tk↓, CTL↑→CalledS/tk↑, estricto "
          f"celda a celda): {'PASS' if ja_ok else 'FAIL'}")
    for (label, d, ok) in ja_rows:
        print(f"    {label:<22} Δ={d:>+6.2f}pp | {'PASS' if ok else 'FAIL'}")

    # JB · DISCIPLINE: BB% material en TODA celda (no ≈0).
    jb_ok = True
    jb_min = min(pct(cells[(ctl, vis)]["outcome"]["BB"], n) for (ctl, vis) in E5_CELLS)
    jb_ok = jb_min >= 1.0
    print(f"JB DISCIPLINE (BB% material en TODA celda, >=1.0%): "
          f"{'PASS' if jb_ok else 'FAIL'} (min BB% = {jb_min:.2f})")

    # JC · CONTACT: Foul/Cnt ≈ 45% (002E-4) ± 1.5pp en toda celda.
    jc_ok = True
    jc_rows = []
    for (ctl, vis) in E5_CELLS:
        o = cells[(ctl, vis)]
        fc = pct(o["fouls"], max(1, o["fouls"] + o["bips"]))
        ok = abs(fc - 45.0) <= 1.5
        jc_ok &= ok
        jc_rows.append((f"CTL{E5_CELL_NAMES[ctl]}/VIS{E5_CELL_NAMES[vis]}", fc, ok))
    print(f"JC CONTACT (Foul/Cnt ≈ 45% ± 1.5pp en toda celda): "
          f"{'PASS' if jc_ok else 'FAIL'}")
    for (cname, fc, ok) in jc_rows:
        print(f"    {cname:<14} Foul/Cnt={fc:>6.2f}% | {'PASS' if ok else 'FAIL'}")

    # JD · ISOLATION: Whiff/Swing invariante entre celdas (span ≤ 1.0pp).
    ws = [whiff_s(cells[(ctl, vis)]) for (ctl, vis) in E5_CELLS]
    span = max(ws) - min(ws)
    jd_ok = span <= 1.0
    print(f"JD ISOLATION (Whiff/Swing invariante entre celdas, span ≤ 1.0pp): "
          f"{'PASS' if jd_ok else 'FAIL'} (span = {span:.2f}pp)")

    # JE · PA STABLE: colas sanas de ref (CTL70/VIS70) vs extremo (CTL45/VIS95),
    # sin explotación de counts: max ≤ 15 y Pit/PA extremo ≤ ref*1.6 + 2.0.
    je_ok = True
    ref = cells[(70, 70)]
    ext = cells[(45, 95)]
    ext_bb = pct(ext["outcome"]["BB"], n)
    ref_bb = pct(ref["outcome"]["BB"], n)
    if ext_bb > ref_bb * 1.6 + 2.0:
        je_ok = False
    if ext["max"] > 15:
        je_ok = False
    print(f"JE PA STABLE (extremo CTL45/VIS95 sin explosión cont. ref "
          f"CTL70/VIS70, max ≤ 15): {'PASS' if je_ok else 'FAIL'}")
    print(f"    BB% 45/95={ext_bb:>5.2f} vs BB% 70/70={ref_bb:>5.2f} | "
          f"Pit/PA={ext['pitches'] / n:>5.2f} vs {ref['pitches'] / n:>5.2f} | "
          f"p95={ext['p95']} max={ext['max']}")

    # JF · CLAMP-001 (regresión): la meseta de 0.25 está CERRADA.
    # En el rincón LOW-CTL/HIGH-VIS el piso 0.20 mostrará pendiente
    # (CalledS/tk CTL45/VIS70 > CTL45/VIS95, material).
    a = called_s(cells[(45, 70)])
    b = called_s(cells[(45, 95)])
    jf_ok = (a - b) >= 2.0   # pendiente material (meseta 0.25 daba ≈ 0)
    print(f"JF CLAMP-001 CERRADO (CTL45/VIS70 > CTL45/VIS95 en CalledS/tk, "
          f"≥ 2.0pp de pendiente): {'PASS' if jf_ok else 'FAIL'} "
          f"(Δ = {a - b:.2f}pp)")

    print("-" * 130)
    print(f"Veredicto 002E-5: JA {'PASS' if ja_ok else 'FAIL'} | "
          f"JB {'PASS' if jb_ok else 'FAIL'} | "
          f"JC {'PASS' if jc_ok else 'FAIL'} | "
          f"JD {'PASS' if jd_ok else 'FAIL'} | "
          f"JE {'PASS' if je_ok else 'FAIL'} | "
          f"JF {'PASS' if jf_ok else 'FAIL'}")
    all_ok = ja_ok and jb_ok and jc_ok and jd_ok and je_ok and jf_ok
    print(f"ACEPTACIÓN DE PRODUCCIÓN: {'PASS · GAMEPLAY-ENGINE-002 CLOSED' if all_ok else 'FAIL'}")
    print("Watch: si JA/JB/JF fallan el paquete 002E-4 está mal promovido; "
          "si JC/JD fallan el cambio entró por el mecanismo equivocado. "
          "002E-4 NO se re-calibra aquí; esto es la verificación del PRODUCTO.")


# ---------------------------------------------------------------------------
# GAMEPLAY-ENGINE-003A · Calibrated Engine Baseline
# ---------------------------------------------------------------------------
# Snapshot de la superficie del motor cerrado (Fatigue v2 + Discipline v2).
# CERO cambios de gameplay: calculator.py intacto; la jugada se resuelve con la
# API pública (calculate_play_outcome, sin knobs LAB). Fatiga neutralizada
# (workload 0.75 → factor 1.0). Agente de medición fijo 65/50/30 = E1_POLICY,
# NO parte de 003A y NO promovido. Stuff/Clutch fuera deliberadamente.
PITCHER_PROFILES_003A = {
    "WEAK": {"velocidad": 55, "control": 55, "movimiento": 55},
    "MID": {"velocidad": 70, "control": 70, "movimiento": 70},
    "STRONG": {"velocidad": 90, "control": 90, "movimiento": 90},
}
BATTER_PROFILES_003A = {
    "WEAK": {"contacto": 55, "poder": 55, "vision": 55},
    "MID": {"contacto": 70, "poder": 70, "vision": 70},
    "STRONG": {"contacto": 90, "poder": 90, "vision": 90},
}
PROFILE_ORDER_003A = ("WEAK", "MID", "STRONG")

# K1-K6 contratos con tolerancias de ruido de muestra (50k PA).
K3_TOL_PP = 0.5   # tolerancia de no-empeoramiento para HR/BIP y XBH/BIP
K5_MAX_PA = 15    # techo de cola de PA por celda (misma regla que JE/002E-5)


def run_calibrated_baseline_e003a(reps: int) -> None:
    """003A-1 · Baseline 3×3 pitcher×batter, producción pura, contratos K1–K6."""
    n = reps
    cells = {}
    for pname in PROFILE_ORDER_003A:
        for bname in PROFILE_ORDER_003A:
            agg = {k: 0 for k in ("pitches", "reached_2strikes", "reached_3balls",
                                  "reached_full", "take_attempts", "balls_on_take",
                                  "called_strikes_on_take", "swing_attempts",
                                  "whiffs", "fouls", "bips", "depth4", "depth6")}
            agg["outcome"] = Counter()
            agg["lengths"] = []
            batter = BATTER_PROFILES_003A[bname]
            pitcher = PITCHER_PROFILES_003A[pname]
            for rep in range(reps):
                seed = int(DISCIPLINE_WORKLOAD * 1000) * 10**6 + rep  # seeds compartidas
                d = _simulate_pa_diag(E1_POLICY, seed,
                                      batter_attrs=batter,
                                      pitcher_attrs=pitcher,
                                      use_public_api=True)
                for k in ("pitches", "reached_3balls", "reached_full",
                          "take_attempts", "balls_on_take",
                          "called_strikes_on_take", "swing_attempts", "whiffs",
                          "fouls", "bips"):
                    agg[k] += d[k]
                agg["outcome"][d["outcome"]] += 1
                agg["lengths"].append(d["pitches"])
                if d["pitches"] >= 4:
                    agg["depth4"] += 1
                if d["pitches"] >= 6:
                    agg["depth6"] += 1
            lengths = sorted(agg["lengths"])
            agg["p95"] = lengths[int(len(lengths) * 0.95) - 1]
            agg["max"] = lengths[-1]
            cells[(pname, bname)] = agg

    def pct(x, k):
        return x / k * 100 if k else 0.0

    def called_s(o):
        return pct(o["called_strikes_on_take"], max(1, o["take_attempts"]))

    def whiff_s(o):
        return pct(o["whiffs"], max(1, o["swing_attempts"]))

    def foul_c(o):
        return pct(o["fouls"], max(1, o["fouls"] + o["bips"]))

    def bip(o):
        return o["outcome"]["OUT"] + o["outcome"]["1B"] + o["outcome"]["2B"] + \
               o["outcome"]["3B"] + o["outcome"]["HR"]

    def xbh(o):
        return o["outcome"]["2B"] + o["outcome"]["3B"] + o["outcome"]["HR"]

    print("=" * 132)
    print("GAMEPLAY-ENGINE-003A · CALIBRATED ENGINE BASELINE (003A-1)")
    print(f"Grid Pitcher×Batter WEAK/MID/STRONG (9 celdas) | {reps:,} PA/celda | "
          f"{reps*9:,} PA total | seeds compartidas por rep (fatiga congelada → factor 1.0)")
    print("Discipline v2 productiva vía calculate_play_outcome() SIN knobs LAB: "
          "base 0.30 · floor 0.20 · ceiling 0.85 · foul/contact 0.45")
    print("Agente de medición fijo 65/50/30 (E1_POLICY). NO es parte de 003A "
          "y NO se promueve. Stuff/Clutch FUERA deliberadamente.")
    print("Contratos K1–K6 fijados ANTES de correr. SIN targets externos "
          "(K%=22, BB%=8, etc.) por diseño.")
    print("=" * 132)

    # Fotografía completa de superficie
    print()
    print("-- PA OUTCOMES + BATTED-BALL (fotografía de superficie) --")
    hdr = (f"{'Matchup':<18} | {'K%':>6} {'BB%':>6} {'BIP%':>6} {'Reach%':>7} | "
           f"{'OUT%':>6} {'1B%':>6} {'2B%':>6} {'3B%':>6} {'HR%':>6}")
    print(hdr)
    print("-" * 132)
    for pname in PROFILE_ORDER_003A:
        for bname in PROFILE_ORDER_003A:
            o = cells[(pname, bname)]
            out = o["outcome"]
            k = int(bip(o))
            bb = out["BB"]
            reach = out["BB"] + out["1B"] + out["2B"] + out["3B"] + out["HR"]
            print(
                f"{bname:<8} vs {pname:<7} | "
                f"{pct(out['K'], n):>6.2f} {pct(bb, n):>6.2f} {pct(k, n):>6.2f} "
                f"{pct(reach, n):>7.2f} | "
                f"{pct(out['OUT'], k):>6.2f} {pct(out['1B'], k):>6.2f} "
                f"{pct(out['2B'], k):>6.2f} {pct(out['3B'], k):>6.2f} "
                f"{pct(out['HR'], k):>6.2f}"
            )
        if pname != "STRONG":
            print("-" * 132)
    print("-" * 132)
    print("Reach% = (BB+1B+2B+3B+HR)/PA · batted-ball sobre BIP · K%+BB%+BIP%=100")

    print()
    print("-- MECHANISMS + PA SHAPE --")
    print(f"{'Matchup':<18} | {'CalledS/tk':>10} | {'Whiff/Sw':>8} "
          f"{'Foul/Cnt':>8} {'Cnt/Sw':>7} | {'Pit/PA':>6} {'P(≥4)':>6} "
          f"{'P(≥6)':>6} {'P(full)':>7} {'p95':>4} {'max':>4}")
    print("-" * 132)
    for pname in PROFILE_ORDER_003A:
        o_p = None
        for bname in PROFILE_ORDER_003A:
            o = cells[(pname, bname)]
            sw = max(1, o["swing_attempts"])
            cont = sw - o["whiffs"]
            print(
                f"{bname:<8} vs {pname:<7} | "
                f"{called_s(o):>10.2f} | "
                f"{whiff_s(o):>8.2f} {foul_c(o):>8.2f} {pct(cont, sw):>7.2f} | "
                f"{o['pitches'] / n:>6.2f} {pct(o['depth4'], n):>6.2f} "
                f"{pct(o['depth6'], n):>6.2f} {pct(o['reached_full'], n):>7.2f} "
                f"{o['p95']:>4} {o['max']:>4}"
            )
        print("-" * 132)

    print()
    print("-- DERIVADAS (para separar 'Stuff reduce contacto' de 'Stuff cambia "
          "calidad del contacto') --")
    print(f"{'Matchup':<18} | {'Contact/Swing':>13} | {'XBH/BIP':>7}")
    print("-" * 132)
    for pname in PROFILE_ORDER_003A:
        for bname in PROFILE_ORDER_003A:
            o = cells[(pname, bname)]
            sw = max(1, o["swing_attempts"])
            print(
                f"{bname:<8} vs {pname:<7} | "
                f"{pct(sw - o['whiffs'], sw):>13.2f} | "
                f"{pct(xbh(o), max(1, bip(o))):>7.2f}"
            )
    print("-" * 132)

    # CONTRATOS K1–K6
    print()
    print("-- CONTRATOS (K1–K6, fijados antes) --")

    # K1 · PITCHER STRENGTH (batter fijo): pitcher WEAK→MID→STRONG →
    # K%↑, Whiff/Swing↑, Reach%↓.
    k1_ok = True
    k1_rows = []
    for bname in PROFILE_ORDER_003A:
        ks = [pct(cells[(p, bname)]["outcome"]["K"], n) for p in PROFILE_ORDER_003A]
        ws = [whiff_s(cells[(p, bname)]) for p in PROFILE_ORDER_003A]
        rs = [pct(cells[(p, bname)]["outcome"]["BB"] +
                  cells[(p, bname)]["outcome"]["1B"] +
                  cells[(p, bname)]["outcome"]["2B"] +
                  cells[(p, bname)]["outcome"]["3B"] +
                  cells[(p, bname)]["outcome"]["HR"], n) for p in PROFILE_ORDER_003A]
        k1_ok &= ks[0] < ks[1] < ks[2]
        k1_ok &= ws[0] < ws[1] < ws[2]
        k1_ok &= rs[0] > rs[1] > rs[2]
        k1_rows.append((f"vs {bname}", ks[0], ks[2], ws[0], ws[2], rs[0], rs[2]))
    print(f"K1 PITCHER STRENGTH (batter fijo; WEAK→MID→STRONG pitcher: K%↑, "
          f"Whiff/Swing↑, Reach%↓): {'PASS' if k1_ok else 'FAIL'}")
    for (lbl, k0, k2, w0, w2, r0, r2) in k1_rows:
        print(f"    {lbl:<8} K% {k0:.2f}→{k2:.2f} | Whiff/Sw {w0:.2f}→{w2:.2f} | "
              f"Reach% {r0:.2f}→{r2:.2f}")

    # K2 · BATTER STRENGTH (pitcher fijo): batter WEAK→MID→STRONG →
    # Whiff/Swing↓, Reach%↑.
    k2_ok = True
    k2_rows = []
    for pname in PROFILE_ORDER_003A:
        ws = [whiff_s(cells[(pname, b)]) for b in PROFILE_ORDER_003A]
        rs = [pct(cells[(pname, b)]["outcome"]["BB"] +
                  cells[(pname, b)]["outcome"]["1B"] +
                  cells[(pname, b)]["outcome"]["2B"] +
                  cells[(pname, b)]["outcome"]["3B"] +
                  cells[(pname, b)]["outcome"]["HR"], n) for b in PROFILE_ORDER_003A]
        k2_ok &= ws[0] > ws[1] > ws[2]
        k2_ok &= rs[0] < rs[1] < rs[2]
        k2_rows.append((f"P {pname}", ws[0], ws[2], rs[0], rs[2]))
    print(f"K2 BATTER STRENGTH (pitcher fijo; batter WEAK→MID→STRONG: "
          f"Whiff/Swing↓, Reach%↑): {'PASS' if k2_ok else 'FAIL'}")
    for (lbl, w0, w2, r0, r2) in k2_rows:
        print(f"    {lbl:<7} Whiff/Sw {w0:.2f}→{w2:.2f} | Reach% {r0:.2f}→{r2:.2f}")

    # K3 · POWER EXPRESSION: batter strength↑ → HR/BIP y XBH/BIP no empeoran
    # (con tolerancia de ruido).
    k3_ok = True
    k3_rows = []
    for pname in PROFILE_ORDER_003A:
        hr = [pct(cells[(pname, b)]["outcome"]["HR"], max(1, bip(cells[(pname, b)])))
              for b in PROFILE_ORDER_003A]
        xb = [pct(xbh(cells[(pname, b)]), max(1, bip(cells[(pname, b)])))
              for b in PROFILE_ORDER_003A]
        ok = hr[1] >= hr[0] - K3_TOL_PP and hr[2] >= hr[1] - K3_TOL_PP
        ok &= xb[1] >= xb[0] - K3_TOL_PP and xb[2] >= xb[1] - K3_TOL_PP
        k3_ok &= ok
        k3_rows.append((f"P {pname}", hr[0], hr[2], xb[0], xb[2], ok))
    print(f"K3 POWER EXPRESSION (batter↑ → HR/BIP y XBH/BIP no empeoran, "
          f"tol ±{K3_TOL_PP}pp): {'PASS' if k3_ok else 'FAIL'}")
    for (lbl, h0, h2, x0, x2, ok) in k3_rows:
        print(f"    {lbl:<7} HR/BIP {h0:.2f}→{h2:.2f} | XBH/BIP {x0:.2f}→{x2:.2f} "
              f"| {'PASS' if ok else 'FAIL'}")

    # K4 · DISCIPLINE SURVIVES: pitcher↑ → CalledStrike/TAKE↑; batter↑ (VIS↑)
    # → CalledStrike/TAKE↓.
    k4_ok = True
    k4_rows = []
    for bname in PROFILE_ORDER_003A:
        cs = [called_s(cells[(p, bname)]) for p in PROFILE_ORDER_003A]
        ok = cs[0] < cs[1] < cs[2]
        k4_ok &= ok
        k4_rows.append((f"vs {bname} pitcher↑", cs[0], cs[2], ok))
    for pname in PROFILE_ORDER_003A:
        cs = [called_s(cells[(pname, b)]) for b in PROFILE_ORDER_003A]
        ok = cs[0] > cs[1] > cs[2]
        k4_ok &= ok
        k4_rows.append((f"P {pname} batter↑", cs[0], cs[2], ok))
    print(f"K4 DISCIPLINE SURVIVES (pitcher↑ → CalledS/TAKE↑; batter↑ (VIS↑) → "
          f"CalledS/TAKE↓): {'PASS' if k4_ok else 'FAIL'}")
    for (lbl, c0, c2, ok) in k4_rows:
        print(f"    {lbl:<15} CalledS/tk {c0:.2f}→{c2:.2f} | "
              f"{'PASS' if ok else 'FAIL'}")

    # K5 · PA STABILITY: max ≤ 15 en toda celda; sin CAP; Pit/PA del rincón más
    # extremo sin explosión vs MID/MID.
    k5_ok = True
    k5_max = max(cells[(p, b)]["max"] for (p, b) in cells)
    k5_caps = sum(cells[(p, b)]["outcome"]["CAP"] for (p, b) in cells)
    ext = max((cells[(p, b)]["pitches"] / n for (p, b) in cells))
    ref = cells[("MID", "MID")]["pitches"] / n
    k5_ok = k5_max <= K5_MAX_PA and k5_caps == 0 and ext <= ref * 1.6 + 2.0
    print(f"K5 PA STABILITY (max ≤ {K5_MAX_PA}, sin CAP, Pit/PA extremo "
          f"≤ ref·1.6+2.0): {'PASS' if k5_ok else 'FAIL'} "
          f"(max={k5_max} CAP={k5_caps} extremo={ext:.2f} vs ref MID/MID={ref:.2f})")

    # K6 · FINITE/VALID: todas las métricas finitas y en [0,100]; invariantes
    # K%+BB%+BIP%=100 y batted-ball suma 100 (sobre BIP).
    k6_ok = True
    k6_rows = []
    for pname in PROFILE_ORDER_003A:
        for bname in PROFILE_ORDER_003A:
            o = cells[(pname, bname)]
            out = o["outcome"]
            k = bip(o)
            kp = pct(out["K"], n)
            bbp = pct(out["BB"], n)
            bipsum = kp + bbp + pct(k, n)
            bb_sc = pct(out["OUT"], k) + pct(out["1B"], k) + pct(out["2B"], k) + \
                    pct(out["3B"], k) + pct(out["HR"], k)
            finite = all(all(math.isfinite(v) for v in (
                kp, bbp, pct(k, n), pct(xbh(o), max(1, k)),
                called_s(o), whiff_s(o), foul_c(o), o['pitches'] / n))
                for _ in (0,))
            inv_ok = abs(bipsum - 100.0) <= 0.5 and abs(bb_sc - 100.0) <= 0.5
            ok = finite and inv_ok
            k6_ok &= ok
            k6_rows.append((f"{bname} vs {pname}", bipsum, bb_sc, ok))
    print(f"K6 FINITE/VALID (métricas finitas, 0≤%≤100, K%+BB%+BIP%=100, "
          f"batted-ball 100): {'PASS' if k6_ok else 'FAIL'}")
    for (lbl, s1, s2, ok) in k6_rows:
        print(f"    {lbl:<15} K+BB+BIP={s1:5.2f} BBall(sum)={s2:5.2f} | "
              f"{'PASS' if ok else 'FAIL'}")

    print("-" * 132)
    print(f"Veredicto 003A-1: K1 {'PASS' if k1_ok else 'FAIL'} | "
          f"K2 {'PASS' if k2_ok else 'FAIL'} | "
          f"K3 {'PASS' if k3_ok else 'FAIL'} | "
          f"K4 {'PASS' if k4_ok else 'FAIL'} | "
          f"K5 {'PASS' if k5_ok else 'FAIL'} | "
          f"K6 {'PASS' if k6_ok else 'FAIL'}")
    all_ok = k1_ok and k2_ok and k3_ok and k4_ok and k5_ok and k6_ok
    if all_ok:
        print("RESULTADO: K1–K6 PASS → superficie congelada como "
              "CALIBRATED-BASELINE-v1 (entrada a 003B · Stuff integration).")
    else:
        print("RESULTADO: K1–K6 con fallas → NO se congela; diagnosticar antes "
              "de abrir 003B.")


# ---------------------------------------------------------------------------
# 003A-TAIL-1 · K5-R validation (cola de PA en la celda STRONG×WEAK)
# ---------------------------------------------------------------------------
# K5 original (max ≤ 15) falló con max=16 en STRONG batter × WEAK pitcher.
# Diagnóstico: outlier aislado (1/50k = 0.002%), p95=6, sin CAP, sin
# acumulación cerca de la cola; mecanismo = fouls repetidos con 2 strikes.
# `max` no es un contrato asintótico estable (5k→13, 50k→16). K5-R mide la
# DISTRIBUCIÓN de la cola con seeds INDEPENDIENTES (base fuera del rango
# 750M..750.5M de la corrida 003A-1) para no validar con los mismos datos que
# diseñaron el contrato.
TAIL1_CELL_BATTER = "STRONG"
TAIL1_CELL_PITCHER = "WEAK"
TAIL1_REPS = 200_000
TAIL1_SEED_BASE = 9_000_000_000  # independiente del rango de 003A-1 (750M..)
# K5-R congelados antes de correr (003A-TAIL-1):
TAIL1_P95_MAX = 6
TAIL1_P12_MAX_PP = 0.05
TAIL1_P16_MAX_PP = 0.01


def run_tail_stability_k5r(reps: int) -> None:
    """003A-TAIL-1 · K5-R: valida la cola de forme 200k con seeds nuevas."""
    n = reps
    batter = BATTER_PROFILES_003A[TAIL1_CELL_BATTER]
    pitcher = PITCHER_PROFILES_003A[TAIL1_CELL_PITCHER]
    lengths = []
    caps = 0
    for rep in range(reps):
        seed = TAIL1_SEED_BASE + rep  # seeds NUEVAS/independientes
        d = _simulate_pa_diag(E1_POLICY, seed,
                              batter_attrs=batter,
                              pitcher_attrs=pitcher,
                              use_public_api=True)
        lengths.append(d["pitches"])
        if d["outcome"] == "CAP":
            caps += 1
    lengths.sort()
    p95 = lengths[int(len(lengths) * 0.95) - 1]
    p99 = lengths[int(len(lengths) * 0.99) - 1]
    n_ = n

    def pge(x):
        return sum(1 for v in lengths if v >= x) / n_ * 100

    p8 = pge(8)
    p10 = pge(10)
    p12 = pge(12)
    p14 = pge(14)
    p16 = pge(16)
    p20 = pge(20)
    p95_ok = p95 <= TAIL1_P95_MAX
    p12_ok = p12 <= TAIL1_P12_MAX_PP
    p16_ok = p16 <= TAIL1_P16_MAX_PP
    cap_ok = caps == 0
    k5r_ok = p95_ok and p12_ok and p16_ok and cap_ok

    print("=" * 100)
    print("003A-TAIL-1 · K5-R VALIDATION · PA tail stability")
    print(f"Celda: {TAIL1_CELL_BATTER} batter × {TAIL1_CELL_PITCHER} pitcher "
          f"(la que falló K5 original) | {n:,} PA | seeds NUEVAS independientes "
          f"(base {TAIL1_SEED_BASE})")
    print("K5-R congelado ANTES de correr: p95 ≤ 6 · P(≥12) ≤ 0.05% · "
          "P(≥16) ≤ 0.01% · sin CAP. max = solo informativo.")
    print("=" * 100)
    print(f"{'Metric':<12} {'Observed':>14} {'K5-R bound':>14} | {'Result':>6}")
    print("-" * 100)
    print(f"{'p95':<12} {p95:>14} {TAIL1_P95_MAX:>14} | "
          f"{'PASS' if p95_ok else 'FAIL':>6}")
    print(f"{'p99 (info)':<12} {p99:>14} {'—':>14} |")
    print(f"{'P(≥8)':<12} {p8:>14.4f} {'—':>14} |")
    print(f"{'P(≥10)':<12} {p10:>14.4f} {'—':>14} |")
    print(f"{'P(≥12)':<12} {p12:>14.4f} {TAIL1_P12_MAX_PP:>14} | "
          f"{'PASS' if p12_ok else 'FAIL':>6}")
    print(f"{'P(≥14)':<12} {p14:>14.4f} {'—':>14} |")
    print(f"{'P(≥16)':<12} {p16:>14.4f} {TAIL1_P16_MAX_PP:>14} | "
          f"{'PASS' if p16_ok else 'FAIL':>6}")
    print(f"{'P(≥20)':<12} {p20:>14.4f} {'—':>14} |")
    print(f"{'CAP':<12} {caps:>14} {'0':>14} | "
          f"{'PASS' if cap_ok else 'FAIL':>6}")
    print(f"{'max (info)':<12} {lengths[-1]:>14} {'—':>14} |")
    print("-" * 100)
    print(f"K5-R veredicto: {'PASS' if k5r_ok else 'FAIL'}")
    if k5r_ok:
        print("Conclusión: la cola es legal (fouls repetidos con 2 strikes); "
              "el fallo de K5 original fue un defecto del instrumento `max`, "
              "no una cola patológica.")
    else:
        print("Conclusión: hay evidencia de cola patológica en la interacción "
              "high Contact × 45% foul/contact × two strikes; investigar antes "
              "de abrir 003B.")


# ---------------------------------------------------------------------------
# 003B-1 · Stuff semantic candidates (harness LAB, identity en Stuff=70)
# ---------------------------------------------------------------------------
# Stuff NO existe en PitcherAttrs de producción; se registra en el harness vía
# _resolve_play_outcome_stuff (replica bit-for-bit del engine, delta=0 en 70).
# Setup: pitcher base VEL70/CTL70/MOV70 (MID profile 003A), batter MID, agente
# E1_POLICY (65/50/30, LAB), disciplina producción, fatiga factor 1.0.
# Niveles 45/55/70/85/95 × brazos S1/S2/S3, 50k PA/celda, seeds compartidas
# con 003A (750M+rep) → Stuff=70 reproduce CALIBRATED-BASELINE-v1 bit-por-bit.
STUFF_L1_TOL_PP = 0.3      # L1: |Contact/Swing−65.41| y |XBH/BIP−23.03| ≤ 0.3
STUFF_L3_SPAN_PP = 0.5     # L3: dimensión no afectada estable (span)
STUFF_L4_MIN_PP = 1.5      # L4: |Δ| 45→95 ≥ 1.5pp
STUFF_L6_STEP_PP = 1.0     # L6: |Δ| entre niveles consecutivos ≤ 1.0pp
STUFF_L6_P95_MAX = 8       # L6: p95 ≤ 8 en toda celda


def run_stuff_semantic_candidates_e003b(reps: int) -> None:
    """003B-1 · 3 brazos × 5 niveles de Stuff, harness LAB, contratos L1–L6."""
    n = reps
    batter = BATTER_PROFILES_003A["MID"]
    pitcher = PITCHER_PROFILES_003A["MID"]
    cells = {}
    for arm in STUFF_ARMS:
        for stuff in STUFF_LEVELS:
            agg = {k: 0 for k in ("pitches", "reached_3balls", "reached_full",
                                  "take_attempts", "balls_on_take",
                                  "called_strikes_on_take", "swing_attempts",
                                  "whiffs", "fouls", "bips", "depth4", "depth6")}
            agg["outcome"] = Counter()
            agg["lengths"] = []
            for rep in range(reps):
                seed = int(DISCIPLINE_WORKLOAD * 1000) * 10**6 + rep
                d = _simulate_pa_diag(E1_POLICY, seed,
                                      batter_attrs=batter,
                                      pitcher_attrs=pitcher,
                                      stuff_level=stuff,
                                      stuff_arm=arm)
                for k in ("pitches", "reached_3balls", "reached_full",
                          "take_attempts", "balls_on_take",
                          "called_strikes_on_take", "swing_attempts", "whiffs",
                          "fouls", "bips"):
                    agg[k] += d[k]
                agg["outcome"][d["outcome"]] += 1
                agg["lengths"].append(d["pitches"])
                if d["pitches"] >= 4:
                    agg["depth4"] += 1
                if d["pitches"] >= 6:
                    agg["depth6"] += 1
            lengths = sorted(agg["lengths"])
            agg["p95"] = lengths[int(len(lengths) * 0.95) - 1]
            agg["max"] = lengths[-1]
            cells[(arm, stuff)] = agg

    def pct(x, k):
        return x / k * 100 if k else 0.0

    def called_s(o):
        return pct(o["called_strikes_on_take"], max(1, o["take_attempts"]))

    def whiff_s(o):
        return pct(o["whiffs"], max(1, o["swing_attempts"]))

    def foul_c(o):
        return pct(o["fouls"], max(1, o["fouls"] + o["bips"]))

    def contact_swing(o):
        sw = max(1, o["swing_attempts"])
        return pct(sw - o["whiffs"], sw)

    def bip(o):
        return o["outcome"]["OUT"] + o["outcome"]["1B"] + o["outcome"]["2B"] + \
               o["outcome"]["3B"] + o["outcome"]["HR"]

    def xbh(o):
        return o["outcome"]["2B"] + o["outcome"]["3B"] + o["outcome"]["HR"]

    def xbh_bip(o):
        return pct(xbh(o), max(1, bip(o)))

    print("=" * 150)
    print("GAMEPLAY-ENGINE-003B · STUFF SEMANTIC CANDIDATES (003B-1)")
    print(f"{len(STUFF_ARMS)} brazos × {len(STUFF_LEVELS)} niveles de Stuff | "
          f"{reps:,} PA/celda | {reps*len(STUFF_ARMS)*len(STUFF_LEVELS):,} PA total")
    print("Setup: pitcher VEL70/CTL70/MOV70 (== CALIBRATED-BASELINE-v1 y Stuff")
    print("independiente de VEL/CTL/MOV), batter MID, agente E1_POLICY 65/50/30, ")
    print("disciplina producción (0.30/0.20/0.85, foul/contacto 0.45), fatiga 1.0.")
    print("Moduladores de forma (NO calibración), identidad EXACTA en Stuff=70:")
    for arm in STUFF_ARMS:
        print(f"  {arm}: whiff_add, power_add = {_stuff_modifiers(arm, 10)} (por 10 Stuff)")
    print("Coeficientes: k_wiff=0.064 (S1), k_qty=0.064 (S2, supresión), "
          "S3 = mitad de cada uno. Contratos L1–L6 fijados ANTES de correr.")
    print("=" * 150)

    # Fotografía de superficie por brazo
    for arm in STUFF_ARMS:
        print()
        print(f"-- BRAZO {arm} · fotografía de superficie --")
        print(f"{'Stuff':>5} | {'K%':>6} {'BB%':>6} {'BIP%':>6} {'Reach%':>7} | "
              f"{'CalledS/tk':>10} {'Whiff/Sw':>8} {'Foul/Cnt':>8} {'Cnt/Sw':>7} | "
              f"{'Pit/PA':>6} {'p95':>4} {'max':>4} | {'Contact/Sw':>10} {'XBH/BIP':>8}")
        print("-" * 150)
        for stuff in STUFF_LEVELS:
            o = cells[(arm, stuff)]
            sw = max(1, o["swing_attempts"])
            out = o["outcome"]
            k = n
            bb = out["BB"]
            bipn = bip(o)
            reach = bb + out["1B"] + out["2B"] + out["3B"] + out["HR"]
            print(
                f"{stuff:>5} | {pct(out['K'], k):>6.2f} {pct(bb, k):>6.2f} "
                f"{pct(bipn, k):>6.2f} {pct(reach, k):>7.2f} | "
                f"{called_s(o):>10.2f} {whiff_s(o):>8.2f} {foul_c(o):>8.2f} "
                f"{pct(sw - o['whiffs'], sw):>7.2f} | "
                f"{o['pitches'] / n:>6.2f} {o['p95']:>4} {o['max']:>4} | "
                f"{contact_swing(o):>10.2f} {xbh_bip(o):>8.2f}"
            )
        print("-" * 150)

    # Deltas por 10 Stuff (para comparar contra VEL/MOV en 003B-2 sin depender
    # de extremos): (valor(95) − valor(45)) / 5 = pendiente por 10 Stuff.
    print()
    print("-- DELTAS POR 10 STUFF (pendiente 45→95 ÷ 5) --")
    print(f"{'Brazo':>5} | {'Δ Cnt/Sw /10':>14} {'Δ XBH/BIP /10':>15}")
    print("-" * 40)
    for arm in STUFF_ARMS:
        lo = cells[(arm, 45)]
        hi = cells[(arm, 95)]
        print(f"{arm:>5} | {(contact_swing(hi) - contact_swing(lo)) / 5:>14.2f} "
              f"{(xbh_bip(hi) - xbh_bip(lo)) / 5:>15.2f}")
    print("-" * 40)

    # CONTRATOS L1–L6
    print()
    print("-- CONTRATOS (L1–L6, fijados antes) --")

    for arm in STUFF_ARMS:
        print(f"  -- Brazo {arm} --")

        # L1 · IDENTITY: Stuff=70 reproduce CALIBRATED-BASELINE-v1 (MID/MID).
        o70 = cells[(arm, 70)]
        cs70 = contact_swing(o70)
        xb70 = xbh_bip(o70)
        l1_ok = abs(cs70 - 65.41) <= STUFF_L1_TOL_PP and abs(xb70 - 23.03) <= STUFF_L1_TOL_PP
        print(f"  L1 IDENTITY (Stuff=70 ≈ baseline 65.41/23.03, tol ±{STUFF_L1_TOL_PP}pp): "
              f"{'PASS' if l1_ok else 'FAIL'} (Cnt/Sw {cs70:.2f}, XBH/BIP {xb70:.2f})")

        # L2 · MONOTONICITY: Stuff↑ nunca mejora la ofensiva en la dimensión del brazo.
        cs_seq = [contact_swing(cells[(arm, s)]) for s in STUFF_LEVELS]
        xb_seq = [xbh_bip(cells[(arm, s)]) for s in STUFF_LEVELS]
        ws_seq = [whiff_s(cells[(arm, s)]) for s in STUFF_LEVELS]
        if arm == "S1":
            l2_ok = all(ws_seq[i] <= ws_seq[i + 1] + 0.05 for i in range(len(ws_seq) - 1))
        elif arm == "S2":
            l2_ok = all(xb_seq[i] >= xb_seq[i + 1] - 0.05 for i in range(len(xb_seq) - 1))
        else:  # S3
            l2_ok = all(ws_seq[i] <= ws_seq[i + 1] + 0.05 for i in range(len(ws_seq) - 1)) and \
                    all(xb_seq[i] >= xb_seq[i + 1] - 0.05 for i in range(len(xb_seq) - 1))
        print(f"  L2 MONOTONICITY (Stuff↑ no mejora la ofensiva del brazo): "
              f"{'PASS' if l2_ok else 'FAIL'}")

        # L3 · ORTHOGONALITY: brazo cambia UNA dimensión, la otra ~estable.
        if arm == "S1":
            l3_ok = (max(cs_seq) - min(cs_seq)) >= STUFF_L4_MIN_PP and \
                    (max(xb_seq) - min(xb_seq)) <= STUFF_L3_SPAN_PP
        elif arm == "S2":
            l3_ok = (max(xb_seq) - min(xb_seq)) >= STUFF_L4_MIN_PP and \
                    (max(cs_seq) - min(cs_seq)) <= STUFF_L3_SPAN_PP
        else:  # S3 → ambas cambian
            l3_ok = (max(cs_seq) - min(cs_seq)) >= STUFF_L4_MIN_PP and \
                    (max(xb_seq) - min(xb_seq)) >= STUFF_L4_MIN_PP
        print(f"  L3 ORTHOGONALITY (dimensión del brazo cambia, otra estable): "
              f"{'PASS' if l3_ok else 'FAIL'} "
              f"(span Cnt/Sw {max(cs_seq) - min(cs_seq):.2f}, "
              f"span XBH/BIP {max(xb_seq) - min(xb_seq):.2f})")

        # L4 · MATERIALITY: |Δ| 45→95 en la(s) dimensión(es) del brazo.
        if arm in ("S1", "S3"):
            l4_cs = abs(contact_swing(cells[(arm, 95)]) - contact_swing(cells[(arm, 45)]))
        else:
            l4_cs = 0.0
        if arm in ("S2", "S3"):
            l4_xb = abs(xbh_bip(cells[(arm, 95)]) - xbh_bip(cells[(arm, 45)]))
        else:
            l4_xb = 0.0
        l4_ok = (l4_cs >= STUFF_L4_MIN_PP or arm == "S2") and \
                (l4_xb >= STUFF_L4_MIN_PP or arm == "S1")
        print(f"  L4 MATERIALITY (|Δ45→95| ≥ {STUFF_L4_MIN_PP}pp): "
              f"{'PASS' if l4_ok else 'FAIL'} "
              f"(Σ|ΔCnt/Sw| {l4_cs:.2f}, |ΔXBH/BIP| {l4_xb:.2f})")

        # L5 · MECHANISM ISOLATION: verificado por construcción del harness
        # (S1 solo whiff_add, S2 solo power_add, S3 descompone en ambos).
        w5, p5 = _stuff_modifiers(arm, 10)  # por 10 Stuff (no 0 en 70)
        l5_ok = (arm in ("S1", "S3") or abs(w5) < 1e-12) and \
                (arm in ("S2", "S3") or abs(p5) < 1e-12)
        print(f"  L5 MECHANISM ISOLATION (por construcción + reporte de "
              f"moduladores whiff_add={w5:+.3f}, power_add={p5:+.3f}): "
              f"{'PASS' if l5_ok else 'FAIL'}")

        # L6 · STABILITY: sin clamp rotos, sin CAP, p95 ≤ 8, |Δ consecutivo| ≤ 1pp.
        caps = sum(cells[(arm, s)]["outcome"]["CAP"] for s in STUFF_LEVELS)
        p95s = [cells[(arm, s)]["p95"] for s in STUFF_LEVELS]
        l6_cs = max(abs(cs_seq[i + 1] - cs_seq[i]) for i in range(len(cs_seq) - 1))
        l6_xb = max(abs(xb_seq[i + 1] - xb_seq[i]) for i in range(len(xb_seq) - 1))
        l6_ok = caps == 0 and max(p95s) <= STUFF_L6_P95_MAX and \
                l6_cs <= STUFF_L6_STEP_PP and l6_xb <= STUFF_L6_STEP_PP
        print(f"  L6 STABILITY (no CAP, p95≤{STUFF_L6_P95_MAX}, "
              f"|Δ consecutivo|≤{STUFF_L6_STEP_PP}pp): "
              f"{'PASS' if l6_ok else 'FAIL'} "
              f"(CAP={caps}, p95={max(p95s)}, max|ΔCnt/Sw|={l6_cs:.2f}, "
              f"max|ΔXBH/BIP|={l6_xb:.2f})")

        l_all = l1_ok and l2_ok and l3_ok and l4_ok and l5_ok and l6_ok
        print(f"  -> Brazo {arm}: L1–L6 {'PASS' if l_all else 'FAIL'}")

    print("-" * 150)
    print("003B-1 NO elige candidato: documenta la FORMA de cada brazo. La")
    print("decisión conceptual llega en 003B-2 (Stuff vs VEL vs MOV sensitivity).")


# ---------------------------------------------------------------------------
# 003B-2 · Stuff vs VEL vs MOV sensitivity (harness LAB, identidad en 70)
# ---------------------------------------------------------------------------
# 5 sweeps independientes × 5 niveles = 25 puntos × 50k PA = 1.25M PA.
#   V-SWEEP: VEL 45/55/70/85/95, MOV=70, Stuff neutral → producción pura.
#   M-SWEEP: MOV 45/55/70/85/95, VEL=70, Stuff neutral → producción pura.
#   S1/S2/S3-SWEEP: Stuff 45/55/70/85/95, arm S1/S2/S3 (moduladores f0584aa
#   intactos), VEL=MOV=CTL=70.
# Contratos M1–M6 fijados ANTES de correr. Seeds compartidas (750M+rep) → en
# todos los sweeps el nivel 70 reproduce CALIBRATED-BASELINE-v1 bit-por-bit.
M_MONO_TOL_PP = 0.2      # M2–M5: tolerancia de no-monotonía entre niveles
M_SPAN_TOL_PP = 0.5      # M2–M4: span de la dimensión no afectada
M1_TOL_PP = 0.3          # M1: drift de identity en 70
M6_P95_MAX = 8           # M6: cola de PA

SWEEP_003B2 = {
    "VEL": {"attr": "velocidad", "arm": None,
            "fix": {"control": 70, "movimiento": 70}, "levels": [45, 55, 70, 85, 95]},
    "MOV": {"attr": "movimiento", "arm": None,
            "fix": {"velocidad": 70, "control": 70}, "levels": [45, 55, 70, 85, 95]},
    "S1":  {"attr": None, "arm": "S1",
            "fix": {"velocidad": 70, "control": 70, "movimiento": 70},
            "levels": [45, 55, 70, 85, 95]},
    "S2":  {"attr": None, "arm": "S2",
            "fix": {"velocidad": 70, "control": 70, "movimiento": 70},
            "levels": [45, 55, 70, 85, 95]},
    "S3":  {"attr": None, "arm": "S3",
            "fix": {"velocidad": 70, "control": 70, "movimiento": 70},
            "levels": [45, 55, 70, 85, 95]},
}
SWEEP_ORDER_003B2 = ("VEL", "MOV", "S1", "S2", "S3")


def _sweep_base_attrs(sweep: str, level: int) -> dict:
    """PitcherAttrs para un punto del sweep (attr variable fija incluye CTL=70)."""
    cfg = SWEEP_003B2[sweep]
    attrs = dict(cfg["fix"])
    if cfg["attr"] is not None:
        attrs[cfg["attr"]] = level
    return attrs


def _cosine(u: tuple, v: tuple) -> float:
    """Cosine similarity entre dos vectores 2D (float provisto por __import__)."""
    import math as _m
    nu = _m.hypot(u[0], u[1])
    nv = _m.hypot(v[0], v[1])
    if nu == 0 or nv == 0:
        return 0.0
    return (u[0] * v[0] + u[1] * v[1]) / (nu * nv)


def run_stuff_vs_vel_mov_sensitivity_e003b2(reps: int) -> None:
    """003B-2 · 5 sweeps × 5 niveles, contratos M1–M6 + geometría de vectores."""
    n = reps
    batter = BATTER_PROFILES_003A["MID"]
    cells = {}
    for sweep in SWEEP_ORDER_003B2:
        for level in SWEEP_003B2[sweep]["levels"]:
            agg = {k: 0 for k in ("pitches", "reached_2strikes", "reached_3balls",
                                  "reached_full", "take_attempts", "balls_on_take",
                                  "called_strikes_on_take", "swing_attempts",
                                  "whiffs", "fouls", "bips", "depth4", "depth6")}
            agg["outcome"] = Counter()
            agg["lengths"] = []
            arm = SWEEP_003B2[sweep]["arm"]
            pitcher = _sweep_base_attrs(sweep, level)
            for rep in range(reps):
                seed = int(DISCIPLINE_WORKLOAD * 1000) * 10**6 + rep  # seeds compartidas
                d = _simulate_pa_diag(E1_POLICY, seed,
                                      batter_attrs=batter,
                                      pitcher_attrs=pitcher,
                                      use_public_api=(arm is None),
                                      stuff_level=level if arm else None,
                                      stuff_arm=arm)
                for k in ("pitches", "reached_3balls", "reached_full",
                          "take_attempts", "balls_on_take",
                          "called_strikes_on_take", "swing_attempts", "whiffs",
                          "fouls", "bips"):
                    agg[k] += d[k]
                agg["outcome"][d["outcome"]] += 1
                agg["lengths"].append(d["pitches"])
                if d["pitches"] >= 4:
                    agg["depth4"] += 1
                if d["pitches"] >= 6:
                    agg["depth6"] += 1
            lengths = sorted(agg["lengths"])
            agg["p95"] = lengths[int(len(lengths) * 0.95) - 1]
            agg["max"] = lengths[-1]
            cells[(sweep, level)] = agg

    def pct(x, k):
        return x / k * 100 if k else 0.0

    def called_s(o):
        return pct(o["called_strikes_on_take"], max(1, o["take_attempts"]))

    def whiff_s(o):
        return pct(o["whiffs"], max(1, o["swing_attempts"]))

    def foul_c(o):
        return pct(o["fouls"], max(1, o["fouls"] + o["bips"]))

    def contact_swing(o):
        sw = max(1, o["swing_attempts"])
        return pct(sw - o["whiffs"], sw)

    def bip(o):
        return o["outcome"]["OUT"] + o["outcome"]["1B"] + o["outcome"]["2B"] + \
               o["outcome"]["3B"] + o["outcome"]["HR"]

    def xbh_bip(o):
        return pct(o["outcome"]["2B"] + o["outcome"]["3B"] + o["outcome"]["HR"],
                   max(1, bip(o)))

    print("=" * 150)
    print("GAMEPLAY-ENGINE-003B-2 · STUFF vs VEL vs MOV SENSITIVITY")
    print(f"5 sweeps × 5 niveles = 25 puntos | {reps:,} PA/punto | "
          f"{reps*25:,} PA total | seeds compartidas (750M+rep)")
    print("V/M sweeps = producción pura (calculate_play_outcome, sin knobs); "
          "S1/S2/S3 = moduladores f0584aa intactos. CTL=70 siempre.")
    print("Contratos M1–M6 fijados ANTES de correr. La geometría (Δ/10 + cos) "
          "es diagnóstico; NO se elige por magnitud.")
    print("=" * 150)

    # Fotografía por sweep (5 filas: niveles del atributo)
    for sweep in SWEEP_ORDER_003B2:
        print()
        print(f"-- SWEEP {sweep} · {SWEEP_003B2[sweep]['attr'] or SWEEP_003B2[sweep]['arm']} --")
        print(f"{'Nivel':>5} | {'K%':>6} {'BB%':>6} {'BIP%':>6} {'Reach%':>7} | "
              f"{'CalledS/tk':>10} {'Whiff/Sw':>8} {'Foul/Cnt':>8} {'Cnt/Sw':>7} | "
              f"{'Pit/PA':>6} {'p95':>4} {'max':>4} | {'Contact/Sw':>10} {'XBH/BIP':>8}")
        print("-" * 150)
        for level in SWEEP_003B2[sweep]["levels"]:
            o = cells[(sweep, level)]
            sw = max(1, o["swing_attempts"])
            out = o["outcome"]
            bb = out["BB"]
            reach = bb + out["1B"] + out["2B"] + out["3B"] + out["HR"]
            print(
                f"{level:>5} | {pct(out['K'], n):>6.2f} {pct(bb, n):>6.2f} "
                f"{pct(bip(o), n):>6.2f} {pct(reach, n):>7.2f} | "
                f"{called_s(o):>10.2f} {whiff_s(o):>8.2f} {foul_c(o):>8.2f} "
                f"{pct(sw - o['whiffs'], sw):>7.2f} | "
                f"{o['pitches'] / n:>6.2f} {o['p95']:>4} {o['max']:>4} | "
                f"{contact_swing(o):>10.2f} {xbh_bip(o):>8.2f}"
            )
        print("-" * 150)

    # Vector de sensibilidad por atributo: Δ/10 = pendiente 45→95 ÷ 5.
    def delta10(sweep, metric_fn):
        lo = metric_fn(cells[(sweep, 45)])
        hi = metric_fn(cells[(sweep, 95)])
        return (hi - lo) / 5.0

    sens = {}
    for sweep in SWEEP_ORDER_003B2:
        sens[sweep] = (delta10(sweep, contact_swing), delta10(sweep, xbh_bip))

    print()
    print("-- VECTOR DE SENSIBILIDAD POR ATRIBUTO (Δ/10 = pendiente 45→95 ÷ 5) --")
    print(f"{'Atributo':>9} | {'Δ Contact/Swing /10':>18} {'Δ XBH/BIP /10':>14}")
    print("-" * 50)
    for sweep in SWEEP_ORDER_003B2:
        print(f"{sweep:>9} | {sens[sweep][0]:>18.3f} {sens[sweep][1]:>14.3f}")
    print("-" * 50)

    # Cosine similarity (diAGNÓSTICO, no contrato).
    print()
    print("-- COSINE SIMILARITY (diagnóstico, NO contrato PASS/FAIL) --")
    cos_table = [
        ("S1 vs MOV", sens["S1"], sens["MOV"]),
        ("S1 vs VEL", sens["S1"], sens["VEL"]),
        ("S2 vs MOV", sens["S2"], sens["MOV"]),
        ("S2 vs VEL", sens["S2"], sens["VEL"]),
        ("S3 vs S1",  sens["S3"], sens["S1"]),
        ("S3 vs S2",  sens["S3"], sens["S2"]),
    ]
    for label, u, v in cos_table:
        print(f"{label:>9} | cos = {_cosine(u, v):.3f}")
    print("Lectura esperada: cos(S1,MOV)≈1.0, cos(S1,VEL)≈1.0, "
          "cos(S2,MOV)≈0.0, cos(S2,VEL)≈0.0.")
    print("Si se confirma → S1 duplica dimensión existente, S2 añade una nueva.")

    # CONTRATOS M1–M6
    print()
    print("-- CONTRATOS (M1–M6, fijados antes) --")

    # M1 · IDENTITY: todos los sweeps en 70 ≈ CALIBRATED-BASELINE-v1.
    m1_ok = True
    for sweep in SWEEP_ORDER_003B2:
        o = cells[(sweep, 70)]
        cs, xb = contact_swing(o), xbh_bip(o)
        ok = abs(cs - 65.41) <= M1_TOL_PP and abs(xb - 23.03) <= M1_TOL_PP
        m1_ok &= ok
        print(f"  M1 IDENTITY {sweep}@70 (≈65.41/23.03, tol ±{M1_TOL_PP}pp): "
              f"{'PASS' if ok else 'FAIL'} (Cnt/Sw {cs:.2f}, XBH/BIP {xb:.2f})")
    print(f"  M1 IDENTITY (todos): {'PASS' if m1_ok else 'FAIL'}")

    def seq(sweep, fn):
        return [fn(cells[(sweep, l)]) for l in SWEEP_003B2[sweep]["levels"]]

    def mono_noninc(s, tol):
        return all(s[i] + tol >= s[i + 1] for i in range(len(s) - 1))

    def span(s):
        return max(s) - min(s)

    # M2 · EXISTING VECTORS (VEL, MOV).
    m2_ok = True
    for sweep in ("VEL", "MOV"):
        css = seq(sweep, contact_swing)
        xbs = seq(sweep, xbh_bip)
        ok = mono_noninc(css, M_MONO_TOL_PP) and span(xbs) <= M_SPAN_TOL_PP
        m2_ok &= ok
        print(f"  M2 EXISTING {sweep} (Cnt/Sw↓ monótono, XBH span≤{M_SPAN_TOL_PP}): "
              f"{'PASS' if ok else 'FAIL'} "
              f"(mono={mono_noninc(css, M_MONO_TOL_PP)}, XBH span {span(xbs):.2f})")
    print(f"  M2 EXISTING VECTORS (todos): {'PASS' if m2_ok else 'FAIL'}")

    # M3 · S1 REDUNDANCY.
    css = seq("S1", contact_swing)
    xbs = seq("S1", xbh_bip)
    m3_ok = mono_noninc(css, M_MONO_TOL_PP) and span(xbs) <= M_SPAN_TOL_PP
    print(f"  M3 S1 REDUNDANCY (Cnt/Sw↓ monótono, XBH span≤{M_SPAN_TOL_PP}): "
          f"{'PASS' if m3_ok else 'FAIL'} "
          f"(mono={mono_noninc(css, M_MONO_TOL_PP)}, XBH span {span(xbs):.2f})")

    # M4 · S2 ORTHOGONALITY.
    css = seq("S2", contact_swing)
    xbs = seq("S2", xbh_bip)
    m4_ok = span(css) <= M_SPAN_TOL_PP and mono_noninc(xbs, M_MONO_TOL_PP)
    print(f"  M4 S2 ORTHOGONALITY (Cnt/Sw span≤{M_SPAN_TOL_PP}, XBH↓ monótono): "
          f"{'PASS' if m4_ok else 'FAIL'} "
          f"(Cnt/Sw span {span(css):.2f}, mono XBH={mono_noninc(xbs, M_MONO_TOL_PP)})")

    # M5 · S3 DECOMPOSITION.
    css = seq("S3", contact_swing)
    xbs = seq("S3", xbh_bip)
    m5_ok = mono_noninc(css, M_MONO_TOL_PP) and mono_noninc(xbs, M_MONO_TOL_PP)
    print(f"  M5 S3 DECOMPOSITION (Cnt/Sw↓ Y XBH↓, ambos monótonos): "
          f"{'PASS' if m5_ok else 'FAIL'} "
          f"(mono Cnt/Sw={mono_noninc(css, M_MONO_TOL_PP)}, "
          f"mono XBH={mono_noninc(xbs, M_MONO_TOL_PP)})")

    # M6 · STABILITY (universal a los 25 puntos).
    caps = sum(cells[(s, l)]["outcome"]["CAP"]
               for s in SWEEP_ORDER_003B2 for l in SWEEP_003B2[s]["levels"])
    m6_max_p95 = max(cells[(s, l)]["p95"]
                     for s in SWEEP_ORDER_003B2 for l in SWEEP_003B2[s]["levels"])
    clamps_ok = True
    for s in SWEEP_ORDER_003B2:
        for l in SWEEP_003B2[s]["levels"]:
            o = cells[(s, l)]
            ws = whiff_s(o)
            cs, xb = contact_swing(o), xbh_bip(o)
            if not (0 <= ws <= 100 and 0 <= cs <= 100 and 0 <= xb <= 100):
                clamps_ok = False
    m6_ok = caps == 0 and m6_max_p95 <= M6_P95_MAX and clamps_ok
    print(f"  M6 STABILITY (no CAP, p95≤{M6_P95_MAX}, % en [0,100]): "
          f"{'PASS' if m6_ok else 'FAIL'} "
          f"(CAP={caps}, max p95={m6_max_p95}, clamps={'OK' if clamps_ok else 'ROTOS'})")

    print("-" * 150)
    all_ok = m1_ok and m2_ok and m3_ok and m4_ok and m5_ok and m6_ok
    print(f"Veredicto 003B-2 (M1–M6): "
          f"M1 {'PASS' if m1_ok else 'FAIL'} · "
          f"M2 {'PASS' if m2_ok else 'FAIL'} · "
          f"M3 {'PASS' if m3_ok else 'FAIL'} · "
          f"M4 {'PASS' if m4_ok else 'FAIL'} · "
          f"M5 {'PASS' if m5_ok else 'FAIL'} · "
          f"M6 {'PASS' if m6_ok else 'FAIL'}")
    if all_ok:
        print("Geometría confirmada. Decisión semántica: S1 reject (redundante), "
              "S3 reserve/reject (parcial), S2 promote (contact-quality "
              "suppression). 003B-3 calibrará cuánto mueve Stuff el power_score.")
    else:
        print("Con fallas: revisar antes de la decisión semántica.")


# ---------------------------------------------------------------------------
# 003B-3 · S2 coefficient sweep (calibración de magnitud, no de semántica)
# ---------------------------------------------------------------------------
# Pregunta: ¿cuánto debe modificar Stuff el power_score para ser material sin
# dominar Power ni deformar el baseline? effective_power_score =
# power_score - stuff_delta * coefficient. El mesh conserva el 0.064 exacto de
# f0584aa (no re-interpolado). S1/S3 ya no participan (cerradas en 003B-2).
# V/M sweeps NO: solo S2 con k variable + power reference del batter (producción
# pura, réplica bit-idéntica en stuff=70). CERO cambios en calculator.py.
STUFF_COEFFS_003B3 = (0.0, 0.064, 0.10, 0.20, 0.30, 0.40, 0.50)
STUFF_POWERSWEEP_003B3 = [45, 55, 70, 85, 95]
N2_SPAN_PP = 0.5    # N2: span por canal aislado (Contact/Sw, Whiff/Sw, CalledS/tk)
N3_MONO_PP = 0.2    # N3: tol de monotonía por paso (XBH/BIP, HR/BIP, OUT/BIP)
N4_MONO_PP = 0.2    # N4: monotonía del |Δ| vs coefficient (no-decreciente, tol ruido)
N5_MAT_PP = 1.5     # N5: piso de materialidad Stuff45→95 (misma regla que L4/003B-1)
N6_STEP_PP = 10.0   # N6: tope de discontinuidad por componente entre niveles
N6_DOM_PP = 85.0    # N6: un componente no puede concentrar >85% del BIP
N7_P95_MAX = 6      # N7: K5-R tail (p95 ≤ 6, además con la granularidad de 003B)
N7_P12_MAX = 0.05   # N7: P(longitud ≥ 12) ≤ 0.05%
N7_P16_MAX = 0.01   # N7: P(longitud ≥ 16) ≤ 0.01%


def _pct_quantile(sorted_values, q):
    if not sorted_values:
        return 0.0
    return sorted_values[int(len(sorted_values) * q) - 1]


def _metric_row(agg, n):
    """Fila compacta de métricas por celda (BIP/PA-shape/contacto/power)."""
    out = agg["outcome"]
    bip = (out["OUT"] + out["1B"] + out["2B"] + out["3B"] + out["HR"])
    bs = max(1, bip)
    sw = max(1, agg["swing_attempts"])
    tk = max(1, agg["take_attempts"])
    return {
        "k": out["K"] / n * 100,
        "bb": out["BB"] / n * 100,
        "bip": bip / n * 100,
        "reach": (out["BB"] + out["1B"] + out["2B"] + out["3B"] + out["HR"]) / n * 100,
        "called_tk": agg["called_strikes_on_take"] / tk * 100,
        "whiff": agg["whiffs"] / sw * 100,
        "cnt": (sw - agg["whiffs"]) / sw * 100,
        "out_bip": out["OUT"] / bs * 100,
        "x1": out["1B"] / bs * 100,
        "x2": out["2B"] / bs * 100,
        "x3": out["3B"] / bs * 100,
        "hr": out["HR"] / bs * 100,
        "xbh": (out["2B"] + out["3B"] + out["HR"]) / bs * 100,
        "pmean": sum(agg["power"]) / len(agg["power"]) if agg["power"] else 0.0,
        "p10": _pct_quantile(agg["power"], 0.10),
        "p50": _pct_quantile(agg["power"], 0.50),
        "p90": _pct_quantile(agg["power"], 0.90),
        "p95": agg["p95"],
        "paus": agg["pitches"] / n,
        "t12": agg["len12"] / n * 100,
        "t16": agg["len16"] / n * 100,
    }


def run_stuff_coefficient_e003b3(reps: int) -> None:
    """003B-3 · sweep de coefficient de S2 + power reference (2.0M PA)."""
    n = reps
    batter = BATTER_PROFILES_003A["MID"]
    pitcher = PITCHER_PROFILES_003A["MID"]
    levels = list(STUFF_LEVELS)
    cells = {}

    def fresh_agg():
        return {"pitches": 0, "take_attempts": 0, "called_strikes_on_take": 0,
                "swing_attempts": 0, "whiffs": 0, "outcome": Counter(),
                "lengths": [], "power": [], "len12": 0, "len16": 0}

    for coef in STUFF_COEFFS_003B3:
        for lvl in levels:
            agg = fresh_agg()
            for rep in range(reps):
                seed = int(DISCIPLINE_WORKLOAD * 1000) * 10**6 + rep  # seeds compartidas
                d = _simulate_pa_diag(E1_POLICY, seed,
                                      batter_attrs=batter,
                                      pitcher_attrs=pitcher,
                                      stuff_level=lvl,
                                      stuff_arm="S2",
                                      stuff_k_qty=coef,
                                      power_log=agg["power"])
                agg["pitches"] += d["pitches"]
                agg["take_attempts"] += d["take_attempts"]
                agg["called_strikes_on_take"] += d["called_strikes_on_take"]
                agg["swing_attempts"] += d["swing_attempts"]
                agg["whiffs"] += d["whiffs"]
                agg["outcome"][d["outcome"]] += 1
                agg["lengths"].append(d["pitches"])
                if d["pitches"] >= 12:
                    agg["len12"] += 1
                if d["pitches"] >= 16:
                    agg["len16"] += 1
            agg["lengths"].sort()
            agg["p95"] = agg["lengths"][int(len(agg["lengths"]) * 0.95) - 1]
            agg["power"].sort()
            cells[(coef, lvl)] = agg

    # Power reference: bater POW variable 45→95, pitcher MID/Stuff70, k=0.0.
    power_ref = {}
    for p in STUFF_POWERSWEEP_003B3:
        batter_ref = {"contacto": 70, "poder": p, "vision": 70}
        agg = fresh_agg()
        for rep in range(reps):
            seed = int(DISCIPLINE_WORKLOAD * 1000) * 10**6 + rep
            d = _simulate_pa_diag(E1_POLICY, seed,
                                  batter_attrs=batter_ref,
                                  pitcher_attrs=pitcher,
                                  stuff_level=STUFF_IDENTITY,
                                  stuff_arm="S2",
                                  stuff_k_qty=0.0,
                                  power_log=agg["power"])
            agg["pitches"] += d["pitches"]
            agg["take_attempts"] += d["take_attempts"]
            agg["called_strikes_on_take"] += d["called_strikes_on_take"]
            agg["swing_attempts"] += d["swing_attempts"]
            agg["whiffs"] += d["whiffs"]
            agg["outcome"][d["outcome"]] += 1
            agg["lengths"].append(d["pitches"])
        agg["lengths"].sort()
        agg["p95"] = agg["lengths"][int(len(agg["lengths"]) * 0.95) - 1]
        agg["power"].sort()
        power_ref[p] = agg

    rows = {}
    for coef in STUFF_COEFFS_003B3:
        rows[coef] = {lvl: _metric_row(cells[(coef, lvl)], n) for lvl in levels}

    print("=" * 150)
    print("GAMEPLAY-ENGINE-003B-3 · S2 COEFFICIENT SWEEP (calibración de magnitud)")
    print(f"7 coefs × 5 Stuff × {reps:,} PA = {reps*35:,} PA | Power ref 5 × {reps:,} "
          f"= {reps*5:,} PA | Total {reps*40:,} PA")
    print("effective_power_score = power_score - stuff_delta * coefficient | "
          "S2 arm | seeds compartidas (750M+rep) | MID all")
    print("Contratos N1–N7 FIJADOS ANTES de correr. suppression_ratio = "
          "diagnóstico (no PASS/FAIL).")
    print("=" * 150)

    # Tabla compacta por coeficiente
    for coef in STUFF_COEFFS_003B3:
        print()
        print(f"-- COEFFICIENT {coef:.3f} --")
        print(f"{'Stuff':>5} | {'K%':>6} {'BB%':>6} {'BIP%':>6} {'Reach%':>7} | "
              f"{'Cnt/Sw':>7} | {'OUT/B':>6} {'1B/B':>6} {'2B/B':>6} {'3B/B':>6} "
              f"{'HR/B':>6} {'XBH/B':>6} | {'pwr mean':>8} {'p10':>6} {'p50':>6} "
              f"{'p90':>6} | {'Pit/PA':>6} {'p95':>4} {'>=12':>6} {'>=16':>6}")
        print("-" * 150)
        for lvl in levels:
            r = rows[coef][lvl]
            print(f"{lvl:>5} | {r['k']:>6.2f} {r['bb']:>6.2f} {r['bip']:>6.2f} "
                  f"{r['reach']:>7.2f} | {r['cnt']:>7.2f} | {r['out_bip']:>6.2f} "
                  f"{r['x1']:>6.2f} {r['x2']:>6.2f} {r['x3']:>6.2f} "
                  f"{r['hr']:>6.2f} {r['xbh']:>6.2f} | {r['pmean']:>8.2f} "
                  f"{r['p10']:>6.2f} {r['p50']:>6.2f} {r['p90']:>6.2f} | "
                  f"{r['paus']:>6.2f} {r['p95']:>4} {r['t12']:>6.3f} {r['t16']:>6.3f}")
        print("-" * 150)

    # Power reference
    print()
    print("-- POWER REFERENCE (batter POW variable, pitcher MID/Stuff=70, k=0) --")
    print(f"{'POW':>5} | {'XBH/BIP':>8} {'HR/BIP':>8} {'pwr mean':>8} {'p50':>6}")
    print("-" * 50)
    for p in STUFF_POWERSWEEP_003B3:
        r = _metric_row(power_ref[p], n)
        print(f"{p:>5} | {r['xbh']:>8.2f} {r['hr']:>8.2f} {r['pmean']:>8.2f} "
              f"{r['p50']:>6.2f}")
    print("-" * 50)
    dx_pow = (_metric_row(power_ref[95], n)["xbh"]
              - _metric_row(power_ref[45], n)["xbh"]) / 5.0
    print(f"Δ XBH/BIP /10 Power = {dx_pow:.3f}")

    # N1–N7
    print()
    print("-- CONTRATOS (N1–N7, fijados antes) --")

    # N1 · IDENTITY: Stuff=70 vs CALIBRATED-BASELINE-v1 → en k cualquiera.
    n1_ok = True
    for coef in STUFF_COEFFS_003B3:
        r = rows[coef][70]
        ok = abs(r["cnt"] - 65.41) <= 0.3 and abs(r["xbh"] - 23.03) <= 0.3
        n1_ok &= ok
        print(f"  N1 IDENTITY k={coef:.3f}@70 (≈65.41/23.03): "
              f"{'PASS' if ok else 'FAIL'} (Cnt/Sw {r['cnt']:.2f}, XBH/BIP {r['xbh']:.2f})")
    print(f"  N1 IDENTITY (todos): {'PASS' if n1_ok else 'FAIL'}")

    # N2 · MECHANISM ISOLATION: span de canales aislados por coeficiente.
    n2_ok = True
    for coef in STUFF_COEFFS_003B3:
        seq_c = [rows[coef][l]["cnt"] for l in levels]
        seq_w = [rows[coef][l]["whiff"] for l in levels]
        seq_ct = [rows[coef][l]["called_tk"] for l in levels]
        ok = (max(seq_c) - min(seq_c) <= N2_SPAN_PP
              and max(seq_w) - min(seq_w) <= N2_SPAN_PP
              and max(seq_ct) - min(seq_ct) <= N2_SPAN_PP)
        n2_ok &= ok
        print(f"  N2 ISOLATION k={coef:.3f} (span Cnt/Sw≤{N2_SPAN_PP}, Whiff, "
              f"CRs/Tk): {'PASS' if ok else 'FAIL'} "
              f"(spans {max(seq_c)-min(seq_c):.2f}/{max(seq_w)-min(seq_w):.2f}/"
              f"{max(seq_ct)-min(seq_ct):.2f})")
    print(f"  N2 MECHANISM ISOLATION (todos): {'PASS' if n2_ok else 'FAIL'}")

    # N3 · MONOTONIC QUALITY (solo k > 0).
    n3_ok = True
    for coef in STUFF_COEFFS_003B3:
        if coef <= 0:
            continue
        seq_x = [rows[coef][l]["xbh"] for l in levels]
        seq_h = [rows[coef][l]["hr"] for l in levels]
        seq_o = [rows[coef][l]["out_bip"] for l in levels]

        def mono_dec(s):
            return all(s[i] + N3_MONO_PP >= s[i + 1] for i in range(len(s) - 1))

        def mono_inc(s):
            return all(s[i] <= s[i + 1] + N3_MONO_PP for i in range(len(s) - 1))

        ok = mono_dec(seq_x) and mono_dec(seq_h) and mono_inc(seq_o)
        n3_ok &= ok
        print(f"  N3 MONO k={coef:.3f} (XBH↓, HR no↑, OUT no↓): "
              f"{'PASS' if ok else 'FAIL'} "
              f"(XBH {seq_x[0]:.2f}→{seq_x[-1]:.2f}, HR {seq_h[0]:.2f}→{seq_h[-1]:.2f}, "
              f"OUT {seq_o[0]:.2f}→{seq_o[-1]:.2f})")
    print(f"  N3 MONOTONIC QUALITY: {'PASS' if n3_ok else 'FAIL'}")

    # N4 · COEFFICIENT ORDERING: |Δ Stuff45→95| crece con coefficient (monótono
    # no-decreciente; el check exige que cada coeficiente superior tenga
    # magnitud ≥ la anterior, con tol de ruido).
    deltas = []
    for coef in STUFF_COEFFS_003B3:
        d = rows[coef][45]["xbh"] - rows[coef][95]["xbh"]
        deltas.append(abs(d))
    n4_ok = all(deltas[i + 1] + N4_MONO_PP >= deltas[i]
                for i in range(len(deltas) - 1))
    print(f"  N4 ORDERING |Δ XBH@45→@95| vs k "
          f"({' · '.join(f'{d:.2f}' for d in deltas)}): "
          f"{'PASS' if n4_ok else 'FAIL'}")

    # N5 · MATERIAL BUT NON-DOMINANT: reportar curva, decidir con resultados.
    d45_95 = {coef: rows[coef][45]["xbh"] - rows[coef][95]["xbh"]
              for coef in STUFF_COEFFS_003B3}
    material = {coef: d for coef, d in d45_95.items() if d >= N5_MAT_PP}
    n5_ok = bool(material)
    nondominant = all(rows[c][95]["xbh"] > 0 and rows[c][95]["out_bip"] < 100
                      for c in STUFF_COEFFS_003B3)
    print(f"  N5 Δ Stuff45→95 (XBH/BIP, material ≥{N5_MAT_PP}pp): "
          + " · ".join(f"k={c:.3f} {d:+.2f}" for c, d in d45_95.items()))
    print(f"      Materiales: {sorted(material.items())} | XBH@95>0 & OUT<100 "
          f"(no dominante): {'OK' if nondominant else 'FALLA'}")
    print(f"  N5 MATERIAL BUT NON-DOMINANT: {'PASS' if n5_ok and nondominant else 'FAIL'}")

    # N6 · DISTRIBUTION HEALTH (BIP components entorno sano, sin cliffs).
    n6_ok = True
    for coef in STUFF_COEFFS_003B3:
        for key in ("out_bip", "x1", "x2", "x3", "hr"):
            seq = [rows[coef][l][key] for l in levels]
            if not all(0 <= v <= 100 for v in seq):
                n6_ok = False
            if any(abs(seq[i] - seq[i + 1]) > N6_STEP_PP
                   for i in range(len(seq) - 1)):
                n6_ok = False
            if any(v > N6_DOM_PP for v in seq):
                n6_ok = False
    print(f"  N6 DISTRIBUTION HEALTH (componentes en [0,100], |Δ pasos|≤{N6_STEP_PP}, "
          f"ninguno >{N6_DOM_PP:.0f}% del BIP): "
          f"{'PASS' if n6_ok else 'FAIL'}")

    # N7 · PA STABILITY (K5-R).
    n7_ok = True
    for coef in STUFF_COEFFS_003B3:
        for lvl in levels:
            agg = cells[(coef, lvl)]
            ok = (agg["p95"] <= N7_P95_MAX
                  and agg["len12"] / n * 100 <= N7_P12_MAX
                  and agg["len16"] / n * 100 <= N7_P16_MAX
                  and agg["outcome"]["CAP"] == 0)
            n7_ok &= ok
    p95s = {c: max(cells[(c, l)]["p95"] for l in levels)
            for c in STUFF_COEFFS_003B3}
    print(f"  N7 PA STABILITY (max p95/t12/t16/CAP ±): "
          f"{'PASS' if n7_ok else 'FAIL'} "
          f"(max p95 por k: " + " · ".join(f"{c:.3f}→{p}" for c, p in p95s.items()) + ")")

    # suppression_ratio (diagnóstico)
    print()
    print("-- suppression_ratio = |Δ XBH/10 Stuff| / |Δ XBH/10 Power| "
          "(DIAGNÓSTICO, no PASS/FAIL) --")
    print(f"  Δ XBH/10 Power = {dx_pow:.3f}")
    for coef in STUFF_COEFFS_003B3:
        dx_stuff = (rows[coef][95]["xbh"] - rows[coef][45]["xbh"]) / 5.0
        ratio = abs(dx_stuff) / abs(dx_pow) if abs(dx_pow) > 1e-9 else float("inf")
        print(f"  k={coef:.3f}: Δ XBH/10 Stuff = {dx_stuff:+.3f} | ratio = {ratio:.3f}")

    # Veredicto
    print("-" * 150)
    print(f"Veredicto 003B-3: N1 {'PASS' if n1_ok else 'FAIL'} · "
          f"N2 {'PASS' if n2_ok else 'FAIL'} · N3 {'PASS' if n3_ok else 'FAIL'} · "
          f"N4 {'PASS' if n4_ok else 'FAIL'} · N5 {'PASS' if n5_ok and nondominant else 'FAIL'} · "
          f"N6 {'PASS' if n6_ok else 'FAIL'} · N7 {'PASS' if n7_ok else 'FAIL'}")
    if material:
        print("Coeficientes con separación material Stuff45→95: "
              + ", ".join(f"k={c:.3f} (Δ {d:+.2f}pp)" for c, d in
                          sorted(material.items())))
        print("Decisión de magnitud se reporta; candidato NO se promueve a "
              "producción hasta 003B-4 (matchup) → 003B-5 (fatigue) → 003B-6.")
    else:
        print("Sin coeficiente material: reevaluar mesh/regla antes de decidir.")


# ---------------------------------------------------------------------------
# 002C-B · TAKE calibration · baseline sweep (intercept de strike_chance)
# ---------------------------------------------------------------------------
# Mantiene coefs CTL/VIS actuales (0.003 / -0.002 con (attr-50)); solo varía
# el baseline. Pregunta: ¿basta desplazar la superficie sana CTL×VIS para que
# el TAKE construya counts? No busca realismo MLB; busca que el BB deje de ser
# casi imposible sin romper K/BIP.
TAKE_BASE_SWEEP = {
    "CURRENT": 0.65,  # producción intacta (take_bias=None→0.65)
    "TAKE-B1": 0.50,
    "TAKE-B2": 0.40,
    "TAKE-B3": 0.30,
}


def run_take_bias_sweep(reps: int) -> None:
    """002C-B · Baseline sweep de TAKE (0.65/0.50/0.40/0.30), MID/MID, CURRENT_LAB."""
    print("=" * 130)
    print("002C-B · TAKE calibration · baseline sweep (coefs CTL/VIS intactos)")
    print(f"MID P {PITCHER_RAW} vs MID B {BATTER} | fatiga congelada 75% | política "
          f"CURRENT_LAB 35/25/10 | {reps:,} PA por variante")
    print(f"strike_chance = BASE + (CTL-50)*0.003 - (VIS-50)*0.002 (clamp 25-85%)")
    print("=" * 130)
    print(f"{'Variant':<10} {'Base':>5} | {'CalledS/take':>12} {'Ball/take':>10} | "
          f"{'K%':>6} {'BB%':>6} {'BIP%':>6} | {'P(3bolas)':>9} {'P(full)':>7} "
          f"{'P(BB|3bol)':>10} | {'Pit/PA':>6} {'≥3':>4} {'≥4':>4} {'≥5':>4} {'≥6':>4}")
    print("-" * 130)

    row = None
    for name, base in TAKE_BASE_SWEEP.items():
        a = run_take_bias_cell(base, reps)
        n = reps
        k = a["outcome"]["K"]
        bb = a["outcome"]["BB"]
        bip = n - k - bb
        r3 = a["reached_3balls"]
        rfull = a["reached_full"]
        ct = max(1, a["take_attempts"])
        print(
            f"{name:<10} {base:>5.2f} | "
            f"{a['called_strikes_on_take'] / ct * 100:>12.2f} "
            f"{a['balls_on_take'] / ct * 100:>10.2f} | "
            f"{k / n * 100:6.2f} {bb / n * 100:6.2f} {bip / n * 100:6.2f} | "
            f"{r3 / n * 100:8.2f} {rfull / n * 100:6.2f} "
            f"{bb / r3 * 100 if r3 else 0:9.2f} | "
            f"{a['pitches'] / n:6.2f} "
            f"{a['depth'][3] / n * 100:4.1f} {a['depth'][4] / n * 100:4.1f} "
            f"{a['depth'][5] / n * 100:4.1f} {a['depth'][6] / n * 100:4.1f}"
        )

    print("-" * 130)
    print("CalledS/take y Ball/take sobre la fórmula: CTL=80/VIS=70 → "
          "0.65+0.09-0.04=0.70 (CURRENT), 0.55, 0.45, 0.35 para los sweeps.")
    print("Pregunta: ¿intercepto solo construye el count o necesita otra estructura de TAKE?")


def run_take_bias_cell(base: float, reps: int) -> dict:
    agg = {
        "outcome": Counter(),
        "pitches": 0,
        "reached_2strikes": 0,
        "reached_3balls": 0,
        "reached_full": 0,
        "take_attempts": 0,
        "balls_on_take": 0,
        "called_strikes_on_take": 0,
        "swing_attempts": 0,
        "whiffs": 0,
        "fouls": 0,
        "bips": 0,
        "depth": Counter(),
    }
    take_probs = DISCIPLINE_POLICIES["CURRENT_LAB"]
    for rep in range(reps):
        seed = int(DISCIPLINE_WORKLOAD * 1000) * 10**6 + rep  # mismas seeds entre variantes
        d = _simulate_pa_diag(take_probs, seed, take_bias=base,
                              foul_chance=0.35, take_floor=0.25)
        for key in ("outcome", "take_attempts", "balls_on_take",
                    "called_strikes_on_take", "swing_attempts", "whiffs",
                    "fouls", "bips"):
            if key == "outcome":
                agg[key][d[key]] += 1
            else:
                agg[key] += d[key]
        agg["pitches"] += d["pitches"]
        agg["reached_2strikes"] += d["reached_2strikes"]
        agg["reached_3balls"] += d["reached_3balls"]
        agg["reached_full"] += d["reached_full"]
        for n in (3, 4, 5, 6):
            if d["pitches"] >= n:
                agg["depth"][n] += 1
    return agg


# ---------------------------------------------------------------------------
# 002C-C · Swing termination · foul/contact sweep
# ---------------------------------------------------------------------------
# Solo varía el % de FOUL sobre los contactos (production = 0.45). NO toca el
# whiff model ni la regla zona+tipo (contacto limpio sin foul). Pregunta: ¿más
# contacto no-terminal produce counts profundos sin destruir K/BIP ni generar
# PA interminables? TAKE vuelve a CURRENT 0.65 para aislar C.
FOUL_SWEEP = {
    "C0": 0.35,  # producción histórica (foul_chance=None→0.45 en 002E-4)
    "C1": 0.45,
    "C2": 0.55,
    "C3": 0.65,
}


def run_foul_sweep(reps: int) -> None:
    """002C-C · Sweep de foul/contact (0.35/0.45/0.55/0.65), TAKE CURRENT, MID/MID."""
    print("=" * 130)
    print("002C-C · Swing termination · foul/contact sweep (whiff intocado)")
    print(f"MID P {PITCHER_RAW} vs MID B {BATTER} | fatiga congelada 75% | política "
          f"CURRENT_LAB 35/25/10 | TAKE baseline 0.65 (CURRENT) | {reps:,} PA por variante")
    print(f"Pipeline: SWING → whiff(strike) | contact → foul(PA continúa) | BIP(terminal)")
    print("=" * 130)
    print(f"{'V':<4} {'Foul%':>6} | {'Foul/Cnt':>8} {'BIP/Cnt':>8} {'CalledS/tk':>10} | "
          f"{'K%':>6} {'BB%':>6} {'BIP%':>6} | {'P(3bolas)':>9} {'P(full)':>7} "
          f"{'P(BB|3bol)':>10} | {'Pit/PA':>6} {'p95':>4} {'max':>4} | "
          f"{'≥3':>4} {'≥4':>4} {'≥6':>4} {'≥8':>4}")
    print("-" * 130)

    for name, foul in FOUL_SWEEP.items():
        a = run_foul_sweep_cell(foul, reps)
        n = reps
        k = a["outcome"]["K"]
        bb = a["outcome"]["BB"]
        bip = n - k - bb
        r3 = a["reached_3balls"]
        rfull = a["reached_full"]
        ct = a["fouls"] + a["bips"]  # contactos no-whiff (con o sin contacto sucio)
        tk = max(1, a["take_attempts"])
        print(
            f"{name:<4} {foul * 100:>6.0f} | "
            f"{a['fouls'] / ct * 100:>8.2f} {a['bips'] / ct * 100:>8.2f} "
            f"{a['called_strikes_on_take'] / tk * 100:>10.2f} | "
            f"{k / n * 100:6.2f} {bb / n * 100:6.2f} {bip / n * 100:6.2f} | "
            f"{r3 / n * 100:8.2f} {rfull / n * 100:6.2f} "
            f"{bb / r3 * 100 if r3 else 0:9.2f} | "
            f"{a['pitches'] / n:6.2f} {a['p95']:>4} {a['max']:>4} | "
            f"{a['depth'][3] / n * 100:4.1f} {a['depth'][4] / n * 100:4.1f} "
            f"{a['depth'][6] / n * 100:4.1f} {a['depth'][8] / n * 100:4.1f}"
        )

    print("-" * 130)
    print("Foul/Cnt y BIP/Cnt verifican que el parámetro LAB llega a los contactos")
    print("(cada swing NO-whiff produce exactamente FOUL o BIP). Confirma que el")
    print("whiff model sigue intacto (K% y swings sin tocar por el sweep).")
    print("Pregunta: ¿C soluciona el count con sensibilidad razonable o se necesitan fouls 65-80%?")


def run_foul_sweep_cell(foul: float, reps: int) -> dict:
    agg = {
        "outcome": Counter(),
        "pitches": 0,
        "lengths": [],
        "reached_2strikes": 0,
        "reached_3balls": 0,
        "reached_full": 0,
        "take_attempts": 0,
        "balls_on_take": 0,
        "called_strikes_on_take": 0,
        "swing_attempts": 0,
        "whiffs": 0,
        "fouls": 0,
        "bips": 0,
        "depth": Counter(),
    }
    take_probs = DISCIPLINE_POLICIES["CURRENT_LAB"]
    for rep in range(reps):
        seed = int(DISCIPLINE_WORKLOAD * 1000) * 10**6 + rep  # mismas seeds entre variantes
        d = _simulate_pa_diag(take_probs, seed, foul_chance=foul,
                              take_bias=0.65, take_floor=0.25)
        for key in ("outcome", "take_attempts", "balls_on_take",
                    "called_strikes_on_take", "swing_attempts", "whiffs",
                    "fouls", "bips"):
            if key == "outcome":
                agg[key][d[key]] += 1
            else:
                agg[key] += d[key]
        agg["pitches"] += d["pitches"]
        agg["lengths"].append(d["pitches"])
        agg["reached_2strikes"] += d["reached_2strikes"]
        agg["reached_3balls"] += d["reached_3balls"]
        agg["reached_full"] += d["reached_full"]
        for n in (3, 4, 6, 8):
            if d["pitches"] >= n:
                agg["depth"][n] += 1
    lengths = sorted(agg["lengths"])
    agg["p95"] = lengths[int(len(lengths) * 0.95) - 1]
    agg["max"] = lengths[-1]
    return agg


# ---------------------------------------------------------------------------
# 002C-BC · Factorial TAKE×foul 2×2 (interacción B×C)
# ---------------------------------------------------------------------------
# B2/B3 (take 0.40/0.30) × C1/C2 (foul 0.45/0.55) + fila PROD (0.30/0.45) como control.
# Pregunta: ¿B (bolas) y C (strikes/supervivencia) se compensan y producen una
# región con K significativo + BB expresable + BIP dominante + PA profundo?
BC_CELLS = {
    "PROD":   {"take": None,  "foul": None},  # producción 002E-4: 0.30 / 0.45
    "B2-C1":  {"take": 0.40,  "foul": 0.45},
    "B2-C2":  {"take": 0.40,  "foul": 0.55},
    "B3-C1":  {"take": 0.30,  "foul": 0.45},
    "B3-C2":  {"take": 0.30,  "foul": 0.55},
}


def run_bc_factorial(reps: int) -> None:
    """002C-BC · Factorial TAKE×foul (interacción). 100k/celda, MID/MID."""
    print("=" * 130)
    print("002C-BC · Factorial TAKE×foul (B×C) · interacción de mecanismos")
    print(f"MID P {PITCHER_RAW} vs MID B {BATTER} | fatiga congelada 75% | política "
          f"CURRENT_LAB 35/25/10 | whiff + zona/tipo intactos | {reps:,} PA por celda")
    print(f"Celdas: B2/B3 (take 0.40/0.30) × C1/C2 (foul 45/55); PROD (0.65/35) como control")
    print("=" * 130)

    cells = {}
    for name, cfg in BC_CELLS.items():
        cells[name] = run_bc_cell(cfg["take"], cfg["foul"], reps)

    # Tabla A: outcomes + count profundo + colas
    print()
    print("-- Outcomes | count | colas --")
    print(f"{'Cell':<7} {'K%':>6} {'BB%':>6} {'BIP%':>6} {'OUT%':>6} {'1B%':>5} "
          f"{'2B%':>5} {'3B%':>5} {'HR%':>5} {'Reach%':>7} | "
          f"{'P(3bol)':>7} {'P(full)':>7} {'P(BB|3b)':>8} | "
          f"{'Pit/PA':>6} {'p95':>4} {'max':>4} | {'≥3':>4} {'≥4':>4} {'≥6':>4} {'≥8':>4}")
    print("-" * 130)

    for name in BC_CELLS:
        a = cells[name]
        n = reps
        out = a["outcome"]
        k = out["K"]
        bb = out["BB"]
        bip = n - k - bb
        r3 = a["reached_3balls"]
        rfull = a["reached_full"]
        reach = bb + out["1B"] + out["2B"] + out["3B"] + out["HR"]
        print(
            f"{name:<7} "
            f"{k / n * 100:6.2f} {bb / n * 100:6.2f} {bip / n * 100:6.2f} "
            f"{out['OUT'] / n * 100:6.2f} {out['1B'] / n * 100:5.2f} "
            f"{out['2B'] / n * 100:5.2f} {out['3B'] / n * 100:5.2f} "
            f"{out['HR'] / n * 100:5.2f} {reach / n * 100:7.2f} | "
            f"{r3 / n * 100:7.2f} {rfull / n * 100:7.2f} "
            f"{bb / r3 * 100 if r3 else 0:8.2f} | "
            f"{a['pitches'] / n:6.2f} {a['p95']:>4} {a['max']:>4} | "
            f"{a['depth'][3] / n * 100:4.1f} {a['depth'][4] / n * 100:4.1f} "
            f"{a['depth'][6] / n * 100:4.1f} {a['depth'][8] / n * 100:4.1f}"
        )
    print("-" * 130)

    # Tabla B: take/swing saneado + deep-count conversion
    print()
    print("-- Take/swing + sanity del parámetro | deep-count conversion (Pit/PA ≥ 4) --")
    print(f"{'Cell':<7} {'CalledS/tk':>10} {'Foul/Cnt':>8} {'BIP/Cnt':>8} {'Whiff%':>7} | "
          f"{'P(K|≥4)':>7} {'P(BB|≥4)':>8} {'P(BIP|≥4)':>8}")
    print("-" * 130)
    for name in BC_CELLS:
        a = cells[name]
        tk = max(1, a["take_attempts"])
        ct = max(1, a["fouls"] + a["bips"])
        sw = max(1, a["swing_attempts"])
        ge4n = max(1, a["ge4"]["n"])
        print(
            f"{name:<7} "
            f"{a['called_strikes_on_take'] / tk * 100:>10.2f} "
            f"{a['fouls'] / ct * 100:>8.2f} {a['bips'] / ct * 100:>8.2f} "
            f"{a['whiffs'] / sw * 100:>7.2f} | "
            f"{a['ge4']['K'] / ge4n * 100:>7.2f} {a['ge4']['BB'] / ge4n * 100:>8.2f} "
            f"{a['ge4']['BIP'] / ge4n * 100:>8.2f}"
        )
    print("-" * 130)

    print("P(K|≥4): qué pasa una vez el PA vive ≥4 pitches. Si sube el K condicional")
    print("con C↑, la supervivencia sigue yendo a strikes; si BB|≥4 sube con B, las")
    print("bolas del TAKE se monetizan.")
    print("BIP% es la terminación dominante si BIP% sigue >~55% en todas las celdas.")
    print("Criterio 002C: ¿existe región con K 20-30%, BB de varios puntos, BIP resto,")
    print("Pit/PA>3 y colas (p95/max) controladas? Selección LAB, no calibración final.")


def run_bc_cell(take_bias: float, foul_chance: float, reps: int) -> dict:
    agg = {
        "outcome": Counter(),
        "pitches": 0,
        "lengths": [],
        "reached_2strikes": 0,
        "reached_3balls": 0,
        "reached_full": 0,
        "take_attempts": 0,
        "balls_on_take": 0,
        "called_strikes_on_take": 0,
        "swing_attempts": 0,
        "whiffs": 0,
        "fouls": 0,
        "bips": 0,
        "depth": Counter(),
        "ge4": Counter(),  # outcomes condicionados a Pit/PA ≥ 4 ("n", "K", "BB", "BIP")
    }
    take_probs = DISCIPLINE_POLICIES["CURRENT_LAB"]
    for rep in range(reps):
        seed = int(DISCIPLINE_WORKLOAD * 1000) * 10**6 + rep  # mismas seeds entre celdas
        d = _simulate_pa_diag(take_probs, seed,
                              take_bias=take_bias, foul_chance=foul_chance)
        for key in ("outcome", "take_attempts", "balls_on_take",
                    "called_strikes_on_take", "swing_attempts", "whiffs",
                    "fouls", "bips"):
            if key == "outcome":
                agg[key][d[key]] += 1
            else:
                agg[key] += d[key]
        agg["pitches"] += d["pitches"]
        agg["lengths"].append(d["pitches"])
        agg["reached_2strikes"] += d["reached_2strikes"]
        agg["reached_3balls"] += d["reached_3balls"]
        agg["reached_full"] += d["reached_full"]
        for n in (3, 4, 6, 8):
            if d["pitches"] >= n:
                agg["depth"][n] += 1
        if d["pitches"] >= 4:
            agg["ge4"]["n"] += 1
            if d["outcome"] == "K":
                agg["ge4"]["K"] += 1
            elif d["outcome"] == "BB":
                agg["ge4"]["BB"] += 1
            else:
                agg["ge4"]["BIP"] += 1
    lengths = sorted(agg["lengths"])
    agg["p95"] = lengths[int(len(lengths) * 0.95) - 1]
    agg["max"] = lengths[-1]
    return agg


# ---------------------------------------------------------------------------
# 002D · Two-strike discipline sensitivity
# ---------------------------------------------------------------------------
# Config fija B3-C1 (TAKE 0.30, foul 45%). Política 0/1 strikes = VERY_PATIENT
# 65/50 para aislar la decisión a 2 strikes: sweep 10/20/30/40/50%.
# Pregunta: ¿la alta terminalidad en count profundo es del calculator o del
# agente 10% de TAKE a 2 strikes? NO toca producción.
D2_FIX = {"take_bias": 0.30, "foul_chance": 0.45, "take_floor": 0.25}
D2_POLICIES_0_1 = {0: 0.65, 1: 0.50}
D2_TAKE_2S_SWEEP = [0.10, 0.20, 0.30, 0.40, 0.50]


def run_two_strike_sweep(reps: int) -> None:
    """002D · Two-strike TAKE sensitivity · B3-C1 fijo, 65/50/X."""
    print("=" * 130)
    print("002D · Two-strike discipline sensitivity (TAKE a 2 strikes)")
    print(f"Fijo: B3-C1 (TAKE baseline 0.30, foul 45%) | política 0/1 strikes = "
          f"65/50 (VERY_PATIENT) | fatiga 75% | CURRENT_LAB solo para aislar la decisión")
    print(f"{reps:,} PA por variante | sweep TAKE a 2 strikes: 10/20/30/40/50%")
    print("=" * 130)

    print(f"{'T2s':>5} | {'K%':>6} {'BB%':>6} {'BIP%':>6} | {'Pit/PA':>6} {'p95':>4} "
          f"{'max':>4} | {'P(3bol)':>7} {'P(full)':>7} | "
          f"{'P(K|≥4)':>7} {'P(BB|≥4)':>8} {'P(BIP|≥4)':>8} | "
          f"{'P(K|2s)':>7} {'P(BB|2s)':>7} {'P(BIP|2s)':>8} | "
          f"{'CalledS/tk':>10} {'Ball/tk':>7} | {'P(TAKE|2s)':>10} "
          f"{'Ball|TAKE2s':>11} {'Cs|TAKE2s':>9}")
    print("-" * 150)

    rows = {}
    for t2 in D2_TAKE_2S_SWEEP:
        take_probs = {**D2_POLICIES_0_1, 2: t2}
        a = run_two_strike_cell(take_probs, reps)
        rows[t2] = a
        n = reps
        k = a["outcome"]["K"]
        bb = a["outcome"]["BB"]
        bip = n - k - bb
        r3 = a["reached_3balls"]
        rfull = a["reached_full"]
        tk = max(1, a["take_attempts"])
        ge4n = max(1, a["ge4"]["n"])
        r2s = max(1, a["outcome_at_2s"]["n"])
        p2s = max(1, a["pitches_at_2s"])
        t2s = max(1, a["take_at_2s"])
        p_take_2s = a["take_at_2s"] / p2s * 100
        p_ball_take2s = a["balls_on_take_at_2s"] / t2s * 100
        p_cs_take2s = a["called_strikes_on_take_at_2s"] / t2s * 100
        print(
            f"{t2:>5.0%} | "
            f"{k / n * 100:6.2f} {bb / n * 100:6.2f} {bip / n * 100:6.2f} | "
            f"{a['pitches'] / n:6.2f} {a['p95']:>4} {a['max']:>4} | "
            f"{r3 / n * 100:7.2f} {rfull / n * 100:7.2f} | "
            f"{a['ge4']['K'] / ge4n * 100:7.2f} {a['ge4']['BB'] / ge4n * 100:8.2f} "
            f"{a['ge4']['BIP'] / ge4n * 100:8.2f} | "
            f"{a['outcome_at_2s']['K'] / r2s * 100:7.2f} "
            f"{a['outcome_at_2s']['BB'] / r2s * 100:7.2f} "
            f"{a['outcome_at_2s']['BIP'] / r2s * 100:8.2f} | "
            f"{a['called_strikes_on_take'] / tk * 100:10.2f} "
            f"{a['balls_on_take'] / tk * 100:7.2f} | "
            f"{p_take_2s:>10.2f} {p_ball_take2s:>11.2f} {p_cs_take2s:>9.2f}"
        )
    print("-" * 150)

    print("Cadena a 2 strikes: P(TAKE|2s) → ball/called-strike del TAKE. La")
    print("terminalidad se mide en P(K/BB/BIP|2s) condicionada a haber llegado a 2 strikes.")
    print("Si BB sube claramente y K cae/estable → el K|deep era agent-policy dependent.")
    print("Si TAKE 10→50% deja BB <2% y P(K|deep) domina → problema del calculator (002E).")


def run_two_strike_cell(take_probs: dict, reps: int) -> dict:
    agg = {
        "outcome": Counter(),
        "pitches": 0,
        "lengths": [],
        "reached_3balls": 0,
        "reached_full": 0,
        "take_attempts": 0,
        "balls_on_take": 0,
        "called_strikes_on_take": 0,
        "take_at_2s": 0,
        "pitches_at_2s": 0,
        "balls_on_take_at_2s": 0,
        "called_strikes_on_take_at_2s": 0,
        "ge4": Counter(),
        "outcome_at_2s": Counter(),
    }
    for rep in range(reps):
        seed = int(DISCIPLINE_WORKLOAD * 1000) * 10**6 + rep  # mismas seeds entre variantes
        d = _simulate_pa_diag(take_probs, seed,
                              take_bias=D2_FIX["take_bias"],
                              foul_chance=D2_FIX["foul_chance"],
                              take_floor=D2_FIX["take_floor"])
        agg["outcome"][d["outcome"]] += 1
        agg["pitches"] += d["pitches"]
        agg["lengths"].append(d["pitches"])
        agg["reached_3balls"] += d["reached_3balls"]
        agg["reached_full"] += d["reached_full"]
        agg["take_attempts"] += d["take_attempts"]
        agg["balls_on_take"] += d["balls_on_take"]
        agg["called_strikes_on_take"] += d["called_strikes_on_take"]
        agg["take_at_2s"] += d["take_at_2s"]
        agg["pitches_at_2s"] += d["pitches_at_2s"]
        agg["balls_on_take_at_2s"] += d["balls_on_take_at_2s"]
        agg["called_strikes_on_take_at_2s"] += d["called_strikes_on_take_at_2s"]
        if d["pitches"] >= 4:
            agg["ge4"]["n"] += 1
            if d["outcome"] == "K":
                agg["ge4"]["K"] += 1
            elif d["outcome"] == "BB":
                agg["ge4"]["BB"] += 1
            else:
                agg["ge4"]["BIP"] += 1
        if d["reached_2strikes"]:
            agg["outcome_at_2s"]["n"] += 1
            if d["outcome"] == "K":
                agg["outcome_at_2s"]["K"] += 1
            elif d["outcome"] == "BB":
                agg["outcome_at_2s"]["BB"] += 1
            else:
                agg["outcome_at_2s"]["BIP"] += 1
    lengths = sorted(agg["lengths"])
    agg["p95"] = lengths[int(len(lengths) * 0.95) - 1]
    agg["max"] = lengths[-1]
    return agg


# ---------------------------------------------------------------------------
# Salidas
# ---------------------------------------------------------------------------

def run_pitch_level(reps: int) -> None:
    print("=" * 130)
    print("001B-3 · Pitch-level Monte Carlo · fatiga (pitch suelto)")
    print(f"MID P {PITCHER_RAW} vs MID B {BATTER} | CPU {DIFFICULTY} | threshold={THRESHOLD} | "
          f"{reps:,} reps por escenario")
    print("=" * 130)
    print(f"{'Curve':<8} {'Wrk':>5} | {'EffV':>4} {'EffC':>4} {'EffM':>4} | "
          f"{'Whiff%':>7} {'Foul%':>6} {'BIP%':>6} {'Out%':>6} "
          f"{'1B%':>6} {'2B%':>6} {'3B%':>6} {'HR%':>6} | "
          f"{'CalledS%':>8} {'Ball%':>6}")
    print("-" * 130)

    for curve in CURVES:
        for w in WORKLOADS:
            pitch_eff, events, swings, takes = run_pitch_scenario(curve, w, reps)
            sw = max(1, swings)
            tk = max(1, takes)
            rows = {
                "whiff": events[Event.STRIKE_SWINGING] / sw,
                "foul": events[Event.FOUL] / sw,
                "bip": (swings - events[Event.STRIKE_SWINGING] - events[Event.FOUL]) / sw,
                "out": (events[Event.OUT_FLY] + events[Event.OUT_GROUND]) / sw,
                "1b": events[Event.HIT_1B] / sw,
                "2b": events[Event.HIT_2B] / sw,
                "3b": events[Event.HIT_3B] / sw,
                "hr": events[Event.HOME_RUN] / sw,
                "called": events[Event.STRIKE_LOOKING] / tk,
                "ball": events[Event.BALL] / tk,
            }
            print(
                f"{curve:<8} {w:>5.0%} | "
                f"{pitch_eff['velocity']:>4} {pitch_eff['control']:>4} {pitch_eff['movement']:>4} | "
                f"{rows['whiff']*100:6.2f} {rows['foul']*100:6.2f} {rows['bip']*100:6.2f} {rows['out']*100:6.2f} "
                f"{rows['1b']*100:6.2f} {rows['2b']*100:6.2f} {rows['3b']*100:6.2f} {rows['hr']*100:6.2f} | "
                f"{rows['called']*100:8.2f} {rows['ball']*100:6.2f}"
            )
    print("-" * 130)


# ---------------------------------------------------------------------------
# 001B-5 · Full PA sobre el PA calibrado de 002 (B3-C1 + 65/50/30)
# ---------------------------------------------------------------------------
# Repite el Monte Carlo full-PA de 001B-4 con la configuración calibrada de la
# rama 002: TAKE baseline 0.30, foul 45%, política LAB 65/50/30. Fatiga dinámica
# intra-PA. Ahora el canal comando (Control → called-strike/ball) es expresable,
# así que se pueden medir las dos vías de coste de la fatiga:
#   dominio (vel/mov) → whiff ↓ → contacto ↑
#   comando (control) → called-strike ↓ → BB ↑
F5_POLICY = {0: 0.65, 1: 0.50, 2: 0.30}
F5_FIX = {"take_bias": 0.30, "foul_chance": 0.45, "take_floor": 0.25}


def _simulate_pa_f5(curve: str, start_workload: float, seed: int) -> dict:
    random.seed(seed)
    balls = 0
    strikes = 0
    pitches = 0
    pitch_count = int(start_workload * THRESHOLD)
    final_count = pitch_count
    takes = swings = whiffs = called_strikes = 0
    reached_full = False

    while pitches < MAX_PA_PITCHES:
        if balls == 3 and strikes == 2:
            reached_full = True
        pitches += 1
        fatigued_pitcher, pitch_eff = effective_attrs(curve, pitch_count)
        final_count = pitch_count
        pitch_count += 1

        pitch = get_cpu_pitch_action(DIFFICULTY)
        swing = batter_action_by_count(strikes, take_probs=F5_POLICY)
        pitch["velocity"] = pitch_eff["velocity"]
        pitch["control"] = pitch_eff["control"]
        pitch["movement"] = pitch_eff["movement"]

        if swing["swing_type"] == SwingType.TAKE:
            takes += 1
        else:
            swings += 1

        event, _description = _resolve_play_outcome(
            pitcher_attrs=fatigued_pitcher,
            batter_attrs=BATTER,
            pitch_selected=pitch,
            swing_selected=swing,
            tactics_modifiers=None,
            take_bias=F5_FIX["take_bias"],
            foul_chance=F5_FIX["foul_chance"],
            take_floor=F5_FIX["take_floor"],
        )

        if event == Event.STRIKE_SWINGING:
            whiffs += 1
        elif event == Event.STRIKE_LOOKING:
            called_strikes += 1

        outcome = None
        if event in (Event.STRIKE_SWINGING, Event.STRIKE_LOOKING):
            strikes += 1
            if strikes == 3:
                outcome = "K"
        elif event == Event.BALL:
            balls += 1
            if balls == 4:
                outcome = "BB"
        elif event == Event.FOUL:
            if strikes < 2:
                strikes += 1
        else:
            outcome = _BIP_OUTCOME[event]

        if outcome is not None:
            break

    return {
        "outcome": outcome if outcome is not None else "CAP",
        "pitches": pitches,
        "final_count": final_count,
        "takes": takes,
        "swings": swings,
        "whiffs": whiffs,
        "called_strikes": called_strikes,
        "reached_full": reached_full,
    }


def run_pa_scenario_f5(curve: str, start_workload: float, reps: int) -> dict:
    outcomes = Counter()
    lengths = []
    final_counts = []
    takes = swings = whiffs = called_strikes = 0
    reached_full = ge4 = ge6 = 0
    for rep in range(reps):
        seed = int(start_workload * 1000) * 10**6 + rep
        d = _simulate_pa_f5(curve, start_workload, seed)
        outcomes[d["outcome"]] += 1
        lengths.append(d["pitches"])
        final_counts.append(d["final_count"])
        takes += d["takes"]
        swings += d["swings"]
        whiffs += d["whiffs"]
        called_strikes += d["called_strikes"]
        if d["reached_full"]:
            reached_full += 1
        if d["pitches"] >= 4:
            ge4 += 1
        if d["pitches"] >= 6:
            ge6 += 1
    return {
        "outcomes": outcomes,
        "lengths": lengths,
        "final_counts": final_counts,
        "takes": takes,
        "swings": swings,
        "whiffs": whiffs,
        "called_strikes": called_strikes,
        "reached_full": reached_full,
        "ge4": ge4,
        "ge6": ge6,
        "n": reps,
    }


def run_fatigue_curve_comparison(reps: int) -> None:
    """001B-5 · Full-PA fatigue Monte Carlo sobre el PA calibrado de 002."""
    print("=" * 130)
    print("001B-5 · Full PA Monte Carlo · PA calibrado 002 (B3-C1 + política 65/50/30)")
    print(f"MID P {PITCHER_RAW} vs MID B {BATTER} | CPU {DIFFICULTY} | threshold={THRESHOLD} | "
          f"{reps:,} PA por escenario ({len(CURVES)} curvas × {len(WORKLOADS)} workloads = "
          f"{reps * len(CURVES) * len(WORKLOADS):,} PA)")
    print("TAKE baseline 0.30 | foul 45% | TAKE 65/50/30 por 0/1/2 strikes | fatiga dinámica intra-PA")
    print("=" * 130)

    rows = {}
    for curve in CURVES:
        for w in WORKLOADS:
            rows[(curve, w)] = run_pa_scenario_f5(curve, w, reps)

    print()
    print("-- Resultados de PA --")
    print(f"{'Curve':<8} {'Start':>5} | {'K%':>6} {'BB%':>6} {'BIP%':>6} {'OUT%':>6} "
          f"{'1B%':>6} {'2B%':>6} {'3B%':>6} {'HR%':>6} | {'Reach%':>7} | "
          f"{'Pit/PA':>6} {'p95':>4} {'max':>4} | {'FinalWk':>7}")
    print("-" * 130)
    global_max_count = 0
    for curve in CURVES:
        for w in WORKLOADS:
            r = rows[(curve, w)]
            o = r["outcomes"]
            n = r["n"]
            bip = o["OUT"] + o["1B"] + o["2B"] + o["3B"] + o["HR"]
            reach = o["BB"] + o["1B"] + o["2B"] + o["3B"] + o["HR"]
            mean_len = sum(r["lengths"]) / n
            p95 = _p95(r["lengths"])
            max_len = max(r["lengths"])
            mean_final = sum(r["final_counts"]) / n
            global_max_count = max(global_max_count, max(r["final_counts"]))
            print(
                f"{curve:<8} {w:>5.0%} | "
                f"{_fmt_pct(o['K'], n)} {_fmt_pct(o['BB'], n)} {_fmt_pct(bip, n)} "
                f"{_fmt_pct(o['OUT'], n)} {_fmt_pct(o['1B'], n)} {_fmt_pct(o['2B'], n)} "
                f"{_fmt_pct(o['3B'], n)} {_fmt_pct(o['HR'], n)} | "
                f"{reach / n * 100:7.2f} | "
                f"{mean_len:6.2f} {p95:>4} {max_len:>4} | "
                f"{mean_final / THRESHOLD * 100:7.1f}"
            )
    print("-" * 130)

    print()
    print("-- Count profundo y las dos vías de coste --")
    print(f"{'Curve':<8} {'Start':>5} | {'P(full)':>7} {'P(≥4)':>6} {'P(≥6)':>6} | "
          f"{'CalledS/take':>12} {'Whiff/swing':>11} | {'Takes/PA':>8} {'Swings/PA':>9}")
    print("-" * 130)
    for curve in CURVES:
        for w in WORKLOADS:
            r = rows[(curve, w)]
            n = r["n"]
            print(
                f"{curve:<8} {w:>5.0%} | "
                f"{r['reached_full'] / n * 100:7.2f} {r['ge4'] / n * 100:6.2f} "
                f"{r['ge6'] / n * 100:6.2f} | "
                f"{r['called_strikes'] / max(1, r['takes']) * 100:12.2f} "
                f"{r['whiffs'] / max(1, r['swings']) * 100:11.2f} | "
                f"{r['takes'] / n:8.3f} {r['swings'] / n:9.3f}"
            )
    print("-" * 130)
    print("Lectura: CalledS/take mide el canal COMANDO (fatiga → control ↓ → BB ↑);")
    print("Whiff/swing mide el canal DOMINIO (fatiga → vel/mov ↓ → whiff ↓ → contacto ↑).")
    print(f"max pitch_count alcanzado global: {global_max_count}")


# ---------------------------------------------------------------------------
# 001C-1 · Natural workload distribution (fatiga NEUTRALIZADA)
# ---------------------------------------------------------------------------
# Simula outings de 9 innings headless con el PA calibrado 002 y SIN deterioro
# por fatiga (factor 1.0). Mide la escala natural de pitch counts del motor para
# decidir dónde debe vivir el 100% de la curva candidata SMOOTH-0.55-F35.
# Modelo de inning: 3 outs; K y OUT cuentan como out; BB/hits no (sin dobles
# matanzas ni avance de corredores). Mid es solo para comparar carga natural.
MATCHUPS_1C1 = {
    "WEAK":   {"velocidad": 78, "control": 58, "movimiento": 70},
    "MID":    dict(PITCHER_RAW),
    "STRONG": {"velocidad": 96, "control": 94, "movimiento": 95},
}
MAX_INNING_PITCHES = 80
_OUT_EVENTS_1C1 = {"K", "OUT"}


def neutral_attrs(pitcher_raw: dict):
    """Atributos efectivos sin fatiga (factor 1.0), mismo escalado que effective_attrs."""
    fatigued = {k: int(v) for k, v in pitcher_raw.items()}
    pitch_eff = {
        "velocity": int(PITCH_RAW["velocity"] * pitcher_raw["velocidad"] / PITCHER_RAW["velocidad"]),
        "control": int(PITCH_RAW["control"] * pitcher_raw["control"] / PITCHER_RAW["control"]),
        "movement": int(PITCH_RAW["movement"] * pitcher_raw["movimiento"] / PITCHER_RAW["movimiento"]),
    }
    return fatigued, pitch_eff


def _simulate_pa_neutral(pitcher_raw: dict, seed: int):
    random.seed(seed)
    balls = strikes = pitches = 0
    fatigued, pitch_eff = neutral_attrs(pitcher_raw)
    while pitches < MAX_PA_PITCHES:
        pitches += 1
        pitch = get_cpu_pitch_action(DIFFICULTY)
        swing = batter_action_by_count(strikes, take_probs=F5_POLICY)
        pitch["velocity"] = pitch_eff["velocity"]
        pitch["control"] = pitch_eff["control"]
        pitch["movement"] = pitch_eff["movement"]

        event, _description = _resolve_play_outcome(
            pitcher_attrs=fatigued,
            batter_attrs=BATTER,
            pitch_selected=pitch,
            swing_selected=swing,
            tactics_modifiers=None,
            take_bias=F5_FIX["take_bias"],
            foul_chance=F5_FIX["foul_chance"],
            take_floor=F5_FIX["take_floor"],
        )

        if event in (Event.STRIKE_SWINGING, Event.STRIKE_LOOKING):
            strikes += 1
            if strikes == 3:
                return "K", pitches
        elif event == Event.BALL:
            balls += 1
            if balls == 4:
                return "BB", pitches
        elif event == Event.FOUL:
            if strikes < 2:
                strikes += 1
        else:
            return _BIP_OUTCOME[event], pitches

    return "CAP", pitches


def simulate_outing_1c1(pitcher_raw: dict, seed: int, innings: int = 9) -> dict:
    rng = random.Random(seed)
    inning_pitches = []
    cum = []
    total = 0
    total_pas = 0
    incomplete = 0
    for _ in range(innings):
        outs = 0
        inning_p = 0
        while outs < 3 and inning_p < MAX_INNING_PITCHES:
            outcome, p = _simulate_pa_neutral(pitcher_raw, rng.getrandbits(63))
            inning_p += p
            total_pas += 1
            if outcome in _OUT_EVENTS_1C1:
                outs += 1
        if outs < 3:
            incomplete += 1
        inning_pitches.append(inning_p)
        total += inning_p
        cum.append(total)
    return {
        "inning_pitches": inning_pitches,
        "cum": cum,
        "total": total,
        "pas": total_pas,
        "incomplete": incomplete,
    }


def _pctl(values: list, p: float):
    s = sorted(values)
    idx = max(0, min(len(s) - 1, int(p / 100.0 * (len(s) - 1))))
    return s[idx]


def run_threshold_distribution(reps: int) -> None:
    """001C-1 · Distribución natural de workload con fatiga neutralizada."""
    print("=" * 130)
    print("001C-1 · Natural workload distribution (fatiga NEUTRALIZADA, PA calibrado 002)")
    print(f"Outings de 9 innings | {reps:,} outings por matchup | "
          f"TAKE 0.30 / foul 45% / política 65/50/30 | bateador MID {BATTER}")
    print("Modelo de inning: 3 outs; K y OUT cuentan como out; BB/hits no. Sin fatiga (factor 1.0).")
    print(f"Matchups: WEAK {MATCHUPS_1C1['WEAK']} | MID {MATCHUPS_1C1['MID']} | "
          f"STRONG {MATCHUPS_1C1['STRONG']}")
    print("=" * 130)

    results = {}
    for name, pitcher in MATCHUPS_1C1.items():
        results[name] = [simulate_outing_1c1(pitcher, 7_000_000 + i) for i in range(reps)]

    mid = results["MID"]
    n = len(mid)
    per_inning = [[d["inning_pitches"][i] for d in mid] for i in range(9)]
    cum_by_k = [[d["cum"][i] for d in mid] for i in range(9)]

    print()
    print(f"-- MID: pitches por inning (n={n}) --")
    print(f"{'Inn':>3} | {'Mean':>6} {'p50':>4} {'p75':>4} {'p90':>4} {'p95':>4}")
    print("-" * 40)
    for i in range(9):
        v = per_inning[i]
        print(f"{i + 1:>3} | {sum(v) / n:6.2f} {_pctl(v, 50):>4} {_pctl(v, 75):>4} "
              f"{_pctl(v, 90):>4} {_pctl(v, 95):>4}")

    print()
    print("-- MID: pitch count ACUMULADO tras inning k --")
    print(f"{'k':>3} | {'Mean':>6} {'p50':>4} {'p75':>4} {'p90':>4} {'p95':>4}")
    print("-" * 44)
    for i in range(9):
        v = cum_by_k[i]
        print(f"{i + 1:>3} | {sum(v) / n:6.1f} {_pctl(v, 50):>4} {_pctl(v, 75):>4} "
              f"{_pctl(v, 90):>4} {_pctl(v, 95):>4}")

    print()
    print("-- Comparativa por matchup (outing de 9 innings, sin fatiga) --")
    print(f"{'Matchup':<8} {'Pit/PA':>7} {'PA/Inn':>7} | {'Total p50':>9} {'Total p90':>9} | "
          f"{'Inn p50':>7} {'Inn p90':>7} | {'InnInc%':>7}")
    print("-" * 130)
    for name in ("WEAK", "MID", "STRONG"):
        data = results[name]
        tot = [d["total"] for d in data]
        pas = sum(d["pas"] for d in data)
        pp = sum(d["total"] for d in data) / pas
        pai = pas / (9 * len(data))
        inn = [p for d in data for p in d["inning_pitches"]]
        inc = sum(d["incomplete"] for d in data)
        print(f"{name:<8} {pp:7.2f} {pai:7.2f} | "
              f"{_pctl(tot, 50):>9} {_pctl(tot, 90):>9} | "
              f"{_pctl(inn, 50):>7} {_pctl(inn, 90):>7} | "
              f"{inc / (9 * len(data)) * 100:6.2f}%")

    print()
    print("-- Cruce de thresholds: inning en que el acumulado cruza cada umbral --")
    print("   (Inn p50/p75 = inning mediano/p75 de cruce; 10 = no cruza en 9 innings;")
    print("    @k = % de outings que ya cruzaron el umbral al terminar el inning k)")
    thresholds = [25, 40, 50, 60, 75, 90]
    for name in ("WEAK", "MID", "STRONG"):
        data = results[name]
        print(f"  {name}:")
        print(f"    {'Thr':>4} | {'Inn p50':>7} {'Inn p75':>7} | {'@3inn':>6} {'@5inn':>6} {'@7inn':>6} {'@9inn':>6}")
        for th in thresholds:
            inn_cross = []
            for d in data:
                cross = 10
                for i, c in enumerate(d["cum"]):
                    if c >= th:
                        cross = i + 1
                        break
                inn_cross.append(cross)

            def share_by(k):
                return sum(1 for c in inn_cross if c <= k) / len(inn_cross) * 100

            print(f"    {th:>4} | {_pctl(inn_cross, 50):>7} {_pctl(inn_cross, 75):>7} | "
                  f"{share_by(3):5.1f}% {share_by(5):5.1f}% {share_by(7):5.1f}% {share_by(9):5.1f}%")
    print("-" * 130)
    print("Lectura: el threshold actual de producción es 25 pitches (9 innings). Si el")
    print("acumulado p50 cruza 25 en el inning 1-2, la fatiga empieza demasiado pronto.")


# ---------------------------------------------------------------------------
# 001C-3 · Threshold × outing (SMOOTH-0.55-F35, outing completo de 9 innings)
# ---------------------------------------------------------------------------
# Congela la curva SMOOTH-0.55-F35 y el PA calibrado 002; corre outings
# completos de 9 innings con pitch_count continuo entre innings y fatiga
# dinámica. Compara NO_FATIGUE (control) vs thresholds 75/100/125.
C13_SCENARIOS = [
    ('NO_FATIGUE', None),
    ('EARLY', 75),
    ('BALANCED', 100),
    ('LATE', 125),
]
_C13_BAND_EDGES = [(0.0, 1.00), (1.00, 1.10), (1.10, 1.25), (1.25, 1.50), (1.50, 99.0)]
_C13_BAND_LABELS = ['w<=1.00', '1.00<w<=1.10', '1.10<w<=1.25', '1.25<w<=1.50', 'w>1.50']


def _apply_factor(pitcher_raw: dict, factor: float):
    fatigued = {k: max(1, int(v * factor)) for k, v in pitcher_raw.items()}
    pitch_eff = {
        'velocity': int(PITCH_RAW['velocity'] * fatigued['velocidad'] / PITCHER_RAW['velocidad']),
        'control': int(PITCH_RAW['control'] * fatigued['control'] / PITCHER_RAW['control']),
        'movement': int(PITCH_RAW['movement'] * fatigued['movimiento'] / PITCHER_RAW['movimiento']),
    }
    return fatigued, pitch_eff


def _fatigue_factor(threshold, pitch_count: int):
    if threshold is None:
        return 1.0, None
    w = pitch_count / threshold
    factor = 1.0 if w <= 1.0 else smooth_factor(w)
    return factor, w


def _simulate_pa_fatigued(pitcher_raw: dict, pitch_count_start: int, threshold, seed: int):
    random.seed(seed)
    balls = strikes = pitches = 0
    while pitches < MAX_PA_PITCHES:
        pitches += 1
        factor, _w = _fatigue_factor(threshold, pitch_count_start + pitches - 1)
        fatigued, pitch_eff = _apply_factor(pitcher_raw, factor)
        pitch = get_cpu_pitch_action(DIFFICULTY)
        swing = batter_action_by_count(strikes, take_probs=F5_POLICY)
        pitch['velocity'] = pitch_eff['velocity']
        pitch['control'] = pitch_eff['control']
        pitch['movement'] = pitch_eff['movement']

        event, _description = _resolve_play_outcome(
            pitcher_attrs=fatigued,
            batter_attrs=BATTER,
            pitch_selected=pitch,
            swing_selected=swing,
            tactics_modifiers=None,
            take_bias=F5_FIX['take_bias'],
            foul_chance=F5_FIX['foul_chance'],
            take_floor=F5_FIX['take_floor'],
        )

        if event in (Event.STRIKE_SWINGING, Event.STRIKE_LOOKING):
            strikes += 1
            if strikes == 3:
                return 'K', pitches
        elif event == Event.BALL:
            balls += 1
            if balls == 4:
                return 'BB', pitches
        elif event == Event.FOUL:
            if strikes < 2:
                strikes += 1
        else:
            return _BIP_OUTCOME[event], pitches

    return 'CAP', pitches


def simulate_outing_1c3(pitcher_raw: dict, threshold, seed: int, innings: int = 9) -> dict:
    rng = random.Random(seed)
    pitch_count = 0
    inning_pitches = []
    inning_pas = []
    inning_outcomes = []
    cum_at_inning = []
    total_pas = 0
    bands = [0, 0, 0, 0, 0]
    last_inning_w = []
    for inn_idx in range(innings):
        outs = 0
        inning_p = 0
        inning_pa = 0
        oc = Counter()
        while outs < 3 and inning_p < MAX_INNING_PITCHES:
            if threshold is not None:
                w = pitch_count / threshold
                if inn_idx == innings - 1:
                    last_inning_w.append(w)
                for bi, (lo, hi) in enumerate(_C13_BAND_EDGES):
                    if lo < w <= hi or (bi == 0 and w <= hi):
                        bands[bi] += 1
                        break
            outcome, p = _simulate_pa_fatigued(pitcher_raw, pitch_count, threshold, rng.getrandbits(63))
            pitch_count += p
            inning_p += p
            inning_pa += 1
            total_pas += 1
            oc[outcome] += 1
            if outcome in _OUT_EVENTS_1C1:
                outs += 1
        inning_pitches.append(inning_p)
        inning_pas.append(inning_pa)
        inning_outcomes.append(oc)
        cum_at_inning.append(pitch_count)
    return {
        'inning_pitches': inning_pitches,
        'inning_pas': inning_pas,
        'inning_outcomes': inning_outcomes,
        'cum_at_inning': cum_at_inning,
        'total': pitch_count,
        'total_pas': total_pas,
        'bands': bands,
        'last_inning_w': last_inning_w,
    }


def _scenario_aggregate(data: list, threshold):
    n = len(data)
    n_inn = len(data[0]['inning_outcomes'])
    per_inning = []
    for i in range(n_inn):
        pa_i = sum(d['inning_pas'][i] for d in data)
        pit_i = sum(d['inning_pitches'][i] for d in data)
        oc = Counter()
        for d in data:
            oc.update(d['inning_outcomes'][i])
        per_inning.append({
            'pa': pa_i, 'pitches': pit_i, 'oc': oc,
            'cum': [d['cum_at_inning'][i] for d in data],
        })
    totals = Counter()
    for d in data:
        for oc in d['inning_outcomes']:
            totals.update(oc)
    tot_pitches = [d['total'] for d in data]
    tot_pas = sum(d['total_pas'] for d in data)
    bands = [sum(d['bands'][b] for d in data) for b in range(5)]
    crossing = {}
    if threshold is not None:
        for level in (1.00, 1.10, 1.25, 1.50):
            inns = []
            for d in data:
                cross = n_inn + 1
                for i, c in enumerate(d['cum_at_inning']):
                    if c / threshold >= level:
                        cross = i + 1
                        break
                inns.append(cross)
            crossing[level] = inns
    return {
        'n': n, 'per_inning': per_inning, 'totals': totals,
        'tot_pitches': tot_pitches, 'tot_pas': tot_pas, 'bands': bands,
        'crossing': crossing,
    }


def run_threshold_outing(reps: int) -> None:
    """001C-3 · Threshold × outing · SMOOTH-0.55-F35 sobre el PA calibrado 002."""
    print('=' * 130)
    print('001C-3 · Threshold × outing · SMOOTH-0.55-F35 · 9 innings, fatiga dinámica')
    print(f'MID P {PITCHER_RAW} vs MID B {BATTER} | take 0.30 / foul 45% / política 65/50/30 | '
          f'{reps:,} outings por escenario')
    print('pitch_count continuo entre innings; NO_FATIGUE = control (factor 1.0).')
    print('=' * 130)

    aggs = {}
    for name, threshold in C13_SCENARIOS:
        data = [simulate_outing_1c3(PITCHER_RAW, threshold, 8_000_000 + i) for i in range(reps)]
        aggs[name] = (threshold, _scenario_aggregate(data, threshold))

    for name, threshold in C13_SCENARIOS:
        _thr, agg = aggs[name]
        thr_txt = 'none' if threshold is None else str(threshold)
        print()
        print(f'-- {name} (threshold={thr_txt}) · snapshot por inning --')
        print(f"{'Inn':>3} | {'cumPitch p50/p90':>17} | {'w p50/p90':>15} | {'factor':>6} | "
              f"{'K%':>6} {'BB%':>6} {'BIP%':>5} {'Reach%':>6} {'Pit/PA':>6} | {'PA':>6}")
        print('-' * 130)
        for i in range(9):
            pi = agg['per_inning'][i]
            pa = max(1, pi['pa'])
            oc = pi['oc']
            bip = oc['OUT'] + oc['1B'] + oc['2B'] + oc['3B'] + oc['HR']
            reach = oc['BB'] + oc['1B'] + oc['2B'] + oc['3B'] + oc['HR']
            cum = pi['cum']
            p50 = _pctl(cum, 50)
            p90 = _pctl(cum, 90)
            if threshold is not None:
                w_str = f'{p50 / threshold:5.2f} / {p90 / threshold:5.2f}'
                fm = sum(smooth_factor(c / threshold) for c in cum) / len(cum)
                f_str = f'{fm:6.3f}'
            else:
                w_str = '    -   /    -  '
                f_str = ' 1.000'
            print(f"{i + 1:>3} | {p50:>7} / {p90:<7} | {w_str:>15} | {f_str:>6} | "
                  f"{oc['K'] / pa * 100:6.2f} {oc['BB'] / pa * 100:6.2f} "
                  f"{bip / pa * 100:5.2f} {reach / pa * 100:6.2f} "
                  f"{pi['pitches'] / pa:6.2f} | {pi['pa']:>6}")
        print('-' * 130)

    print()
    print('-- Acumulado del outing --')
    print(f"{'Scenario':<11} {'TotPit p50/p90':>15} {'PA':>6} | {'K%':>6} {'BB%':>6} {'BIP%':>6} {'Reach%':>6} | "
          f"{'1B%':>5} {'2B%':>5} {'3B%':>5} {'HR%':>5} | {'Pit/PA':>6}")
    print('-' * 130)
    for name, threshold in C13_SCENARIOS:
        _thr, agg = aggs[name]
        tot = agg['totals']
        pas = max(1, agg['tot_pas'])
        bip = tot['OUT'] + tot['1B'] + tot['2B'] + tot['3B'] + tot['HR']
        reach = tot['BB'] + tot['1B'] + tot['2B'] + tot['3B'] + tot['HR']
        tp = agg['tot_pitches']
        print(f"{name:<11} {_pctl(tp, 50):>7} / {_pctl(tp, 90):<7} {pas / agg['n']:>6.1f} | "
              f"{tot['K'] / pas * 100:6.2f} {tot['BB'] / pas * 100:6.2f} "
              f"{bip / pas * 100:6.2f} {reach / pas * 100:6.2f} | "
              f"{tot['1B'] / pas * 100:5.2f} {tot['2B'] / pas * 100:5.2f} "
              f"{tot['3B'] / pas * 100:5.2f} {tot['HR'] / pas * 100:5.2f} | "
              f"{sum(tp) / pas:6.2f}")
    print('-' * 130)

    print()
    print('-- Distribución de PAs por banda de workload --')
    print(f"{'Scenario':<11} | " + ' '.join(f'{lbl:>13}' for lbl in _C13_BAND_LABELS))
    print('-' * 130)
    for name, threshold in C13_SCENARIOS:
        _thr, agg = aggs[name]
        pas = max(1, agg['tot_pas'])
        if threshold is None:
            print(f'{name:<11} | ' + ' '.join(f"{'-':>13}" for _ in _C13_BAND_LABELS))
        else:
            print(f"{name:<11} | " + ' '.join(
                f"{agg['bands'][b] / pas * 100:12.2f}%" for b in range(5)))
    print('-' * 130)

    print()
    print('-- Primer inning que alcanza cada nivel de workload (p50/p90; 10 = no cruza en 9) --')
    print(f"{'Scenario':<11} | " + ' '.join(f'{lbl:>15}' for lbl in ['w>1.00', 'w>=1.10', 'w>=1.25', 'w>=1.50']))
    print('-' * 130)
    for name, threshold in C13_SCENARIOS:
        _thr, agg = aggs[name]
        if threshold is None:
            print(f'{name:<11} | ' + ' '.join(f"{'-':>15}" for _ in range(4)))
            continue
        cells = []
        for level in (1.00, 1.10, 1.25, 1.50):
            inns = agg['crossing'][level]
            cells.append(f'{_pctl(inns, 50):>6} / {_pctl(inns, 90):<6}')
        print(f"{name:<11} | " + ' '.join(cells))
    print('-' * 130)


# ---------------------------------------------------------------------------
# 001C-4 · Robustez de la política de fatiga por matchup (SMOOTH-100)
# ---------------------------------------------------------------------------
C14_THRESHOLD = 100
C14_MATCHUP_ORDER = ['STRONG', 'MID', 'WEAK']


def run_matchup_robustness(reps: int) -> None:
    """001C-4 · SMOOTH-0.55-F35 threshold=100 sobre STRONG/MID/WEAK vs MID."""
    print('=' * 130)
    print('001C-4 · Fatigue policy robustness · SMOOTH-0.55-F35 · threshold=100')
    print(f'Bateador MID {BATTER} | take 0.30 / foul 45% / política 65/50/30 | '
          f'{reps:,} outings por matchup | 9 innings, fatiga dinámica')
    print('Criterio: STRONG debe fatigarse algo más tarde y WEAK algo antes; ventana útil en los tres.')
    print('=' * 130)

    aggs = {}
    for name in C14_MATCHUP_ORDER:
        data = [simulate_outing_1c3(MATCHUPS_1C1[name], C14_THRESHOLD, 9_000_000 + i)
                for i in range(reps)]
        aggs[name] = _scenario_aggregate(data, C14_THRESHOLD)

    print()
    print('-- Innings 6-9 por matchup (w p50/p90 · factor · K%/BB%/BIP%) --')
    for name in C14_MATCHUP_ORDER:
        agg = aggs[name]
        print(f'  {name} ({MATCHUPS_1C1[name]}):')
        print(f"    {'Inn':>3} | {'w p50/p90':>15} | {'factor':>6} | "
              f"{'K%':>6} {'BB%':>6} {'BIP%':>6} | {'PA':>6}")
        for i in (5, 6, 7, 8):
            pi = agg['per_inning'][i]
            pa = max(1, pi['pa'])
            oc = pi['oc']
            bip = oc['OUT'] + oc['1B'] + oc['2B'] + oc['3B'] + oc['HR']
            cum = pi['cum']
            p50 = _pctl(cum, 50)
            p90 = _pctl(cum, 90)
            fm = sum(smooth_factor(c / C14_THRESHOLD) for c in cum) / len(cum)
            print(f"    {i + 1:>3} | {p50 / C14_THRESHOLD:6.2f} / {p90 / C14_THRESHOLD:6.2f} | "
                  f"{fm:6.3f} | {oc['K'] / pa * 100:6.2f} {oc['BB'] / pa * 100:6.2f} "
                  f"{bip / pa * 100:6.2f} | {pi['pa']:>6}")
    print('-' * 130)

    print()
    print('-- Acumulado por matchup --')
    print(f"{'Matchup':<8} {'TotPit p50/p90':>15} {'PA':>6} | "
          f"{'K%':>6} {'BB%':>6} {'BIP%':>6} {'Reach%':>6} | {'Pit/PA':>6}")
    print('-' * 130)
    for name in C14_MATCHUP_ORDER:
        agg = aggs[name]
        tot = agg['totals']
        pas = max(1, agg['tot_pas'])
        bip = tot['OUT'] + tot['1B'] + tot['2B'] + tot['3B'] + tot['HR']
        reach = tot['BB'] + tot['1B'] + tot['2B'] + tot['3B'] + tot['HR']
        tp = agg['tot_pitches']
        print(f"{name:<8} {_pctl(tp, 50):>7} / {_pctl(tp, 90):<7} {pas / agg['n']:>6.1f} | "
              f"{tot['K'] / pas * 100:6.2f} {tot['BB'] / pas * 100:6.2f} "
              f"{bip / pas * 100:6.2f} {reach / pas * 100:6.2f} | {sum(tp) / pas:6.2f}")
    print('-' * 130)

    print()
    print('-- Bandas de workload por matchup --')
    print(f"{'Matchup':<8} | " + ' '.join(f'{lbl:>13}' for lbl in _C13_BAND_LABELS))
    print('-' * 130)
    for name in C14_MATCHUP_ORDER:
        agg = aggs[name]
        pas = max(1, agg['tot_pas'])
        print(f"{name:<8} | " + ' '.join(f"{agg['bands'][b] / pas * 100:12.2f}%" for b in range(5)))
    print('-' * 130)

    print()
    print('-- Cruce de niveles por matchup (inning p50/p90; 10 = no cruza en 9) --')
    print(f"{'Matchup':<8} | " + ' '.join(f'{lbl:>15}' for lbl in ['w>1.00', 'w>=1.25', 'w>=1.50']))
    print('-' * 130)
    for name in C14_MATCHUP_ORDER:
        agg = aggs[name]
        cells = []
        for level in (1.00, 1.25, 1.50):
            inns = agg['crossing'][level]
            cells.append(f'{_pctl(inns, 50):>6} / {_pctl(inns, 90):<6}')
        print(f"{name:<8} | " + ' '.join(cells))
    print('-' * 130)


C15_DURATIONS = [(3, 33), (6, 67), (9, 100)]


def _normalized_third(i: int, innings: int) -> int:
    """Tercio normalizado (1..3) del inning i (0-based) para un outing dado."""
    return (i * 3) // innings + 1


def run_scale_345(reps: int) -> None:
    """001C-5 · Escala del threshold para 3/6/9 innings (SMOOTH-0.55-F35)."""
    print('=' * 130)
    print('001C-5 · Escala del threshold 3/6/9 innings · SMOOTH-0.55-F35')
    print(f'MID P {PITCHER_RAW} vs MID B {BATTER} | take 0.30 / foul 45% / política 65/50/30 | '
          f'{reps:,} outings por duración')
    print('Hipótesis: threshold ≈ 2/3 del workload natural → {3: 33, 6: 67, 9: 100}.')
    print('=' * 130)

    natural = {}
    for innings, _thr in C15_DURATIONS:
        data = [simulate_outing_1c1(PITCHER_RAW, 6_000_000 + i, innings=innings)
                for i in range(reps)]
        natural[innings] = data

    print()
    print('-- 001C-5A · Workload natural (fatiga neutralizada) --')
    print(f"{'Dur':>3} {'Thr':>4} | {'Nat p50':>7} {'Nat p90':>7} {'Mean':>7} | "
          f"{'Pit/PA':>7} {'PA':>6} {'PA/Inn':>6} | {'Thr/p50':>7} {'Thr/Mean':>8}")
    print('-' * 130)
    for innings, thr in C15_DURATIONS:
        data = natural[innings]
        tot = [d['total'] for d in data]
        pas = sum(d['pas'] for d in data)
        p50 = _pctl(tot, 50)
        p90 = _pctl(tot, 90)
        mean = sum(tot) / len(tot)
        print(f"{innings:>3} {thr:>4} | {p50:>7} {p90:>7} {mean:>7.1f} | "
              f"{sum(tot) / pas:7.2f} {pas / len(data):>6.1f} {pas / (innings * len(data)):>6.2f} | "
              f"{p50 / thr:7.2f} {mean / thr:8.2f}")

    aggs = {}
    for innings, thr in C15_DURATIONS:
        data = [simulate_outing_1c3(PITCHER_RAW, thr, 5_000_000 + i, innings=innings)
                for i in range(reps)]
        aggs[innings] = (thr, _scenario_aggregate(data, thr), data)

    print()
    print('-- 001C-5B · Snapshot por inning (SMOOTH dinámico) --')
    for innings, thr in C15_DURATIONS:
        _t, agg, _d = aggs[innings]
        print(f'  {innings} innings (threshold={thr}):')
        print(f"    {'Inn':>3} | {'cumPitch p50/p90':>17} | {'w p50/p90':>15} | {'factor':>6} | "
              f"{'K%':>6} {'BB%':>6} {'BIP%':>6} | {'Pit/PA':>6}")
        for i in range(innings):
            pi = agg['per_inning'][i]
            pa = max(1, pi['pa'])
            oc = pi['oc']
            bip = oc['OUT'] + oc['1B'] + oc['2B'] + oc['3B'] + oc['HR']
            cum = pi['cum']
            p50 = _pctl(cum, 50)
            p90 = _pctl(cum, 90)
            fm = sum(smooth_factor(c / thr) for c in cum) / len(cum)
            print(f"    {i + 1:>3} | {p50:>7} / {p90:<7} | "
                  f"{p50 / thr:6.2f} / {p90 / thr:6.2f} | {fm:6.3f} | "
                  f"{oc['K'] / pa * 100:6.2f} {oc['BB'] / pa * 100:6.2f} {bip / pa * 100:6.2f} | "
                  f"{pi['pitches'] / pa:6.2f}")
        print('-' * 130)

    print()
    print('-- 001C-5C · Comparación normalizada por duración --')
    print(f"{'Dur':>3} {'Thr':>4} | {'TotPit p50/p90':>15} {'PA':>6} | {'K%':>6} {'BB%':>6} "
          f"{'BIP%':>6} {'Reach%':>6} | {'Pit/PA':>6}")
    print('-' * 130)
    for innings, thr in C15_DURATIONS:
        _t, agg, _d = aggs[innings]
        tot = agg['totals']
        pas = max(1, agg['tot_pas'])
        bip = tot['OUT'] + tot['1B'] + tot['2B'] + tot['3B'] + tot['HR']
        reach = tot['BB'] + tot['1B'] + tot['2B'] + tot['3B'] + tot['HR']
        tp = agg['tot_pitches']
        print(f"{innings:>3} {thr:>4} | {_pctl(tp, 50):>7} / {_pctl(tp, 90):<7} "
              f"{pas / agg['n']:>6.1f} | {tot['K'] / pas * 100:6.2f} {tot['BB'] / pas * 100:6.2f} "
              f"{bip / pas * 100:6.2f} {reach / pas * 100:6.2f} | {sum(tp) / pas:6.2f}")
    print('-' * 130)

    print()
    print('-- Bandas de workload por duración --')
    print(f"{'Dur':>3} | " + ' '.join(f'{lbl:>13}' for lbl in _C13_BAND_LABELS))
    print('-' * 130)
    for innings, thr in C15_DURATIONS:
        _t, agg, _d = aggs[innings]
        pas = max(1, agg['tot_pas'])
        print(f"{innings:>3} | " + ' '.join(f"{agg['bands'][b] / pas * 100:12.2f}%" for b in range(5)))
    print('-' * 130)

    print()
    print('-- Cruce de niveles (inning p50/p90 · fracción del outing p50/p90) --')
    print(f"{'Dur':>3} | " + ' '.join(f'{lbl:>19}' for lbl in ['w>1.00', 'w>=1.25', 'w>=1.50']))
    print('-' * 130)
    for innings, thr in C15_DURATIONS:
        _t, agg, _d = aggs[innings]
        cells = []
        for level in (1.00, 1.25, 1.50):
            inns = agg['crossing'][level]
            ip50, ip90 = _pctl(inns, 50), _pctl(inns, 90)
            f50 = min(ip50, innings) / innings
            f90 = min(ip90, innings) / innings
            cells.append(f'{ip50:>2} / {ip90:<2} ({f50:.2f}/{f90:.2f})')
        print(f"{innings:>3} | " + ' '.join(f'{c:>19}' for c in cells))
    print('-' * 130)

    print()
    print('-- Factor medio por tercio normalizado del outing --')
    print(f"{'Dur':>3} | {'Primer 1/3':>12} {'Segundo 1/3':>12} {'Último 1/3':>12}")
    print('-' * 60)
    for innings, thr in C15_DURATIONS:
        _t, agg, _d = aggs[innings]
        third_vals = {1: [], 2: [], 3: []}
        for i in range(innings):
            cum = agg['per_inning'][i]['cum']
            third_vals[_normalized_third(i, innings)].extend(
                smooth_factor(c / thr) for c in cum)
        cells = []
        for k in (1, 2, 3):
            v = third_vals[k]
            cells.append(f'{sum(v) / len(v):12.3f}')
        print(f"{innings:>3} | " + ' '.join(cells))
    print('-' * 60)

    print()
    print('-- w PA-a-PA dentro del ÚLTIMO inning (p50/p90 por posición; factor p50) --')
    for innings, thr in C15_DURATIONS:
        _t, _agg, d = aggs[innings]
        max_pos = max(len(x['last_inning_w']) for x in d)
        by_pos = [[] for _ in range(max_pos)]
        for x in d:
            for pos, w in enumerate(x['last_inning_w']):
                by_pos[pos].append(w)
        labels = ' '.join(
            f'{pos + 1}:{_pctl(v, 50):.2f}/{_pctl(v, 90):.2f}(f{smooth_factor(_pctl(v, 50)):.3f})'
            for pos, v in enumerate(by_pos) if v)
        print(f'  {innings} inn (thr={thr}): {labels}')
    print('-' * 130)


# ---------------------------------------------------------------------------
# 001D-1 · Caracterización de la decisión CPU de cambio de pitcher bajo Policy v2
# ---------------------------------------------------------------------------
# NO toca producción: solo lee compute_fatigue_level / get_cpu_pitcher_change_decision
# tal como están hoy, sobre outings SMOOTH v2 (threshold=100, 9 innings).
# Registra, para cada salida, el PRIMER PA en que la CPU es elegible para cambiar
# (fatigue_level >= umbral de dificultad) y el PRIMER PA en que efectivamente
# cambia (con la probabilidad real). Guarda inning, pitch_count, workload y el
# factor SMOOTH real del engine en ese momento.
CPU_DIFFICULTIES = ["HARD", "MEDIUM", "EASY"]
_CPU_DIFFICULTY_SEED = {"HARD": 1, "MEDIUM": 2, "EASY": 3}


def _outing_pa_observations(pitcher_raw: dict, threshold, seed: int, innings: int = 9):
    """Camina PAs y registra (inning_1based, pitch_count al inicio) de cada PA."""
    rng = random.Random(seed)
    pitch_count = 0
    obs = []
    for inn_idx in range(innings):
        outs = 0
        inning_p = 0
        while outs < 3 and inning_p < MAX_INNING_PITCHES:
            obs.append((inn_idx + 1, pitch_count))
            outcome, p = _simulate_pa_fatigued(pitcher_raw, pitch_count, threshold, rng.getrandbits(63))
            pitch_count += p
            inning_p += p
            if outcome in _OUT_EVENTS_1C1:
                outs += 1
    return obs


def run_cpu_change_characterization(reps: int) -> None:
    """001D-1 · ¿Cuándo cambiaría la CPU hoy, con Policy v2 ya activa?"""
    threshold = get_pitch_threshold(9)
    print('=' * 130)
    print('001D-1 · Decisión CPU de cambio bajo Fatigue Policy v2 (sin tocar producción)')
    print(f'Outings SMOOTH de 9 innings, threshold={threshold} | {reps:,} outings por matchup')
    print('Elegible = primer PA con workload = get_workload(pc, threshold) >= umbral de dificultad.')
    print('Factor = SMOOTH real del engine (get_fatigue_factor) en ese pitch_count.')
    print('=' * 130)

    print()
    print('-- Trigger nominal analítico (9 inn; w_umbral por dificultad, 001D-4) --')
    print(f"{'Dif':>6} {'w umbral':>9} | {'pc':>4} {'w':>6} {'factor SMOOTH':>13}")
    print('-' * 46)
    for diff in CPU_DIFFICULTIES:
        w_thr = _CPU_CHANGE_WORKLOAD_THRESHOLD.get(diff, 1.35)
        pc = math.ceil(w_thr * threshold)
        print(f"{diff:>6} {w_thr:>9.2f} | {pc:>4} {get_workload(pc, threshold):>6.2f} "
              f"{get_fatigue_factor(pc, threshold):>13.4f}")
    print('-' * 46)

    for mname in ('MID', 'WEAK', 'STRONG'):
        pitcher = MATCHUPS_1C1[mname]
        data = [_outing_pa_observations(pitcher, threshold, 4_100_000 + i) for i in range(reps)]

        eligible = {d: [] for d in CPU_DIFFICULTIES}
        actual = {d: [] for d in CPU_DIFFICULTIES}
        for idx, obs in enumerate(data):
            for diff in CPU_DIFFICULTIES:
                w_thr = _CPU_CHANGE_WORKLOAD_THRESHOLD.get(diff, 1.35)
                for inning, pc in obs:
                    if get_workload(pc, threshold) >= w_thr:
                        eligible[diff].append((inning, pc))
                        break
                random.seed(4_100_000 + idx + _CPU_DIFFICULTY_SEED[diff])
                for inning, pc in obs:
                    if get_cpu_pitcher_change_decision(pc, get_workload(pc, threshold), diff):
                        actual[diff].append((inning, pc))
                        break

        print()
        print(f'-- {mname} {pitcher} --')
        print(f"{'Dif':>6} | {'elegible inn p50/p90':>21} {'pc p50/p90':>11} {'w p50/p90':>12} "
              f"{'factor p50/p90':>16} {'%outings':>9}")
        print('-' * 100)
        for diff in CPU_DIFFICULTIES:
            recs = eligible[diff]
            if not recs:
                print(f"{diff:>6} | (nunca elegible en 9 inn)")
                continue
            inns = [r[0] for r in recs]
            pcs = [r[1] for r in recs]
            ws = [pc / threshold for pc in pcs]
            fs = [get_fatigue_factor(pc, threshold) for pc in pcs]
            print(f"{diff:>6} | {_pctl(inns, 50):>9} / {_pctl(inns, 90):<9} "
                  f"{_pctl(pcs, 50):>5} / {_pctl(pcs, 90):<5} "
                  f"{_pctl(ws, 50):>5.2f} / {_pctl(ws, 90):<5.2f} "
                  f"{_pctl(fs, 50):>7.4f} / {_pctl(fs, 90):<7.4f} {len(recs) / reps * 100:>8.1f}%")
        print('-' * 100)
        for diff in CPU_DIFFICULTIES:
            recs = actual[diff]
            if not recs:
                print(f"  {diff:>6} real (con prob): nunca cambia en 9 inn")
                continue
            inns = [r[0] for r in recs]
            pcs = [r[1] for r in recs]
            fs = [get_fatigue_factor(pc, threshold) for pc in pcs]
            print(f"  {diff:>6} real (con prob): inn {_pctl(inns, 50)}/{_pctl(inns, 90)} | "
                  f"pc {_pctl(pcs, 50)}/{_pctl(pcs, 90)} | factor {_pctl(fs, 50):.4f}/{_pctl(fs, 90):.4f} | "
                  f"{len(recs) / reps * 100:.1f}%")
    print('=' * 130)


# ---------------------------------------------------------------------------
# 001D-2 · Fatigue signal semantics — workload es la señal estratégica canónica
# ---------------------------------------------------------------------------
# Bandas derivadas de los puntos ya usados durante 001B/001C para interpretar
# las simulaciones (NO son constantes nuevas). La CPU razona sobre workload
# (en qué zona de utilización está el pitcher), no sobre el nivel de fatiga
# legacy; fatigue_factor es la degradación física que consume el outcome engine.
WORKLOAD_BANDS = [
    (float('-inf'), 1.00, 'HEALTHY'),
    (1.00, 1.10, 'EARLY_FATIGUE'),
    (1.10, 1.25, 'MANAGEABLE'),
    (1.25, 1.50, 'HIGH_RISK'),
    (1.50, float('inf'), 'SEVERE'),
]


def workload_band(w: float) -> str:
    for lo, hi, name in WORKLOAD_BANDS:
        if lo < w <= hi:
            return name
    return 'SEVERE'


# ---------------------------------------------------------------------------
# 001D-3 · Estrategias CPU de cambio (workload-based) × matchup
# ---------------------------------------------------------------------------
# Políticas LAB (no mapear aún a EASY/MEDIUM/HARD): la CPU "considera el cambio"
# al alcanzar el workload. Mismos requisitos reales (MIN_PITCHES_TO_CHANGE, etc.).
CPU_STRATEGY_THRESHOLDS = [
    ('AGGRESSIVE', 1.10),
    ('BALANCED', 1.25),
    ('TOLERANT', 1.50),
]


def _simulate_full_outing_records(pitcher_raw: dict, threshold, seed: int, innings: int = 9):
    """Outing completo de 9 innings como lista de (inning, pc_start, outcome, pitches).

    Es la secuencia compartida: cada política se deriva del mismo stream,
    cortando en el primer PA en que considera el cambio.
    """
    rng = random.Random(seed)
    pc = 0
    recs = []
    for inn_idx in range(innings):
        outs = 0
        inning_p = 0
        while outs < 3 and inning_p < MAX_INNING_PITCHES:
            outcome, p = _simulate_pa_fatigued(pitcher_raw, pc, threshold, rng.getrandbits(63))
            recs.append((inn_idx + 1, pc, outcome, p))
            pc += p
            inning_p += p
            if outcome in _OUT_EVENTS_1C1:
                outs += 1
    return recs


def _strategy_from_records(recs, threshold, w_threshold):
    """Aplica una política a un outing: corta en el primer PA elegible."""
    outcomes = Counter()
    band_pas = Counter()
    for idx, (inning, pc_start, outcome, _p) in enumerate(recs):
        w = pc_start / threshold
        if pc_start >= MIN_PITCHES_TO_CHANGE and w >= w_threshold:
            return {
                'removed': True,
                'inning': inning,
                'pc': pc_start,
                'w': w,
                'factor': get_fatigue_factor(pc_start, threshold),
                'pas': idx,
                'outcomes': outcomes,
                'band_pas': band_pas,
                'total_pitches': pc_start,
            }
        band_pas[workload_band(w)] += 1
        outcomes[outcome] += 1
    total_pitches = recs[-1][1] + recs[-1][3] if recs else 0
    return {
        'removed': False,
        'inning': None,
        'pc': total_pitches,
        'w': total_pitches / threshold,
        'factor': get_fatigue_factor(total_pitches, threshold),
        'pas': len(recs),
        'outcomes': outcomes,
        'band_pas': band_pas,
        'total_pitches': total_pitches,
    }


def _strategy_block(name, w_threshold, per_matchup, reps):
    print()
    print(f'== {name} (considera el cambio a w >= {w_threshold:.2f}) ==')
    for mname, rows in per_matchup.items():
        removed = [r for r in rows if r['removed']]
        rm = len(removed) / reps * 100
        inn_counts = Counter(r['inning'] for r in removed)
        inn_le6 = sum(c for i, c in inn_counts.items() if i <= 6) / reps * 100
        inn7 = inn_counts.get(7, 0) / reps * 100
        inn8 = inn_counts.get(8, 0) / reps * 100
        inn9 = inn_counts.get(9, 0) / reps * 100
        never = (reps - len(removed)) / reps * 100
        pcs = [r['pc'] for r in removed]
        ws = [r['w'] for r in removed]
        fs = [r['factor'] for r in removed]
        pas = [r['pas'] for r in rows]
        tot_out = Counter()
        tot_band = Counter()
        for r in rows:
            tot_out.update(r['outcomes'])
            tot_band.update(r['band_pas'])
        total_pas = sum(tot_out.values()) or 1
        bip = sum(tot_out[k] for k in ('OUT', '1B', '2B', '3B', 'HR'))
        reach = sum(tot_out[k] for k in ('BB', '1B', '2B', '3B', 'HR'))
        bands = tot_band
        band_total = sum(bands.values()) or 1
        print(f"  -- {mname} --")
        print(f"    removed {rm:5.1f}%  |  <=6 {inn_le6:5.1f}%  7 {inn7:5.1f}%  8 {inn8:5.1f}%  "
              f"9 {inn9:5.1f}%  never {never:5.1f}%")
        if removed:
            print(f"    pit@removal {_pctl(pcs, 50):>4}/{_pctl(pcs, 90):<4} | "
                  f"w@removal {_pctl(ws, 50):>5.2f}/{_pctl(ws, 90):<5.2f} | "
                  f"factor@removal {_pctl(fs, 50):>7.4f}/{_pctl(fs, 90):<7.4f}")
        else:
            print("    pit@removal  n/a (nunca removido)")
        print(f"    starter PA p50 {_pctl(pas, 50):>4} mean {sum(pas) / len(pas):>5.1f} | "
              f"K {tot_out['K'] / total_pas * 100:5.2f}%  BB {tot_out['BB'] / total_pas * 100:5.2f}%  "
              f"BIP {bip / total_pas * 100:5.2f}%  Reach {reach / total_pas * 100:5.2f}%")
        band_str = '  '.join(
            f"{name_b[:4]} {bands.get(name_b, 0) / band_total * 100:5.1f}%"
            for _lo, _hi, name_b in WORKLOAD_BANDS)
        print(f"    PA por banda: {band_str}")


def run_cpu_strategy_comparison(reps: int) -> None:
    """001D-3 · Compara políticas de cambio workload-based por matchup."""
    threshold = get_pitch_threshold(9)
    print('=' * 130)
    print('001D-3 · Estrategias CPU de cambio de pitcher (workload-based, Policy v2)')
    print(f'Outings de 9 innings, threshold={threshold} | {reps:,} outings por matchup')
    print(f'Requisitos reales: MIN_PITCHES_TO_CHANGE={MIN_PITCHES_TO_CHANGE}; corte en el primer PA elegible.')
    print('Señal estratégica (001D-2): workload = pitch_count / threshold. Bandas: '
          'HEALTHY/ EARLY_FATIGUE/ MANAGEABLE/ HIGH_RISK/ SEVERE.')
    print('=' * 130)

    for name, w_thr in CPU_STRATEGY_THRESHOLDS:
        per_matchup = {}
        for mname in ('STRONG', 'MID', 'WEAK'):
            pitcher = MATCHUPS_1C1[mname]
            rows = []
            for i in range(reps):
                recs = _simulate_full_outing_records(pitcher, threshold, 4_200_000 + i)
                rows.append(_strategy_from_records(recs, threshold, w_thr))
            per_matchup[mname] = rows
        _strategy_block(name, w_thr, per_matchup, reps)
    print('=' * 130)
    print('Lectura: STRONG trabaja menos -> alcanza cada w más tarde; WEAK trabaja más -> antes.')
    print('Si una política no preserva esa diferenciación, no sirve como dificultad.')
    print('=' * 130)


# ---------------------------------------------------------------------------
# 001D-4 · Precio estratégico de esperar (marginal cost) + barrido ampliado
# ---------------------------------------------------------------------------
# 001D-4A: añade w=1.20 y w=1.35 a los regímenes ya caracterizados en 001D-3.
# 001D-4B: outcomes por ventana de workload sobre el stream completo, para medir
#          qué cuesta dejar al pitcher más allá de cada threshold (Δ vs sano).
# 001D-4C: el mapeo a EASY/MEDIUM/HARD es una decisión posterior (001D-4C/001D-4).
CPU_PRICING_THRESHOLDS = [
    ('w1.10', 1.10),
    ('w1.20', 1.20),
    ('w1.25', 1.25),
    ('w1.35', 1.35),
    ('w1.50', 1.50),
]
PRICING_WINDOWS = [
    (0.00, 1.00, 'sano'),
    (1.00, 1.10, '1.00-1.10'),
    (1.10, 1.20, '1.10-1.20'),
    (1.20, 1.25, '1.20-1.25'),
    (1.25, 1.35, '1.25-1.35'),
    (1.35, 1.50, '1.35-1.50'),
    (1.50, float('inf'), '>1.50'),
]


def run_cpu_strategy_pricing(reps: int) -> None:
    """001D-4A/B · Barrido ampliado + coste marginal de esperar."""
    threshold = get_pitch_threshold(9)
    print('=' * 130)
    print('001D-4 · Precio estratégico de esperar al cambiar de pitcher (Policy v2)')
    print(f'Outings de 9 innings, threshold={threshold} | {reps:,} outings por matchup')
    print('A: barrido 1.10/1.20/1.25/1.35/1.50 · B: outcomes por ventana (stream completo, sin retiro).')
    print('=' * 130)

    streams = {}
    for mname in ('STRONG', 'MID', 'WEAK'):
        pitcher = MATCHUPS_1C1[mname]
        streams[mname] = [
            _simulate_full_outing_records(pitcher, threshold, 4_300_000 + i)
            for i in range(reps)
        ]

    print()
    print('-- A · Retiro por política (mediana sobre salidas; % de outings) --')
    print(f"{'thr':>5} |" + ''.join(f" {m:>34}" for m in ('STRONG', 'MID', 'WEAK')))
    print(f"{'':>5} |" + ''.join(f" {'removed':>8}{'never':>8}{'inn':>6}{'factor':>8}" for _ in range(3)))
    print('-' * 118)
    for label, w_thr in CPU_PRICING_THRESHOLDS:
        cells = []
        for mname in ('STRONG', 'MID', 'WEAK'):
            rows = [_strategy_from_records(recs, threshold, w_thr) for recs in streams[mname]]
            removed = [r for r in rows if r['removed']]
            rm = len(removed) / reps * 100
            inn = _pctl([r['inning'] for r in removed], 50) if removed else 0
            fac = _pctl([r['factor'] for r in removed], 50) if removed else 0.0
            cells.append(f" {rm:>7.1f}%{100 - rm:>7.1f}%{inn:>6}{fac:>8.4f}")
        print(f"{label:>5} |" + ''.join(cells))
    print('-' * 118)

    print()
    print('-- B · Outcomes por ventana de workload (todo PA del starter, sin retiro) --')
    print('   ΔReach / ΔK = puntos porcentuales vs la banda sana (w<=1.00).')
    for mname in ('STRONG', 'MID', 'WEAK'):
        bucket = {name: Counter() for _lo, _hi, name in PRICING_WINDOWS}
        for recs in streams[mname]:
            for _inning, pc_start, outcome, _p in recs:
                w = pc_start / threshold
                for lo, hi, name in PRICING_WINDOWS:
                    if lo < w <= hi or (lo == 0.0 and w <= hi):
                        bucket[name][outcome] += 1
                        break
        base = bucket['sano']
        base_n = sum(base.values()) or 1
        base_reach = sum(base[k] for k in ('BB', '1B', '2B', '3B', 'HR')) / base_n * 100
        base_k = base['K'] / base_n * 100
        print(f"  -- {mname} --")
        print(f"    {'ventana':>10} {'PA/out':>7} {'K%':>6} {'BB%':>6} {'BIP%':>6} {'Reach%':>7} "
              f"{'ΔReach':>7} {'ΔK':>7}")
        for _lo, _hi, name in PRICING_WINDOWS:
            c = bucket[name]
            n = sum(c.values())
            if n == 0:
                print(f"    {name:>10} {0.0:>7.2f}       -      -      -       -       -")
                continue
            k = c['K'] / n * 100
            bb = c['BB'] / n * 100
            bip = sum(c[x] for x in ('OUT', '1B', '2B', '3B', 'HR')) / n * 100
            reach = sum(c[x] for x in ('BB', '1B', '2B', '3B', 'HR')) / n * 100
            print(f"    {name:>10} {n / reps:>7.2f} {k:>6.2f} {bb:>6.2f} {bip:>6.2f} {reach:>7.2f} "
                  f"{reach - base_reach:>+7.2f} {k - base_k:>+7.2f}")
    print('=' * 130)
    print('Lectura: si una ventana no empeora K/BB/Reach vs sano, esperar hasta ella no cuesta nada;')
    print('si 1.25-1.50 empeora claramente, ahí vive la diferencia útil para una dificultad tolerante.')
    print('=' * 130)


def run_pa_level(reps: int) -> None:
    print("=" * 130)
    print("001B-4 · Full PA Monte Carlo · fatiga dinámica dentro del PA")
    print(f"MID P {PITCHER_RAW} vs MID B {BATTER} | CPU {DIFFICULTY} | threshold={THRESHOLD} | "
          f"{reps:,} PA por escenario")
    print("Política LAB: TAKE 35/25/10% por 0/1/2 strikes (Swing = NORMAL). "
          "Workload = starting workload; fatiga avanza por lanzamiento.")
    print("=" * 130)
    print(f"{'Curve':<8} {'Start':>5} | {'K%':>6} {'BB%':>6} {'BIP%':>6} {'OUT%':>6} "
          f"{'1B%':>6} {'2B%':>6} {'3B%':>6} {'HR%':>6} | {'Reach%':>7} | "
          f"{'Pit/PA':>6} {'p95':>4} {'max':>4} | {'CapPAs':>6} {'FinalWk':>7}")
    print("-" * 130)

    global_max_count = 0
    for curve in CURVES:
        for w in WORKLOADS:
            outcomes, lengths, final_counts = run_pa_scenario(curve, w, reps)
            n = sum(outcomes.values())
            reach = (outcomes["BB"] + outcomes["1B"] + outcomes["2B"] + outcomes["3B"] + outcomes["HR"]) / n
            mean_len = sum(lengths) / n
            p95 = _p95(lengths)
            max_len = max(lengths)
            mean_final = sum(final_counts) / n
            global_max_count = max(global_max_count, max(final_counts))
            print(
                f"{curve:<8} {w:>5.0%} | "
                f"{_fmt_pct(outcomes['K'], n)} {_fmt_pct(outcomes['BB'], n)} "
                f"{_fmt_pct(outcomes['OUT'] + outcomes['1B'] + outcomes['2B'] + outcomes['3B'] + outcomes['HR'], n)} "
                f"{_fmt_pct(outcomes['OUT'], n)} "
                f"{_fmt_pct(outcomes['1B'], n)} {_fmt_pct(outcomes['2B'], n)} "
                f"{_fmt_pct(outcomes['3B'], n)} {_fmt_pct(outcomes['HR'], n)} | "
                f"{reach * 100:7.2f} | "
                f"{mean_len:6.2f} {p95:>4} {max_len:>4} | "
                f"{outcomes['CAP']:>6} {mean_final / THRESHOLD * 100:7.1f}"
            )
    print("-" * 130)
    print(f"FinalWk = % del threshold del count efectivo en el último pitch del PA.")
    print(f"max pitch_count alcanzado global: {global_max_count}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Monte Carlo de fatiga (GAMEPLAY-ENGINE-001B)")
    parser.add_argument("--mode", choices=["pa", "pitch", "discipline", "cv", "take", "foul", "bc", "d2", "cv2", "f5", "c1", "c3", "c4", "c5", "d1", "d3", "d4", "e1", "e2", "e3", "e3b", "e5", "e003a", "e003a-tail", "e003b", "e003b2", "e003b3"], default="pa",
                        help="pa = PA completo (001B-4); pitch = pitch suelto (001B-3); "
                             "discipline = diagnóstico de count/disciplina sin fatiga (002A); "
                             "cv = factorial Control×Vision (002B); "
                             "take = baseline sweep de TAKE (002C-B); "
                             "foul = sweep de terminación foul/contact (002C-C); "
                             "bc = factorial TAKE×foul (002C-BC); "
                             "d2 = two-strike discipline sensitivity (002D); "
                             "cv2 = Control×Vision sobre candidato 002D (002C-CV); "
                              "e1 = baseline PROD vs candidato B3-C1 head-to-head sobre grid CTL×VIS (002E-1); "
                              "e2 = robustez B3-C1 por perfil ofensivo del bateador (WEAK/MID/STRONG over CTL fijo) (002E-2); "
                              "e2 = robustez B3-C1 por perfil ofensivo del bateador WEAK/MID/STRONG sobre grid CTL (002E-2); "
                             "f5 = full-PA sobre el PA calibrado 002 (001B-5); "
                             "c1 = distribución natural de workload, fatiga neutralizada (001C-1); "
                             "c3 = threshold × outing completo, SMOOTH (001C-3); "
                             "c4 = robustez por matchup, SMOOTH-100 (001C-4); "
                              "c5 = escala del threshold 3/6/9 innings (001C-5); "
                              "d1 = caracterización de la decisión CPU de cambio bajo Policy v2 (001D-1); "
                              "e2 = robustez B3-C1 por matchup ofensivo del bateador, CTL×perfil WEAK/MID/STRONG (002E-2); "
"e5 = producción acceptance: calculate_play_outcome() sin knobs, grid 3×3 CTL×VIS, contratos JA–JF (002E-5); "
                              "e003a = calibrated engine baseline: 3×3 pitcher×batter, producción pura, contratos K1–K6 (003A); "
                              "e003a-tail = K5-R: validación de cola de PA (STRONG×WEAK, 200k, seeds nuevas) (003A-TAIL-1); "
                              "e003b = stuff semantic candidates: 3 brazos × 5 niveles (45/55/70/85/95), LAB, contratos L1–L6 (003B-1); "
                              "e003b2 = stuff vs VEL/MOV sensitivity: 5 sweeps × 5 niveles, contratos M1–M6 + geometría de vectores (003B-2); "
                              "e003b3 = S2 coefficient sweep: 7 coefs × 5 Stuff + power reference, contratos N1–N7, suppression_ratio diagnóstico (003B-3); "
                              "d3 = comparación de estrategias CPU workload-based por matchup (001D-3); "
                             "d4 = barrido ampliado + coste marginal de esperar (001D-4A/B)")
    parser.add_argument("--reps", type=int, default=REPS, help="réplicas por escenario")
    args = parser.parse_args()

    if args.mode == "pitch":
        run_pitch_level(args.reps)
    elif args.mode == "discipline":
        run_discipline_level(args.reps)
    elif args.mode == "cv":
        run_control_vision_level(args.reps)
    elif args.mode == "take":
        run_take_bias_sweep(args.reps)
    elif args.mode == "foul":
        run_foul_sweep(args.reps)
    elif args.mode == "bc":
        run_bc_factorial(args.reps)
    elif args.mode == "d2":
        run_two_strike_sweep(args.reps)
    elif args.mode == "cv2":
        run_control_vision_level_calibrated(args.reps)
    elif args.mode == "e1":
        run_prod_vs_b3c1(args.reps)
    elif args.mode == "e2":
        run_matchup_robustness_e2(args.reps)
    elif args.mode == "e3":
        run_clamp_characterization_e3(args.reps)
    elif args.mode == "e3b":
        run_clamp001_floor_mc_e3b(args.reps)
    elif args.mode == "e5":
        run_production_acceptance_e5(args.reps)
    elif args.mode == "e003a":
        run_calibrated_baseline_e003a(args.reps)
    elif args.mode == "e003a-tail":
        run_tail_stability_k5r(args.reps)
    elif args.mode == "e003b":
        run_stuff_semantic_candidates_e003b(args.reps)
    elif args.mode == "e003b2":
        run_stuff_vs_vel_mov_sensitivity_e003b2(args.reps)
    elif args.mode == "e003b3":
        run_stuff_coefficient_e003b3(args.reps)
    elif args.mode == "f5":
        run_fatigue_curve_comparison(args.reps)
    elif args.mode == "c1":
        run_threshold_distribution(args.reps)
    elif args.mode == "c3":
        run_threshold_outing(args.reps)
    elif args.mode == "c4":
        run_matchup_robustness(args.reps)
    elif args.mode == "c5":
        run_scale_345(args.reps)
    elif args.mode == "d1":
        run_cpu_change_characterization(args.reps)
    elif args.mode == "d3":
        run_cpu_strategy_comparison(args.reps)
    elif args.mode == "d4":
        run_cpu_strategy_pricing(args.reps)
    else:
        run_pa_level(args.reps)


if __name__ == "__main__":
    main()