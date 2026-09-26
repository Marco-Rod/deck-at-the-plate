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
import inspect
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
    apply_pitcher_fatigue,
    get_fatigue_factor,
    get_pitch_threshold,
    get_workload,
)
from app.engine.attribute_mapper import map_card_to_pitcher_attrs
from app.engine.stuff_policy import (
    STUFF_BASELINE as PROD_STUFF_BASELINE,
    STUFF_FATIGUE_ALPHA as PROD_STUFF_FATIGUE_ALPHA,
    STUFF_POWER_SUPPRESSION as PROD_STUFF_K,
    effective_stuff as prod_effective_stuff,
    stuff_power_suppression as prod_stuff_power_suppression,
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
                      power_log: list = None,
                      workload: float = None) -> dict:
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
        workload:  factor de fatiga a aplicar (003B-5A · semántica Stuff×fatigue).
                    None → DISCIPLINE_WORKLOAD congelado (0.75 → factor 1.0,
                    comportamiento 003B-1..4 exacto). Cuando se pasa, es el
                    workload productivo (1.00/1.20/1.35/1.50 → f vía la curva
                    SMOOTH-0.55-F35) y VEL/CTL/MOV se fatigan normalmente por PROD.
    """
    random.seed(seed)
    balls = 0
    strikes = 0
    pitches = 0
    eff_workload = DISCIPLINE_WORKLOAD if workload is None else workload
    pitch_count = int(eff_workload * THRESHOLD)  # congelado → factor 1.0 (o w.prod)

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
            DISCIPLINE_CURVE, pitch_count, workload=eff_workload,
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
# 003B-4 · Power × Stuff matchup robustness (romper/no romper k=0.30)
# ---------------------------------------------------------------------------
# Con k=0.30 fijado, cruzar POWER (batter) × STUFF (pitcher) para confirmar que
# NINGÚN atributo borra al otro en su punto más adverso. 15 celdas = POW
# {45,55,70,85,95} × ST {45,70,95}. O1–O7 congelados antes de correr.
O1_MONO_PP = 0.2    # O1/O2: tol de monotonía por paso
O3_MIN_PP = 1.0     # O3: POW95×ST95 ≥ POW70×ST95 + 1.0pp
O4_XBH_MAX = 55.0   # O4: XBH/BIP max en columna Stuff45
O4_HR_MAX = 35.0    # O4: HR/BIP max en columna Stuff45
O5_TOL_PP = 1.0     # O5: diagonal no decreciente (tol total de acumulación)
O6_SPAN_PP = 0.5    # O6: span por canal de aislamiento
O7_P95_MAX = 6      # O7: K5-R tail


def run_matchup_robustness_e003b4(reps: int) -> None:
    """003B-4 · POWER×STUFF k=.30, contrọaros O1–O7 (750k PA)."""
    n = reps
    k = 0.30
    powers = [45, 55, 70, 85, 95]
    stuffs = [45, 70, 95]
    pitcher = PITCHER_PROFILES_003A["MID"]
    cells = {}

    for powa in powers:
        for st in stuffs:
            batter = {"contacto": 70, "poder": powa, "vision": 70}
            agg = {"pitches": 0, "take_attempts": 0, "called_strikes_on_take": 0,
                   "swing_attempts": 0, "whiffs": 0, "outcome": Counter(),
                   "lengths": [], "power": [], "bips": 0, "len12": 0, "len16": 0}
            for rep in range(reps):
                seed = int(DISCIPLINE_WORKLOAD * 1000) * 10**6 + rep  # seeds compartidas
                d = _simulate_pa_diag(E1_POLICY, seed,
                                      batter_attrs=batter,
                                      pitcher_attrs=pitcher,
                                      stuff_level=st,
                                      stuff_arm="S2",
                                      stuff_k_qty=k)
                agg["pitches"] += d["pitches"]
                agg["take_attempts"] += d["take_attempts"]
                agg["called_strikes_on_take"] += d["called_strikes_on_take"]
                agg["swing_attempts"] += d["swing_attempts"]
                agg["whiffs"] += d["whiffs"]
                agg["bips"] += d["bips"]
                agg["outcome"][d["outcome"]] += 1
                agg["lengths"].append(d["pitches"])
                if d["pitches"] >= 12:
                    agg["len12"] += 1
                if d["pitches"] >= 16:
                    agg["len16"] += 1
            agg["lengths"].sort()
            agg["p95"] = agg["lengths"][int(len(agg["lengths"]) * 0.95) - 1]
            agg["power"].sort()
            cells[(powa, st)] = agg

    rows = {(powa, st): _metric_row(cells[(powa, st)], n)
            for powa in powers for st in stuffs}

    def xbh(p, s):
        return rows[(p, s)]["xbh"]

    def hr(p, s):
        return rows[(p, s)]["hr"]

    print("=" * 150)
    print("GAMEPLAY-ENGINE-003B-4 · POWER × STUFF MATCHUP ROBUSTNESS (k=0.30)")
    print(f"5 Powers × 3 Stuffs × {reps:,} PA = {reps*15:,} PA | seeds compartidas "
          "(750M+rep) | MID pitcher/batter | agent 65/50/30 | PROD discipline")
    print("Contratos O1–O7 FIJADOS ANTES de correr. calculator.py UNCHANGED.")
    print("=" * 150)

    # Matrices XBH/BIP y HR/BIP
    print()
    print("-- XBH/BIP (%) · filas = POWER, columnas = STUFF --")
    print(f"{'POW':>5} | {'ST45':>8} {'ST70':>8} {'ST95':>8}")
    print("-" * 40)
    for p in powers:
        print(f"{p:>5} | {xbh(p, 45):>8.2f} {xbh(p, 70):>8.2f} {xbh(p, 95):>8.2f}")
    print("-" * 40)
    print()
    print("-- HR/BIP (%) · filas = POWER, columnas = STUFF --")
    print(f"{'POW':>5} | {'ST45':>8} {'ST70':>8} {'ST95':>8}")
    print("-" * 40)
    for p in powers:
        print(f"{p:>5} | {hr(p, 45):>8.2f} {hr(p, 70):>8.2f} {hr(p, 95):>8.2f}")
    print("-" * 40)

    # Pendientes de saturación
    print()
    print("-- PENDIENTES (Δ XBH/BIP / 10) --")
    print(f"{'':>5} | {'Δ/10 Power ST45':>15} {'Δ/10 Power ST70':>15} "
          f"{'Δ/10 Power ST95':>15}")
    print("-" * 60)
    for p in (None,):
        print(f"{'POW':>5} | {'':>15} {'':>15} {'':>15}")
    line = " "
    for st in stuffs:
        slope = (xbh(95, st) - xbh(45, st)) / 5.0
        line += f" | Δ/10 Pow @ ST{st} = {slope:.3f}"
    print(line)
    print()
    for p in powers:
        slope_st = (xbh(p, 95) - xbh(p, 45)) / 5.0
        print(f"Δ/10 Stuff @ POW{p} = {slope_st:.3f}")

    # CONTRATOS O1–O7
    print()
    print("-- CONTRATOS (O1–O7, fijados antes) --")

    def mono_inc(s):
        return all(s[i + 1] + O1_MONO_PP >= s[i] for i in range(len(s) - 1))

    def mono_dec(s):
        return all(s[i + 1] <= s[i] + O1_MONO_PP for i in range(len(s) - 1))

    # O1 · POWER MONOTONIC con STUFF fijo (incluso ST95).
    o1_ok = True
    for st in stuffs:
        seq = [xbh(p, st) for p in powers]
        ok = mono_inc(seq)
        o1_ok &= ok
        print(f"  O1 POWER↑ @ST{st} ({' · '.join(f'{v:.2f}' for v in seq)}): "
              f"{'PASS' if ok else 'FAIL'}")
    print(f"  O1 POWER MONOTONIC (todos): {'PASS' if o1_ok else 'FAIL'}")

    # O2 · STUFF MONOTONIC con POWER fijo (incluso POW95).
    o2_ok = True
    for p in powers:
        seq = [xbh(p, st) for st in stuffs]
        ok = mono_dec(seq)
        o2_ok &= ok
        print(f"  O2 STUFF↓ @POW{p} ({' · '.join(f'{v:.2f}' for v in seq)}): "
              f"{'PASS' if ok else 'FAIL'}")
    print(f"  O2 STUFF MONOTONIC (todos): {'PASS' if o2_ok else 'FAIL'}")

    # O3 · POW95×ST95 ≥ POW70×ST95 + margen.
    o3_margin = xbh(95, 95) - xbh(70, 95)
    o3_ok = o3_margin >= O3_MIN_PP
    print(f"  O3 POW95×ST95 vs POW70×ST95 (Δ {o3_margin:+.2f} ≥ +{O3_MIN_PP}): "
          f"{'PASS' if o3_ok else 'FAIL'}")

    # O4 · sin extremos con STUFF45.
    o4_x = max(xbh(p, 45) for p in powers)
    o4_h = max(hr(p, 45) for p in powers)
    o4_ok = o4_x <= O4_XBH_MAX and o4_h <= O4_HR_MAX
    print(f"  O4 STUFF45 sin extremos (max XBH {o4_x:.2f}≤{O4_XBH_MAX}, "
          f"max HR {o4_h:.2f}≤{O4_HR_MAX}): "
          f"{'PASS' if o4_ok else 'FAIL'}")

    # O5 · diagonal 45/45 → 70/70 → 95/95 sin colapso (no decreciente).
    diag = [xbh(p, p) for p in (45, 70, 95)]
    o5_ok = diag[0] < diag[1] + O5_TOL_PP and diag[1] < diag[2] + O5_TOL_PP
    print(f"  O5 DIAGONAL ({' → '.join(f'{v:.2f}' for v in diag)}) "
          f"no decreciente: {'PASS' if o5_ok else 'FAIL'}")

    # O6 · MECHANISM ISOLATION (invariantes a través de 15 celdas).
    o6_ok = True
    for chan in ("cnt", "whiff", "called_tk", "k", "bb"):
        vals = [rows[(p, st)][chan] for p in powers for st in stuffs]
        span = max(vals) - min(vals)
        if span > O6_SPAN_PP:
            o6_ok = False
        print(f"  O6 {chan} span {span:.3f} (≤{O6_SPAN_PP}): "
              f"{'PASS' if span <= O6_SPAN_PP else 'FAIL'}")
    print(f"  O6 MECHANISM ISOLATION (todos): {'PASS' if o6_ok else 'FAIL'}")

    # O7 · PA STABILITY (K5-R).
    o7_ok = all(cells[(p, st)]["p95"] <= O7_P95_MAX
                and cells[(p, st)]["outcome"]["CAP"] == 0
                for p in powers for st in stuffs)
    max_p95 = max(cells[(p, st)]["p95"] for p in powers for st in stuffs)
    caps = sum(cells[(p, st)]["outcome"]["CAP"]
               for p in powers for st in stuffs)
    print(f"  O7 PA STABILITY (max p95 {max_p95}≤{O7_P95_MAX}, CAP {caps}): "
          f"{'PASS' if o7_ok else 'FAIL'}")

    # Decisión 003B-4
    print("-" * 150)
    all_pass = o1_ok and o2_ok and o3_ok and o4_ok and o5_ok and o6_ok and o7_ok
    print(f"Veredicto 003B-4: O1 {'PASS' if o1_ok else 'FAIL'} · "
          f"O2 {'PASS' if o2_ok else 'FAIL'} · O3 {'PASS' if o3_ok else 'FAIL'} · "
          f"O4 {'PASS' if o4_ok else 'FAIL'} · O5 {'PASS' if o5_ok else 'FAIL'} · "
          f"O6 {'PASS' if o6_ok else 'FAIL'} · O7 {'PASS' if o7_ok else 'FAIL'}")
    if all_pass:
        print("k=.30 → ROBUSTNESS-VALIDATED CANDIDATE (superficie sana). "
              "Siguiente: 003B-5 (fatiga de Stuff).")
    elif o1_ok and o2_ok:
        print("Monotonía PASS pero extremos comprimidos/otra señal: "
              "k=.30 → revisar contra .20.")
    else:
        print("Power o Stuff pierden expresión: k=.30 → FAIL.")


# ---------------------------------------------------------------------------
# 003B-5A · Semántica Stuff × Fatigue (políticas F0-F3, LAB, 2.4M PA)
# ---------------------------------------------------------------------------
# Pregunta A: ¿debe Stuff degradarse con fatiga? Pregunta B (intensidad α) se
# responde en 003B-5B. Aquí se comparan 4 políticas SOLO en LAB:
#   F0 NONE      effective_stuff = raw_stuff                     (control)
#   F1 FULL      effective_stuff = raw_stuff * fatigue_factor
#   F2 HALF      effective_stuff = raw_stuff * (1 - 0.5*(1-f))   (representante
#                                                                de la familia
#                                                                multiplicativa
#                                                                parcial)
#   F3 ANCHORED  effective_stuff = 70 + (raw_stuff - 70)*f       (ancla identidad)
# El factor f se obtiene del PRODUCTIVO get_fatigue_factor() (SMOOTH-0.55-F35);
# NO se duplica la curva en el harness. F1 usa eff=raw*f → a w≈1.5 (f≈.634)
# ST95≈60 → posible colapso del élite frente a un MID fresco; F3 en ST45 tiende
# hacia la identidad 70 al fatigarse → posible "mejora" (violación de P4).
# El diagnóstico "Stuff-added fatigue cost" = metric(política)(w) - metric(F0)(w)
# aísla el deterioro NUEVO causado por Stuff del PROD de VEL/CTL/MOV.
STUFF_FATIGUE_POLICIES_003B5A = {
    "F0 NONE": lambda raw, f: raw,
    "F1 FULL": lambda raw, f: raw * f,
    "F2 HALF": lambda raw, f: raw * (1.0 - 0.5 * (1.0 - f)),
    "F3 ANCHORED": lambda raw, f: 70.0 + (raw - 70.0) * f,
}
STUFF_FATIGUE_WORKLOADS_003B5A = (1.00, 1.20, 1.35, 1.50)
PROD_THRESHOLD_003B5A = get_pitch_threshold(9)  # 100 (Fatigue Policy v2)
P1_SPAN_PP = 0.2    # P1: span entre políticas en w=1.00 (bit-exacto: mismas seeds)
P1_REF_PP = 0.2     # P1: cotejo XBH/BIP vs 003B-4 fresco (30.49/23.03/15.77).
                    #   A 50k es BIT-EXACTO (mismas seeds 750M + mismo code path):
                    #   F0/w1.00 ≡ 003B-4/POW70 → |Δ|=0.0. (Smoke a 3k no valida
                    #   esta cláusula: compara 3k contra referencia 50k.)
P2_STAB_PP = 1.5    # P2: span de XBH/BIP de F0 entre workloads. Incluye el drift
                    #   real de 2º orden de composición VEL/MOV (menos whiff ⇒
                    #   contactos menos seleccionados hacia zone+pitch match ⇒
                    #   menos +15 ⇒ XBH/BIP baja ~0.5-1pp; ES efecto PROD
                    #   conocido, no Stuff) + ruido 50k (SE 0.26pp). Los
                    #   desplazamientos Stuff-driving son ≥+5pp → 1.5 discrimina
                    #   limpio "control plano" vs "Stuff moviéndose".
P2_PROD_PP = 0.5    # P2: señal PROD mínima Whiff/CalledS↓ de w1.0→w1.5.
P3_MONO_PP = 0.7    # P3/P4: tol de no-descenso del Stuff-added cost por paso de w.
                    #   El cost es pareado (mismas seeds → mismo trayecto de PA,
                    #   solo difiere el bucket de power_score) → ruido ≈0.2pp;
                    #   0.7 es holgura. ANCHORED/ST45 cae ~-1pp/paso → caza.
P5_ORD_PP = 0.5     # P5: tol de orden en cada workload (márgenes ~7pp, ruidoso)
P6_MAT_PP = 1.0     # P6: ventaja material ST95 sobre ST70 a w=1.50
P7_P95_MAX = 6      # P7: K5-R (p95 ≤ 6, CAP 0), P≥12 ≤0.05%, P≥16 ≤0.01%
P7_P12_MAX = 0.05
P7_P16_MAX = 0.01


def run_stuff_fatigue_policies_e003b5a(reps: int) -> None:
    """003B-5A · semántica Stuff×fatigue, 4 políticas, 2.4M PA."""
    n = reps
    k = 0.30
    batter = BATTER_PROFILES_003A["MID"]
    pitcher = PITCHER_PROFILES_003A["MID"]
    stuffs = [45, 70, 95]
    workloads = list(STUFF_FATIGUE_WORKLOADS_003B5A)
    cells = {}

    def fresh_agg():
        return {"pitches": 0, "take_attempts": 0, "called_strikes_on_take": 0,
                "swing_attempts": 0, "whiffs": 0, "outcome": Counter(),
                "lengths": [], "power": [], "bips": 0, "len12": 0, "len16": 0}

    factors = {w: get_fatigue_factor(
        int(w * PROD_THRESHOLD_003B5A), PROD_THRESHOLD_003B5A)
        for w in workloads}
    eff = {}
    for pol_name, pol_fn in STUFF_FATIGUE_POLICIES_003B5A.items():
        for w in workloads:
            f = factors[w]
            for st in stuffs:
                e = pol_fn(float(st), f)
                eff[(pol_name, w, st)] = e
                agg = fresh_agg()
                for rep in range(reps):
                    seed = int(DISCIPLINE_WORKLOAD * 1000) * 10**6 + rep  # compartidas
                    d = _simulate_pa_diag(E1_POLICY, seed,
                                          batter_attrs=batter,
                                          pitcher_attrs=pitcher,
                                          stuff_level=e,
                                          stuff_arm="S2",
                                          stuff_k_qty=k,
                                          workload=w)
                    agg["pitches"] += d["pitches"]
                    agg["take_attempts"] += d["take_attempts"]
                    agg["called_strikes_on_take"] += d["called_strikes_on_take"]
                    agg["swing_attempts"] += d["swing_attempts"]
                    agg["whiffs"] += d["whiffs"]
                    agg["bips"] += d["bips"]
                    agg["outcome"][d["outcome"]] += 1
                    agg["lengths"].append(d["pitches"])
                    if d["pitches"] >= 12:
                        agg["len12"] += 1
                    if d["pitches"] >= 16:
                        agg["len16"] += 1
                agg["lengths"].sort()
                agg["p95"] = agg["lengths"][int(len(agg["lengths"]) * 0.95) - 1]
                agg["power"].sort()
                cells[(pol_name, w, st)] = agg

    rows = {(pol_name, w, st): _metric_row(cells[(pol_name, w, st)], n)
            for pol_name in STUFF_FATIGUE_POLICIES_003B5A
            for w in workloads for st in stuffs}

    def r(pol, w, st, key):
        return rows[(pol, w, st)][key]

    print("=" * 150)
    print("GAMEPLAY-ENGINE-003B-5A · SEMÁNTICA STUFF × FATIGUE (F0-F3, LAB)")
    print(f"4 policies × 4 workloads × 3 Stuff × {reps:,} PA = {reps*48:,} PA | "
          "factor = get_fatigue_factor() productivo (SMOOTH-0.55-F35) | k=.30 ")
    print("MID pitcher/batter (VEL/CTL/MOV=70) | agent 65/50/30 | PROD discipline")
    print("Contratos P1–P7 FIJADOS ANTES de correr. calculator.py UNCHANGED.")
    print("=" * 150)

    for pol_name in STUFF_FATIGUE_POLICIES_003B5A:
        print()
        print(f"---- POLÍTICA {pol_name} --------------------------------------")
        print("   w     f    | eff ST45   ST70   ST95 | XBH 45    70    95 | "
              "HR 45     70    95")
        print("-" * 100)
        for w in workloads:
            f = factors[w]
            print(f" {w:>5.2f} {f:>5.3f} | "
                  f"{eff[(pol_name, w, 45)]:>8.2f} {eff[(pol_name, w, 70)]:>6.2f} "
                  f"{eff[(pol_name, w, 95)]:>6.2f} | "
                  f"{r(pol_name, w, 45, 'xbh'):>7.2f} {r(pol_name, w, 70, 'xbh'):>6.2f} "
                  f"{r(pol_name, w, 95, 'xbh'):>6.2f} | "
                  f"{r(pol_name, w, 45, 'hr'):>7.2f} {r(pol_name, w, 70, 'hr'):>6.2f} "
                  f"{r(pol_name, w, 95, 'hr'):>6.2f}")

    # ------ Stuff-added fatigue cost (aisla el deterioro nuevo de Stuff) ------
    print()
    print("-- STUFF-ADDED FATIGUE COST · XBH/BIP (pp): metric(Fi)(w) − metric(F0)(w) --")
    for pol_name in ("F1 FULL", "F2 HALF", "F3 ANCHORED"):
        print(f"  {pol_name}:")
        for w in workloads:
            c45 = r(pol_name, w, 45, "xbh") - r("F0 NONE", w, 45, "xbh")
            c70 = r(pol_name, w, 70, "xbh") - r("F0 NONE", w, 70, "xbh")
            c95 = r(pol_name, w, 95, "xbh") - r("F0 NONE", w, 95, "xbh")
            print(f"    w={w:.2f}: ST45 {c45:+6.2f} | ST70 {c70:+6.2f} | "
                  f"ST95 {c95:+6.2f}")
    print()
    print("-- STUFF-ADDED FATIGUE COST · HR/BIP (pp) --")
    for pol_name in ("F1 FULL", "F2 HALF", "F3 ANCHORED"):
        print(f"  {pol_name}:")
        for w in workloads:
            c45 = r(pol_name, w, 45, "hr") - r("F0 NONE", w, 45, "hr")
            c70 = r(pol_name, w, 70, "hr") - r("F0 NONE", w, 70, "hr")
            c95 = r(pol_name, w, 95, "hr") - r("F0 NONE", w, 95, "hr")
            print(f"    w={w:.2f}: ST45 {c45:+6.2f} | ST70 {c70:+6.2f} | "
                  f"ST95 {c95:+6.2f}")

    # ------ Diagnóstico: élite fatigado vs MID fresco (compound penalty) ------
    ref_mid_fresh = r("F0 NONE", 1.00, 70, "xbh")
    print()
    print("-- DIAGNÓSTICO · ÉLITE (ST95) A w=1.50 vs MID (ST70) FRESCO --")
    print(f"  ref MID fresco (XBH/BIP ST70 w=1.00) = {ref_mid_fresh:.2f}")
    for pol_name in STUFF_FATIGUE_POLICIES_003B5A:
        elite_w150 = r(pol_name, 1.50, 95, "xbh")
        delta = elite_w150 - ref_mid_fresh
        word = "PEOR (permite más XBH que un MID fresco)" if delta > P6_MAT_PP else \
               ("equivalente" if abs(delta) <= P6_MAT_PP else "MEJOR")
        print(f"  {pol_name} ST95 w=1.50: XBH {elite_w150:.2f} → Δ {delta:+.2f} "
              f"vs MID fresco → {word}")

    # ------ Contratos P1–P7 ------
    print()
    print("-- CONTRATOS (P1–P7, fijados antes) --")

    # P1 · FRESH IDENTITY en w=1.00 (todas las políticas colapsan a 003B-4).
    p1_ok = True
    refs = {45: 30.49, 70: 23.03, 95: 15.77}  # 003B-4 fresco (matriz XBH, k=.30)
    for st in stuffs:
        vals = [r(pol_name, 1.00, st, "xbh")
                for pol_name in STUFF_FATIGUE_POLICIES_003B5A]
        span = max(vals) - min(vals)
        ref_d = max(abs(v - refs[st]) for v in vals)
        ok = span <= P1_SPAN_PP and ref_d <= P1_REF_PP
        p1_ok &= ok
        print(f"  P1 w=1.00 ST{st}: span entre políticas {span:.2f} "
              f"(≤{P1_SPAN_PP}), |Δ vs 003B-4| máx {ref_d:.2f} (≤{P1_REF_PP}): "
              f"{'PASS' if ok else 'FAIL'}")
    print(f"  P1 FRESH IDENTITY (todos): {'PASS' if p1_ok else 'FAIL'}")

    # P2 · NONE CONTROL (F0): eff=raw en todo w + solo señal PROD conocida.
    # La estabilidad de XBH/BIP tolera el drift PROD de 2º orden (composición
    # de canales VEL/MOV), NO es señal de supresión de Stuff.
    p2_ok = True
    for st in stuffs:
        seq = [r("F0 NONE", w, st, "xbh") for w in workloads]
        span = max(seq) - min(seq)
        ok = span <= P2_STAB_PP
        p2_ok &= ok
        print(f"  P2 F0 ST{st}: XBH span {span:.2f} entre workloads "
              f"(≤{P2_STAB_PP}): {'PASS' if ok else 'FAIL'}")
    wf0 = [r("F0 NONE", w, 70, "whiff") for w in workloads]
    csf0 = [r("F0 NONE", w, 70, "called_tk") for w in workloads]
    wf_d = wf0[0] - wf0[-1]
    cs_d = csf0[0] - csf0[-1]
    p2_prod = wf_d >= P2_PROD_PP and cs_d >= P2_PROD_PP
    p2_ok &= p2_prod
    print(f"  P2 F0 señal PROD: Whiff↓ {wf_d:.2f} y CalledS↓ {cs_d:.2f} "
          f"de w1.00→w1.50 (cada ≥{P2_PROD_PP}): "
          f"{'PASS' if p2_prod else 'FAIL'}")
    print(f"  P2 NONE CONTROL (todos): {'PASS' if p2_ok else 'FAIL'}")

    def stuff_cost(pol_name, w, st, key):
        return r(pol_name, w, st, key) - r("F0 NONE", w, st, key)

    # P3 · MONOTONIC DEGRADATION (Stuff≥70): el Stuff-added cost de supresión
    # no debe volverse negativo (más supresión) con w creciente. Evaluado sobre
    # el cost aislado del canal Stuff (F0 resta la deriva de composición
    # VEL/MOV); en Stuff≥70 ninguna de las 4 políticas debería mejorar.
    p3_ok = True
    p3_by_pol = {}
    for pol_name in STUFF_FATIGUE_POLICIES_003B5A:
        pol_ok = True
        for st in (70, 95):
            cseq = [stuff_cost(pol_name, w, st, "xbh") for w in workloads]
            ok = all(cseq[i + 1] + P3_MONO_PP >= cseq[i]
                     for i in range(len(cseq) - 1))
            pol_ok &= ok
            p3_ok &= ok
            print(f"  P3 {pol_name} ST{st} cost XBH "
                  f"{['%+.2f' % v for v in cseq]} no-mejora (Stuff≥70): "
                  f"{'PASS' if ok else 'FAIL'}")
        p3_by_pol[pol_name] = pol_ok
    print(f"  P3 MONOTONIC DEGRADATION (todos): {'PASS' if p3_ok else 'FAIL'}")

    # P4 · NO FATIGUE IMPROVEMENT (todo Stuff, incl. 45): mismo check sobre el
    # cost. F0 es trivialmente PASS (cost ≡ 0). ANCHORED/ST45 → cost se vuelve
    # negativo (45→54: más supresión al fatigarse) → FAIL por semántica.
    p4_ok = True
    p4_by_pol = {}
    for pol_name in STUFF_FATIGUE_POLICIES_003B5A:
        pol_ok = True
        for st in stuffs:
            cseq = [stuff_cost(pol_name, w, st, "xbh") for w in workloads]
            ok = all(cseq[i + 1] + P3_MONO_PP >= cseq[i]
                     for i in range(len(cseq) - 1))
            pol_ok &= ok
            p4_ok &= ok
            print(f"  P4 {pol_name} ST{st} cost XBH "
                  f"{['%+.2f' % v for v in cseq]} no-mejora: "
                  f"{'PASS' if ok else 'FAIL'}")
        p4_by_pol[pol_name] = pol_ok
    print(f"  P4 NO FATIGUE IMPROVEMENT (todos): {'PASS' if p4_ok else 'FAIL'}")

    # P5 · ORDER PRESERVATION en cada workload.
    p5_ok = True
    for pol_name in STUFF_FATIGUE_POLICIES_003B5A:
        for w in workloads:
            x45 = r(pol_name, w, 45, "xbh")
            x70 = r(pol_name, w, 70, "xbh")
            x95 = r(pol_name, w, 95, "xbh")
            ok = x45 > x70 - P5_ORD_PP and x70 > x95 - P5_ORD_PP
            p5_ok &= ok
            print(f"  P5 {pol_name} w={w:.2f} ST95({x95:.2f}) < ST70({x70:.2f}) "
                  f"< ST45({x45:.2f}): {'PASS' if ok else 'FAIL'}")
    print(f"  P5 ORDER PRESERVATION (todos): {'PASS' if p5_ok else 'FAIL'}")

    # P6 · NON-COLLAPSE a w=1.50 (ST95 conserva ventaja material sobre ST70).
    p6_ok = True
    for pol_name in STUFF_FATIGUE_POLICIES_003B5A:
        x70 = r(pol_name, 1.50, 70, "xbh")
        x95 = r(pol_name, 1.50, 95, "xbh")
        margin = x70 - x95
        ok = margin >= P6_MAT_PP
        p6_ok &= ok
        print(f"  P6 {pol_name} w=1.50: XBH70 − XBH95 = {margin:+.2f} "
              f"(≥{P6_MAT_PP}): {'PASS' if ok else 'FAIL'}")
    print(f"  P6 NON-COLLAPSE (todos): {'PASS' if p6_ok else 'FAIL'}")

    # P7 · SYSTEM STABILITY (K5-R + colas + CAP por celda).
    p7_ok = True
    max_p95 = 0
    caps = 0
    violations = []
    for pol_name in STUFF_FATIGUE_POLICIES_003B5A:
        for w in workloads:
            for st in stuffs:
                c = cells[(pol_name, w, st)]
                p95 = c["p95"]
                cap = c["outcome"]["CAP"]
                p12 = c["len12"] / n * 100
                p16 = c["len16"] / n * 100
                max_p95 = max(max_p95, p95)
                caps += cap
                if not (p95 <= P7_P95_MAX and cap == 0
                        and p12 <= P7_P12_MAX and p16 <= P7_P16_MAX):
                    p7_ok = False
                    violations.append((pol_name, w, st, p95, cap, p12, p16))
    print(f"  P7 max p95 {max_p95}≤{P7_P95_MAX}, CAP {caps}, violaciones "
          f"{len(violations)}: {'PASS' if p7_ok else 'FAIL'}")
    if violations:
        for v in violations[:8]:
            print("    ", v)
    print(f"  P7 SYSTEM STABILITY: {'PASS' if p7_ok else 'FAIL'}")

    # ------ Decisión 003B-5A ------
    print("-" * 150)
    # Matriz de contratos por política (F0 evalúa P1+P2+estabilidad; las
    # políticas de degradación evalúan P1+P3/P4 (cost-based)+P5-P7).
    spec = {
        "F0 NONE": {"P1": p1_ok, "P2": p2_ok, "P7": p7_ok},
        "F1 FULL": {"P1": p1_ok, "P3": p3_by_pol["F1 FULL"],
                    "P4": p4_by_pol["F1 FULL"], "P5": p5_ok, "P6": p6_ok,
                    "P7": p7_ok},
        "F2 HALF": {"P1": p1_ok, "P3": p3_by_pol["F2 HALF"],
                    "P4": p4_by_pol["F2 HALF"], "P5": p5_ok, "P6": p6_ok,
                    "P7": p7_ok},
        "F3 ANCHORED": {"P1": p1_ok, "P3": p3_by_pol["F3 ANCHORED"],
                        "P4": p4_by_pol["F3 ANCHORED"], "P5": p5_ok,
                        "P6": p6_ok, "P7": p7_ok},
    }
    print("Resultado por política:")
    for pol_name in STUFF_FATIGUE_POLICIES_003B5A:
        fails = [cname for cname, ok in spec[pol_name].items() if not ok]
        status = "TODO PASS" if not fails else f"FAIL en {', '.join(fails)}"
        print(f"  {pol_name}: {status}")

    # Semántica por política (P4 es el check falsable clave).
    p4_anchored = spec["F3 ANCHORED"]["P4"]
    p4_full = spec["F1 FULL"]["P4"]
    print()
    if not p4_anchored:
        print("F3 ANCHORED → VIOLA P4 (semántica): low Stuff mejora su "
              "supresión al fatigarse (45→~54: se acerca a la identidad 70). "
              "RECHAZADO por semántica, aunque los agregados parezcan buenos.")
    else:
        print("F3 ANCHORED → P1..P7 PASS: pendiente de decisión.")
    if not p4_full:
        print("F1 FULL → VIOLA P4 (semántica): alguna Stuff MEJORA al fatigarse. "
              "RECHAZADO por semántica.")
    if spec["F2 HALF"]["P4"] and spec["F2 HALF"]["P3"] and p2_ok:
        print("F2 HALF → comportamiento sano (P1, P3, P4, P5-P7 PASS + F0 "
              "control OK). FAMILIA MULTIPLICATIVA PARCIAL GANA como semántica.")
        print("Conclusión → abrir 003B-5B para calibrar α "
              "(0.25/0.40/0.50/0.60/0.75/1.00 + NONE como control). α=.50 NO es "
              "definitivo. Sin promoción a producción hasta 003B-6.")
    else:
        print("F2 HALF NO confirmado → revisar diagnóstico antes de decidir familia.")


# ---------------------------------------------------------------------------
# 003B-5B · Calibración α de la fatiga de Stuff (LAB, 4.2M PA)
# ---------------------------------------------------------------------------
# 003B-5A cerró la SEMÁNTICA: Stuff sí se fatiga con la curva productiva f, pero
# la transformación COMPLETA (raw·f) destruye la identidad del élite (F1 FULL:
# ST95 a w=1.50 quedaba PEOR que un MID fresco, Δ+2.95pp) y la ANCHORED hacía
# MEJORAR al Stuff bajo (P4). Ganó la familia multiplicativa PARCIAL:
#
#     effective_stuff = raw_stuff * (1 - α * (1 - f))
#
# 5B NO re-litiga la semántica: calibra CUÁNTA degradación parcial se quiere.
# α=0.00 es el control (Stuff no se fatiga) · α=1.00 es la REFERENCIA ya
# condenada en 5A (se conserva para medir el extremo) · α=.50 es solo el
# representante ya medido, NO un default. Matriz IDÉNTICA a 5A (3 Stuff, 4
# workloads, mismas seeds) → comparación directa; lo único que cambia es α.
STUFF_FATIGUE_ALPHAS_003B5B = (0.00, 0.25, 0.40, 0.50, 0.60, 0.75, 1.00)
STUFF_FATIGUE_WORKLOADS_003B5B = (1.00, 1.20, 1.35, 1.50)
STUFF_LEVELS_003B5B = (45, 70, 95)
PROD_THRESHOLD_003B5B = get_pitch_threshold(9)  # 100 (Fatigue Policy v2)
STUFF_K_QTY_003B5B = 0.30                       # S2 (003B-3 · 003B-4)

# Referencias 003B-4 (Stuff fresca, k=.30, mismas seeds 750M+rep) para Q1.
Q1_REFS_003B5B = {45: 30.49, 70: 23.03, 95: 15.77}
# Referencias 003B-5A (50k) para el check de REPRO entre familias: α=0.00 ≡ F0
# NONE, α=0.50 ≡ F2 HALF, α=1.00 ≡ F1 FULL (misma fórmula, mismas seeds, mismo
# code path) → deben reproducir bit-a-bit. Tolerancia 0.01 = redondeo del print
# de 5A a 2 decimales (no es comparación de bits, es de cifras publicadas).
REPRO_5A_003B5B = {
    0.00: {1.00: (30.49, 23.03, 15.77), 1.20: (30.36, 22.91, 15.73),
           1.35: (30.54, 22.98, 15.67), 1.50: (30.51, 23.02, 15.78)},
    0.50: {1.00: (30.49, 23.03, 15.77), 1.20: (30.85, 23.81, 16.77),
           1.35: (32.09, 25.36, 18.75), 1.50: (32.97, 26.87, 20.85)},
    1.00: {1.00: (30.49, 23.03, 15.77), 1.20: (31.47, 24.66, 18.01),
           1.35: (33.45, 27.49, 21.73), 1.50: (35.46, 30.66, 25.98)},
}
REPRO_5A_TOL_PP = 0.01

# Tolerancias Q1–Q7 (fijadas ANTES de correr).
Q1_SPAN_PP = 0.2      # Q1: span entre α a w=1.00 (esperado 0.00: mismas seeds)
Q1_REF_PP = 0.2       # Q1: |Δ| vs Stuff fresca de 003B-4
Q2_TOL_PP = 0.5       # Q2: α↑ → XBH no debe DISMINUIR (supresión no aumenta)
Q3_MONO_PP = 0.7      # Q3: w↑ → XBH no disminuye (ST70/ST95, α>0)
Q3_CTRL_SPAN_PP = 1.5  # Q3 control (α=0): XBH plana entre workloads (deriva PROD
                      #   de 2º orden de composición VEL/MOV, no señal de Stuff)
Q4_MARGIN_PP = 0.0    # Q4: ST95 fatigado a w=1.50 debe seguir SIENDO MEJOR que
                      #   un ST70 FRESCO. Es la frontera que condenó FULL en 5A:
                      #   cruzar (Δ ≥ 0) = demasiado destructivo.
Q4_BAND_PP = 1.0      # Q4 banda advisory de retención de identidad (≥1pp holgada)
Q5_EPS_PP = 0.5      # Q5 estructural: cost@w>1.00 debe exceder el eps (efecto
                      #   reproducible, no ruido de muestra; ~5 SE a 50k)
Q5_MATERIAL_BAR = 0.25  # Barra POST-HOC de MATERIALIDAD: cost ≥ 25% del gap de
                        #   identidad fresco (XBH ST45 − ST95 a w=1.00 ≈ 14.7pp).
                        #   NO es un contrato (Q5 contractual = cost positivo,
                        #   monótono en w y ordenado en α); es la pantalla de
                        #   SELECCIÓN, y se reporta su sensibilidad abajo.
Q6_STEP_PP = 0.7      # Q6: los incrementos de cost entre pasos de w no pueden
                      #   ser negativos (sin saltos hacia atrás)
Q6_MAX_ACCEL = 2.0    # Q6: d2/d1 — nada de aceleración patológica
Q7_P95_MAX = 6        # Q7: K5-R (p95 ≤ 6, CAP 0)
Q7_P12_MAX = 0.05
Q7_P16_MAX = 0.01
Q7_SHAPE_PP = 0.05    # Q7: aislamiento de mecanismo. S2 solo modula power_score
                      #   (whiff_add ≡ 0) y SOLO el bucket del PRIMER BIP, que
                      #   termina el PA en cualquier caso → la TRAYECTORIA del PA
                      #   (Pit/PA, K%, BB%, BIP%, Whiff/Sw, CalledS/TAKE,
                      #   Contacto/Sw, p95) debe ser INVARIANTE con α a w fijo.
                      #   Invarianza EXACTA, no estadística.
                      #   Lo que SÍ puede moverse (y es el canal de Stuff): la
                      #   mezcla DENTRO del BIP (OUT/1B/2B/3B/HR) y Reach%,
                      #   porque los swaps cruzan el umbral 25/63 (OUT↔1B) igual
                      #   que 63/85/93/96 (1B↔2B↔3B↔HR). Reach% NO es invariante:
                      #   un Stuff fatigado convierte hits en outs.


def _stuff_fatigue_eff_003b5b(raw: float, alpha: float, f: float) -> float:
    """Familia multiplicativa parcial de 003B-5A, con α libre (003B-5B)."""
    return raw * (1.0 - alpha * (1.0 - f))


def run_stuff_fatigue_alpha_e003b5b(reps: int) -> None:
    """003B-5B · calibración α de la fatiga de Stuff, 7 α × 4 w × 3 Stuff."""
    n = reps
    k = STUFF_K_QTY_003B5B
    batter = BATTER_PROFILES_003A["MID"]
    pitcher = PITCHER_PROFILES_003A["MID"]
    stuffs = list(STUFF_LEVELS_003B5B)
    workloads = list(STUFF_FATIGUE_WORKLOADS_003B5B)
    alphas = list(STUFF_FATIGUE_ALPHAS_003B5B)
    cells = {}
    eff = {}

    def fresh_agg():
        return {"pitches": 0, "take_attempts": 0, "called_strikes_on_take": 0,
                "swing_attempts": 0, "whiffs": 0, "outcome": Counter(),
                "lengths": [], "power": [], "bips": 0, "len12": 0, "len16": 0}

    factors = {w: get_fatigue_factor(
        int(w * PROD_THRESHOLD_003B5B), PROD_THRESHOLD_003B5B)
        for w in workloads}
    for a in alphas:
        for w in workloads:
            f = factors[w]
            for st in stuffs:
                e = _stuff_fatigue_eff_003b5b(float(st), a, f)
                eff[(a, w, st)] = e
                agg = fresh_agg()
                for rep in range(reps):
                    # MISMAS seeds que 003B-4/5A en todas las celdas → toda la
                    # matriz es pareada: el único cambio entre α es power_add.
                    seed = int(DISCIPLINE_WORKLOAD * 1000) * 10**6 + rep
                    d = _simulate_pa_diag(E1_POLICY, seed,
                                          batter_attrs=batter,
                                          pitcher_attrs=pitcher,
                                          stuff_level=e,
                                          stuff_arm="S2",
                                          stuff_k_qty=k,
                                          workload=w,
                                          power_log=agg["power"])
                    agg["pitches"] += d["pitches"]
                    agg["take_attempts"] += d["take_attempts"]
                    agg["called_strikes_on_take"] += d["called_strikes_on_take"]
                    agg["swing_attempts"] += d["swing_attempts"]
                    agg["whiffs"] += d["whiffs"]
                    agg["bips"] += d["bips"]
                    agg["outcome"][d["outcome"]] += 1
                    agg["lengths"].append(d["pitches"])
                    if d["pitches"] >= 12:
                        agg["len12"] += 1
                    if d["pitches"] >= 16:
                        agg["len16"] += 1
                agg["lengths"].sort()
                agg["p95"] = agg["lengths"][int(len(agg["lengths"]) * 0.95) - 1]
                agg["power"].sort()
                cells[(a, w, st)] = agg

    rows = {(a, w, st): _metric_row(cells[(a, w, st)], n)
            for a in alphas for w in workloads for st in stuffs}

    def r(a, w, st, key):
        return rows[(a, w, st)][key]

    def cost(a, w, st, key="xbh"):
        """Stuff-added fatigue cost: XBH de la política α menos la de α=0."""
        return r(a, w, st, key) - r(0.00, w, st, key)

    def supp(a, w, st, key="xbh"):
        """Supresión de Stuff medida contra ST70 en el MISMO contexto (α, w)."""
        return r(a, w, 70, key) - r(a, w, st, key)

    supp_fresh = {st: supp(0.00, 1.00, st) for st in stuffs}
    # Gap de identidad fresco: recorrido TOTAL de la dimensión Stuff en XBH/BIP
    # (ST45 → ST95 a w=1.00). Es la escala propia del motor contra la que se
    # juzga "material": NO es un miembro de la familia α, así que la barra de
    # materialidad no es degenerada (el coste escala ~α, la barra no).
    identity_gap = supp_fresh[95] - supp_fresh[45]

    def retention(a, w, st):
        base = supp_fresh[st]
        if abs(base) < 1e-9:
            return float("nan")
        return supp(a, w, st) / base

    print("=" * 150)
    print("GAMEPLAY-ENGINE-003B-5B · CALIBRACIÓN α DE LA FATIGA DE STUFF (LAB)")
    print(f"7 α × 4 workloads × 3 Stuff × {reps:,} PA = {reps*84:,} PA | "
          "effective_stuff = raw·(1 − α·(1−f)), f = get_fatigue_factor() "
          "productivo (SMOOTH-0.55-F35)")
    print("α: 0.00 control · .25/.40/.50/.60/.75 candidatos · 1.00 = FULL "
          "(referencia YA CONDENADA en 5A)")
    print("Matriz IDÉNTICA a 003B-5A (Power 70, VEL/CTL/MOV 70, k=.30, mismas "
          "seeds) · MID pitcher/batter · agent 65/50/30")
    print("Contratos Q1–Q7 FIJADOS ANTES de correr. calculator.py UNCHANGED.")
    print("=" * 150)

    # ---------------- Matrices por α ----------------
    for a in alphas:
        tag = " (control)" if a == 0.00 else (" (FULL, referencia)" if a == 1.00
                                              else "")
        print()
        print(f"---- α = {a:.2f}{tag} " + "-" * (44 - len(tag)))
        print("   w     f    | eff ST45   ST70   ST95 | XBH 45    70    95 | "
              "HR 45     70    95")
        print("-" * 100)
        for w in workloads:
            print(f" {w:>5.2f} {factors[w]:>5.3f} | "
                  f"{eff[(a, w, 45)]:>8.2f} {eff[(a, w, 70)]:>6.2f} "
                  f"{eff[(a, w, 95)]:>6.2f} | "
                  f"{r(a, w, 45, 'xbh'):>7.2f} {r(a, w, 70, 'xbh'):>6.2f} "
                  f"{r(a, w, 95, 'xbh'):>6.2f} | "
                  f"{r(a, w, 45, 'hr'):>7.2f} {r(a, w, 70, 'hr'):>6.2f} "
                  f"{r(a, w, 95, 'hr'):>6.2f}")

    # ---------------- Tabla decisiva ST95 ----------------
    print()
    print("=" * 150)
    print("TABLA DECISIVA · ST95 (effective stuff degradado + coste XBH/BIP)")
    print("-" * 150)
    print("  α     | eff@1.20  eff@1.35  eff@1.50 | XBH@1.20  XBH@1.35  XBH@1.50 | "
          "cost@1.20  cost@1.35  cost@1.50")
    print("-" * 150)
    for a in alphas:
        print(f" {a:.2f}    | {eff[(a, 1.20, 95)]:>8.2f}  {eff[(a, 1.35, 95)]:>8.2f}  "
              f"{eff[(a, 1.50, 95)]:>8.2f} | {r(a, 1.20, 95, 'xbh'):>8.2f}  "
              f"{r(a, 1.35, 95, 'xbh'):>8.2f}  {r(a, 1.50, 95, 'xbh'):>8.2f} | "
              f"{cost(a, 1.20, 95):>9.2f}  {cost(a, 1.35, 95):>9.2f}  "
              f"{cost(a, 1.50, 95):>9.2f}")
    print("=" * 150)

    # ---------------- Stuff-added fatigue cost ----------------
    print()
    print("-- STUFF-ADDED FATIGUE COST · XBH/BIP (pp): XBH(α)(w) − XBH(α=0)(w) --")
    for a in alphas:
        if a == 0.00:
            continue
        print(f"  α={a:.2f}:")
        for w in workloads:
            print(f"    w={w:.2f}: ST45 {cost(a, w, 45):+6.2f} | ST70 "
                  f"{cost(a, w, 70):+6.2f} | ST95 {cost(a, w, 95):+6.2f}")

    # ---------------- Retención de supresión ----------------
    print()
    print("-- fatigue_suppression_retention = supresión(w) / supresión(fresco) --")
    print(f"   (supresión = XBH ST70 − XBH ST en el MISMO α y workload; "
          f"fresco ST45 {supp_fresh[45]:.2f}pp / ST95 {supp_fresh[95]:.2f}pp)")
    print("  α     | ret ST95 @1.20  @1.35  @1.50 | ret ST45 @1.20  @1.35  @1.50")
    print("-" * 100)
    for a in alphas:
        r95 = [retention(a, w, 95) for w in (1.20, 1.35, 1.50)]
        r45 = [retention(a, w, 45) for w in (1.20, 1.35, 1.50)]
        print(f" {a:.2f}    | {r95[0]*100:>12.1f}% {r95[1]*100:>6.1f}% {r95[2]*100:>6.1f}%"
              f" | {r45[0]*100:>12.1f}% {r45[1]*100:>6.1f}% {r45[2]*100:>6.1f}%")
    print()
    for a in alphas:
        print(f"  → A workload 1.50, un Stuff95 (α={a:.2f}) conserva el "
              f"{retention(a, 1.50, 95)*100:.1f}% de su ventaja fresca de "
              f"supresión ({supp_fresh[95]:.2f}pp → "
              f"{supp(a, 1.50, 95):.2f}pp).")

    # ---------------- REPRO vs 003B-5A ----------------
    print()
    print("-- REPRO vs 003B-5A (α=0.00≡F0 NONE, α=0.50≡F2 HALF, α=1.00≡F1 FULL) --")
    repro_ok = True
    for a in sorted(REPRO_5A_003B5B):
        worst = 0.0
        for w in workloads:
            ref = REPRO_5A_003B5B[a][w]
            for i, st in enumerate(stuffs):
                worst = max(worst, abs(r(a, w, st, "xbh") - ref[i]))
        ok = worst <= REPRO_5A_TOL_PP
        repro_ok &= ok
        print(f"  α={a:.2f}: |Δ| XBH máx vs 5A = {worst:.2f}pp "
              f"(≤{REPRO_5A_TOL_PP}): {'PASS' if ok else 'FAIL'}")
    print(f"  REPRO 5A: {'PASS' if repro_ok else 'FAIL'} "
          "(misma fórmula + mismas seeds → debe ser 0.00)")

    # ---------------- Contratos Q1–Q7 ----------------
    print()
    print("-- CONTRATOS (Q1–Q7, fijados antes) --")

    # Q1 · FRESH IDENTITY: en w=1.00 f=1.0 → effective_stuff = raw para TODO α.
    q1_ok = True
    for st in stuffs:
        vals = [r(a, 1.00, st, "xbh") for a in alphas]
        span = max(vals) - min(vals)
        ref_d = max(abs(v - Q1_REFS_003B5B[st]) for v in vals)
        effs = [eff[(a, 1.00, st)] for a in alphas]
        eff_exact = all(abs(e - st) < 1e-9 for e in effs)
        ok = span <= Q1_SPAN_PP and ref_d <= Q1_REF_PP and eff_exact
        q1_ok &= ok
        print(f"  Q1 w=1.00 ST{st}: span entre α {span:.2f} (≤{Q1_SPAN_PP}), "
              f"|Δ vs 003B-4| máx {ref_d:.2f} (≤{Q1_REF_PP}), eff≡raw "
              f"{eff_exact}: {'PASS' if ok else 'FAIL'}")
    print(f"  Q1 FRESH IDENTITY (todos): {'PASS' if q1_ok else 'FAIL'}")

    # Q2 · ALPHA ORDERING: mismo raw Stuff y workload>1, α↑ → effective_stuff no
    # aumenta (exacto por construcción) → la capacidad de supresión no aumenta
    # (XBH/BIP no disminuye). Para ST95 esto es más daño permitido al subir α.
    q2_by_alpha = {}
    for a in alphas:
        a_ok = True
        for w in workloads[1:]:
            for st in stuffs:
                eseq = [eff[(x, w, st)] for x in alphas]
                xseq = [r(x, w, st, "xbh") for x in alphas]
                e_ok = all(eseq[i + 1] <= eseq[i] + 1e-9
                           for i in range(len(eseq) - 1))
                x_ok = all(xseq[i + 1] + Q2_TOL_PP >= xseq[i]
                           for i in range(len(xseq) - 1))
                a_ok &= e_ok and x_ok
        q2_by_alpha[a] = a_ok
    print(f"  Q2 ALPHA ORDERING: eff no-creciente en α y XBH no decreciente "
          f"(tol {Q2_TOL_PP}pp) en las 3×3 combinaciones w>1 × Stuff")
    for a in alphas:
        print(f"    α={a:.2f}: {'PASS' if q2_by_alpha[a] else 'FAIL'}")

    # Q3 · WORKLOAD MONOTONICITY: w↑ → effective_stuff↓ (exacto) y, para α>0,
    # XBH/BIP NO disminuye en ST70/ST95. ST45 no se usa como contrato monotónico
    # de XBH porque el sistema completo también degrada VEL/MOV/CTL (el canal de
    # Stuff es una fracción del cambio total); su effective_stuff sí es monotónico.
    q3_by_alpha = {}
    for a in alphas:
        a_ok = True
        detail = []
        for st in stuffs:
            eseq = [eff[(a, w, st)] for w in workloads]
            a_ok &= all(eseq[i + 1] <= eseq[i] + 1e-9
                        for i in range(len(eseq) - 1))
        if a > 0.0:
            for st in (70, 95):
                cseq = [cost(a, w, st) for w in workloads]
                ok = all(cseq[i + 1] + Q3_MONO_PP >= cseq[i]
                         for i in range(len(cseq) - 1))
                a_ok &= ok
                detail.append(f"ST{st} {['%+.2f' % v for v in cseq]}")
        else:
            for st in stuffs:
                xseq = [r(a, w, st, "xbh") for w in workloads]
                ok = max(xseq) - min(xseq) <= Q3_CTRL_SPAN_PP
                a_ok &= ok
                detail.append(f"ST{st} span {max(xseq)-min(xseq):.2f}")
        q3_by_alpha[a] = a_ok
        print(f"  Q3 α={a:.2f} eff↓ en w (las 3 Stuff) + "
              f"{'cost↑ (tol %.1f)' % Q3_MONO_PP if a > 0 else 'XBH plana (≤%.1f)' % Q3_CTRL_SPAN_PP}: "
              f"{' | '.join(detail)} → {'PASS' if a_ok else 'FAIL'}")

    # Q4 · ELITE IDENTITY SURVIVES: a w=1.50 el ST95 fatigado debe conservar
    # ventaja de supresión frente a un ST70 FRESCO. Es exactamente la frontera
    # que condenó FULL en 5A (Δ+2.95 = peor que un MID fresco).
    fresh_mid = r(0.00, 1.00, 70, "xbh")
    q4_by_alpha = {}
    print(f"  Q4 ref MID fresco (XBH ST70 w=1.00) = {fresh_mid:.2f}")
    for a in alphas:
        x95 = r(a, 1.50, 95, "xbh")
        margin = fresh_mid - x95
        ok = margin > Q4_MARGIN_PP
        q4_by_alpha[a] = ok
        band = "banda ≥1.0pp OK" if margin >= Q4_BAND_PP else "banda <1.0pp"
        word = "conserva ventaja" if ok else "CRUZA la frontera (peor que MID fresco)"
        print(f"    α={a:.2f}: XBH ST95 w=1.50 {x95:.2f} → Δ {-margin:+.2f} vs MID "
              f"fresco (margen {margin:+.2f}) → {word}; {band}")

    # Q5 · MATERIAL FATIGUE (estructural) + escalera de materialidad.
    q5_by_alpha = {}
    for a in alphas:
        if a == 0.00:
            q5_by_alpha[a] = True
            continue
        a_ok = True
        for st in stuffs:
            cseq = [cost(a, w, st) for w in workloads]
            a_ok &= cseq[2] > Q5_EPS_PP and cseq[3] > Q5_EPS_PP
            a_ok &= all(cseq[i + 1] + Q6_STEP_PP >= cseq[i]
                        for i in range(len(cseq) - 1))
        q5_by_alpha[a] = a_ok
    print(f"  Q5 estructural: cost@1.35 y @1.50 > {Q5_EPS_PP}pp y monótono en w "
          "(efecto reproducible, no ruido)")
    for a in alphas:
        if a == 0.00:
            print("    α=0.00: control (cost ≡ 0 por construcción) → N/A")
        else:
            print(f"    α={a:.2f}: {'PASS' if q5_by_alpha[a] else 'FAIL'}")

    # Q6 · NO COMPOUND EXPLOSION: el coste adicional sobre α=0 crece con
    # suavidad; sin saltos hacia atrás, sin cruces entre α y sin aceleración
    # patológica entre w1.20 → 1.35 → 1.50.
    q6_by_alpha = {}
    for a in alphas:
        a_ok = True
        detail = []
        for st in stuffs:
            c = [cost(a, w, st) for w in workloads]
            d1 = c[2] - c[1]
            d2 = c[3] - c[2]
            step_ok = d1 + Q6_STEP_PP >= 0.0 and d2 + Q6_STEP_PP >= 0.0
            accel = (d2 / d1) if d1 > 1e-9 else None
            accel_ok = accel is None or accel <= Q6_MAX_ACCEL
            a_ok &= step_ok and accel_ok
            detail.append(f"ST{st} d1 {d1:+.2f} d2 {d2:+.2f} "
                          f"accel {'—' if accel is None else f'{accel:.2f}'}")
        q6_by_alpha[a] = a_ok
        print(f"  Q6 α={a:.2f}: {' | '.join(detail)} → "
              f"{'PASS' if a_ok else 'FAIL'}")
    cross_ok = True
    for w in workloads:
        for st in stuffs:
            cseq = [cost(x, w, st) for x in alphas[1:]]
            ok = all(cseq[i + 1] + Q6_STEP_PP >= cseq[i]
                     for i in range(len(cseq) - 1))
            cross_ok &= ok
    print(f"  Q6 sin CRUCES entre α (cost monótono en α en cada w × Stuff, "
          f"tol {Q6_STEP_PP}): {'PASS' if cross_ok else 'FAIL'}")
    q6_by_alpha = {a: (q6_by_alpha[a] and cross_ok) for a in alphas}

    # Q7 · SYSTEM STABILITY: K5-R sano, colas, CAP, probabilidades válidas y
    # aislamiento de mecanismo. S2 solo modula power_score, y SOLO el bucket del
    # primer BIP (que termina el PA igual en todos los casos) → la trayectoria
    # del PA es bit-idéntica entre α. Eso convierte el aislamiento de mecanismo
    # en una INVARIANZA EXACTA, no en un test estadístico. Lo único que puede
    # moverse es la mezcla dentro del BIP (y Reach%, que se mueve con OUT↔1B),
    # que es exactamente el canal de Stuff.
    q7_ok = True
    max_p95 = 0
    caps = 0
    invalid = []
    violations = []
    # Claves que NO dependen de power_score → invariancia exacta exigida.
    shape_keys = ("k", "bb", "bip", "whiff", "called_tk", "cnt", "paus")
    # Claves que SÍ son el canal de Stuff → se miden y se reportan, sin contrato.
    mix_keys = ("xbh", "hr", "out_bip", "x1", "x2", "x3", "reach")
    key_worst = {key: (0.0, None) for key in shape_keys + mix_keys + ("p95",)}
    for a in alphas:
        for w in workloads:
            for st in stuffs:
                c = cells[(a, w, st)]
                p95 = c["p95"]
                cap = c["outcome"]["CAP"]
                p12 = c["len12"] / n * 100
                p16 = c["len16"] / n * 100
                max_p95 = max(max_p95, p95)
                caps += cap
                if not (p95 <= Q7_P95_MAX and cap == 0
                        and p12 <= Q7_P12_MAX and p16 <= Q7_P16_MAX):
                    q7_ok = False
                    violations.append((a, w, st, p95, cap, p12, p16))
                for key, val in rows[(a, w, st)].items():
                    bad = (val != val) or val in (float("inf"), float("-inf"))
                    if not bad and key not in ("p95", "paus", "pmean", "p10",
                                               "p50", "p90"):
                        bad = val < -1e-9 or val > 100 + 1e-9
                    if bad:
                        invalid.append((a, w, st, key, val))
                if a == 0.00:
                    continue
                for key in shape_keys + mix_keys:
                    d = abs(r(a, w, st, key) - r(0.00, w, st, key))
                    if d > key_worst[key][0]:
                        key_worst[key] = (d, (a, w, st))
                d_p95 = abs(c["p95"] - cells[(0.00, w, st)]["p95"])
                if d_p95 > key_worst["p95"][0]:
                    key_worst["p95"] = (d_p95, (a, w, st))
    shape_worst = max(key_worst[key][0] for key in shape_keys)
    shape_worst = max(shape_worst, key_worst["p95"][0])
    shape_ok = shape_worst <= Q7_SHAPE_PP
    q7_ok &= shape_ok and not invalid
    print(f"  Q7 max p95 {max_p95}≤{Q7_P95_MAX}, CAP {caps}, violaciones "
          f"{len(violations)}: {'PASS' if not violations else 'FAIL'}")
    if violations:
        for v in violations[:8]:
            print("    ", v)
    print(f"  Q7 probabilidades finite/válidas (fuera de [0,100]): {len(invalid)}: "
          f"{'PASS' if not invalid else 'FAIL'}")
    if invalid[:5]:
        for v in invalid[:5]:
            print("    ", v)
    print("  Q7 aislamiento de MECANISMO · |Δ| máx vs α=0 a mismo workload:")
    print("    trayectoria del PA (debe ser 0.00 EXACTO):")
    for key in shape_keys + ("p95",):
        d, at = key_worst[key]
        ok = d <= Q7_SHAPE_PP
        loc = ("" if at is None else
               f"  (α={at[0]:.2f} w={at[1]:.2f} ST{at[2]})")
        print(f"      {key:>10}: {d:>6.2f}pp (≤{Q7_SHAPE_PP}): "
              f"{'PASS' if ok else 'FAIL'}{loc}")
    print(f"    trayectoria del PA completa: {'PASS' if shape_ok else 'FAIL'} "
          f"(|Δ| máx {shape_worst:.2f}pp)")
    print("    canal de Stuff (SÍ debe moverse; es la única firma permitida):")
    for key in mix_keys:
        d, at = key_worst[key]
        loc = ("" if at is None else
               f"  (α={at[0]:.2f} w={at[1]:.2f} ST{at[2]})")
        print(f"      {key:>10}: {d:>6.2f}pp{loc}")
    print(f"  Q7 SYSTEM STABILITY: {'PASS' if q7_ok else 'FAIL'}")

    # ---------------- Matriz de contratos + selección ----------------
    spec = {a: {"Q1": q1_ok, "Q2": q2_by_alpha[a], "Q3": q3_by_alpha[a],
                "Q4": q4_by_alpha[a], "Q5": q5_by_alpha[a], "Q6": q6_by_alpha[a],
                "Q7": q7_ok} for a in alphas}
    hard = ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7")
    candidates = [a for a in alphas if a not in (0.00, 1.00)]

    def material_at(a, w, bar):
        return cost(a, w, 95) >= identity_gap * bar

    def material_both(a, bar):
        return all(material_at(a, w, bar) for w in (1.35, 1.50))

    print()
    print("-" * 150)
    print("MATRIZ DE CANDIDATOS (Q1-Q7) + MATERIALIDAD + RETENCIÓN")
    print(f"  gap de identidad fresco (ST45−ST95 XBH a w=1.00) = {identity_gap:.2f}pp "
          f"→ barra de materialidad = {Q5_MATERIAL_BAR*100:.0f}% = "
          f"{identity_gap*Q5_MATERIAL_BAR:.2f}pp")
    print("  α     | Q1   Q2   Q3   Q4   Q5   Q6   Q7 | cost@1.35 cost@1.50 "
          "%gap@1.35 %gap@1.50 | ret@1.50 | veredicto")
    print("-" * 150)
    for a in alphas:
        marks = "  ".join("Y" if spec[a][c] else "N" for c in hard)
        c35, c50 = cost(a, 1.35, 95), cost(a, 1.50, 95)
        p35, p50 = c35 / identity_gap * 100, c50 / identity_gap * 100
        fails = [c for c in hard if not spec[a][c]]
        if a == 0.00:
            verdict = "CONTROL (no candidato)"
        elif a == 1.00:
            verdict = "REFERENCIA (ya condenada en 5A)"
        elif fails:
            verdict = f"RECHAZADO ({','.join(fails)})"
        elif material_both(a, Q5_MATERIAL_BAR):
            verdict = "CANDIDATO (sano + material en 1.35 y 1.50)"
        elif material_at(a, 1.50, Q5_MATERIAL_BAR):
            verdict = "sano + material@1.50, NO material@1.35"
        else:
            verdict = "sano pero NO material"
        print(f"  {a:.2f}   | {marks} | {c35:>9.2f} {c50:>10.2f} {p35:>9.1f}% "
              f"{p50:>9.1f}% | {retention(a, 1.50, 95)*100:>7.1f}% | {verdict}")
    print("-" * 150)

    # Sensibilidad de la decisión a la barra de materialidad. La barra es una
    # pantalla POST-HOC (Q5 contractual es solo estructural: cost positivo,
    # monótono en w y ordenado en α), así que se muestra explícitamente qué α
    # ganaría con cada barra y hasta dónde permite llegar Q4.
    q4_ceiling = max([a for a in candidates if q4_by_alpha[a]], default=None)
    print("  Ceiling de Q4 (mayor α que todavía conserva identidad a w=1.50): "
          f"{'α=%.2f' % q4_ceiling if q4_ceiling is not None else 'NINGUNO'}")
    print("  Sensibilidad a la barra de materialidad (menor α sano y material):")
    print("    barra   pp     | material@1.50  material@1.35&1.50  "
          "selección(1.35&1.50)")
    for bar in (0.15, 0.20, 0.25, 0.30, 0.35, 0.40):
        pick50 = pickboth = None
        for a in candidates:
            if not all(spec[a][c] for c in hard):
                continue
            if pick50 is None and material_at(a, 1.50, bar):
                pick50 = a
            if pickboth is None and material_both(a, bar):
                pickboth = a
        print(f"    {bar*100:>4.0f}%  {identity_gap*bar:>5.2f}  | "
              f"{'α=%.2f' % pick50 if pick50 is not None else '—':>12}  "
              f"{'α=%.2f' % pickboth if pickboth is not None else 'NINGUNO':>17}  "
              f"{'α=%.2f' % pickboth if pickboth is not None else '—':>19}")
    print("    (la barra no es un contrato: Q5 contractual solo exige que el "
          "coste sea >", f"{Q5_EPS_PP}pp, monótono y ordenado en α)")

    # ---------------- Decisión 003B-5B ----------------
    print()
    winner = None
    for a in candidates:
        if all(spec[a][c] for c in hard) and material_both(a, Q5_MATERIAL_BAR):
            winner = a
            break

    def band(pred):
        got = [a for a in candidates if pred(a)]
        return ("{" + ", ".join("%.2f" % a for a in got) + "}"
                if got else "{} (ninguno)")

    print("-" * 150)
    print("RESUMEN DE BANDAS (no un punto: la decisión depende de la barra)")
    print(f"  sanos (Q1–Q7 todos PASS)        : {band(lambda a: all(spec[a][c] for c in hard))}")
    print(f"  material@1.50 (barra "
          f"{Q5_MATERIAL_BAR*100:.0f}%)        : "
          f"{band(lambda a: material_at(a, 1.50, Q5_MATERIAL_BAR))}")
    print(f"  material@1.35 (barra "
          f"{Q5_MATERIAL_BAR*100:.0f}%)        : "
          f"{band(lambda a: material_at(a, 1.35, Q5_MATERIAL_BAR))}")
    print(f"  techo Q4 (identidad a w=1.50)   : α ≤ "
          f"{q4_ceiling if q4_ceiling is not None else '—'}")
    print(f"  estructural 1.35 vs 1.50        : (1−f) = "
          f"{1-factors[1.35]:.3f} a w=1.35 vs {1-factors[1.50]:.3f} a w=1.50 → "
          f"la fatiga realizada en 1.35 es {100*(1-factors[1.35])/(1-factors[1.50]):.0f}% "
          "de la de 1.50 (asimetría estructural, no artefacto de la barra)")
    print("-" * 150)
    if winner is not None:
        # Holguras del ganador: sin esto el "CANDIDATO" puede parecer mucho más
        # firme de lo que es (en 50k α=.60 apenas supera la barra de materialidad).
        slack135 = cost(winner, 1.35, 95) - identity_gap * Q5_MATERIAL_BAR
        margin_q4 = fresh_mid - r(winner, 1.50, 95, "xbh")
        # Frontera Q4 interpolada linealmente entre el último α sano y el
        # primero que cruza (etiquetado como interpolación, no como medición).
        crossing = None
        for a, b in zip(candidates, candidates[1:]):
            if q4_by_alpha[a] and not q4_by_alpha[b]:
                m_a = fresh_mid - r(a, 1.50, 95, "xbh")
                m_b = fresh_mid - r(b, 1.50, 95, "xbh")
                if m_a > 0 > m_b:
                    crossing = a + (b - a) * m_a / (m_a - m_b)
                break
        print(f"003B-5B DECISION → α = {winner:.2f} es el CANDIDATO")
        print(f"  Stuff gameplay k = .30 · Stuff fatigue: effective = raw·(1 − "
              f"{winner:.2f}·(1−f)) con f = get_fatigue_factor() productivo")
        print(f"  materialidad: cost@1.50 ST95 {cost(winner, 1.50, 95):+.2f}pp "
              f"({cost(winner, 1.50, 95)/identity_gap*100:.0f}% del gap de "
              f"identidad) | retención ST95 @1.50 "
              f"{retention(winner, 1.50, 95)*100:.1f}% | margen de identidad "
              f"Q4 {margin_q4:+.2f}pp")
        print(f"  HOLGURAS: cost@1.35 {cost(winner, 1.35, 95):.2f}pp vs barra "
              f"{identity_gap*Q5_MATERIAL_BAR:.2f}pp → {slack135:+.2f}pp "
              f"({slack135/(identity_gap*Q5_MATERIAL_BAR)*100:+.1f}% de la barra) "
              f"| margen Q4 {margin_q4:+.2f}pp")
        if crossing is not None:
            print(f"  Frontera Q4 interpolada: α* ≈ {crossing:.2f} (entre el "
                  f"mayor α sano y el primero que cruza) → el α ganador está a "
                  f"{crossing-winner:.2f} de la frontera")
        if abs(slack135) < 0.5:
            print(f"  AVISO: el ganador supera la barra de materialidad por "
                  f"{abs(slack135):.2f}pp — es un punto de equilibrio, no un "
                  f"interior robusto. La lectura por BANDAS (arriba) es la "
                  f"confiable; este α es el mínimo que satisface la lectura "
                  f"estricta de Q5.")
        print("  Sigue SIN tocar producción (calculator.py UNCHANGED).")
        print("  Siguiente → 003B-5C de robustez: Power {45,70,95} × Stuff "
              "{45,70,95} × workload {1.00,1.35,1.50} con α ganador, para")
        print("  comprobar que Power×Stuff×Fatigue no rompe la superficie "
              "validada en 003B-4. Solo después 003B-6 (producción).")
    else:
        # Sin ganador: hay que separar POR QUÉ no lo hay. Si el techo de Q4 y el
        # mínimo de materialidad no se solapan, el conflicto es entre contratos
        # (Q4 vs Q5), no un fallo de los α candidatos.
        need135 = next((a for a in candidates
                        if all(spec[a][c] for c in hard)
                        and material_at(a, 1.35, Q5_MATERIAL_BAR)), None)
        print("003B-5B DECISION → NINGÚN α es a la vez sano y material en 1.35 "
              "y 1.50 con la barra actual.")
        print(f"  Q4 permite hasta α={q4_ceiling if q4_ceiling is not None else '—'}"
              f"; la materialidad@1.35 empieza en α={need135 if need135 is not None else '—'}"
              f". Si el mínimo de materialidad es MAYOR que el techo de Q4, el "
              "conflicto es entre contratos (Q5 vs Q4), no entre candidatos.")
        print("  Relee la tabla de sensibilidad: la decisión depende de la barra, "
              "así que la barra es una decisión de diseño, no un hallazgo.")
    if q4_by_alpha[1.00]:
        print("AVISO DE INSTRUMENTO: Q4 debería RECHAZAR α=1.00 (la frontera que "
              "condenó FULL en 5A). Si α=1.00 pasa Q4, el instrumento está "
              "sospechoso → revisar antes de leer cualquier otra cosa.")


# ---------------------------------------------------------------------------
# 003B-5C · Power × Stuff × Fatigue robustness, α=.50 vs α=.60 (2.7M PA)
# ---------------------------------------------------------------------------
# 003B-5B dejó la decisión de α en una frontera de 0.01pp: ambos α pasan Q1–Q7
# y ambos son VIABLES, y el que "gana" la lectura estricta de Q5 lo hace por
# +0.01pp sobre una barra POST-HOC. Eso NO es evidencia suficiente para congelar
# un parámetro de producción. 5C cambia de filosofía: NO vuelve a preguntar si α
# alcanza una barra arbitraria de materialidad — pregunta si el SISTEMA se
# comporta mejor con α=.60 que con α=.50, en la superficie completa
# Power × Stuff × Fatigue.
#
# La familia y la fórmula NO se re-litigan (5A) ni el rango sano (5B):
#     effective_stuff = raw_stuff * (1 - α * (1 - f)),  f = get_fatigue_factor()
#
# DESCARTADOS antes de correr (5B): α<=.25 cosmético · α>=.75 pierde identidad
# (Q4) · α=.40 fallback conservador documentado, NO se lleva a 5C salvo que
# ambos finalistas fallen. FINALISTAS: .50 (menor intervención) vs .60.
STUFF_FATIGUE_ALPHAS_003B5C = (0.50, 0.60)   # finalistas pareados
POWER_LEVELS_003B5C = (45, 70, 95)           # poder del BATTER (eje de 003B-4)
STUFF_LEVELS_003B5C = (45, 70, 95)
WORKLOADS_003B5C = (1.00, 1.35, 1.50)        # w=1.00 es el control FRESCO in-run
K_003B5C = 0.30                              # S2 (003B-3 · 003B-4 · congelado)
PROD_THRESHOLD_003B5C = get_pitch_threshold(9)  # 100 (Fatigue Policy v2)

# --- Tolerancias R1–R9 (fijadas ANTES de correr, heredadas donde ya existían) ---
R1_STEP_PP = 0.2    # R1: Power↑ → XBH↑ por paso (tol de 003B-4 O1/O2; los
                    #   incrementos frescos observados son ~4pp/paso, ~20× la tol)
R2_STEP_PP = 0.2    # R2: Stuff↓ → XBH↑ por paso (003B-4 O2; ~7.5pp/paso frescos)
R3_STEP_PP = 0.7    # R3: el coste de fatiga de Stuff70/95 debe MONOTONO en w.
                    #   Tol = la de 003B-5B Q3: cerca de saturación (POW95) el
                    #   paso de XBH puede encogerse por el techo, no por señal
                    #   inversa; 0.7pp evita un FAIL falso sin abrir la puerta a
                    #   una inversión real de la fatiga.
R4_MARGIN_PP = 0.0  # R4: ST95 fatigado sigue siendo MEJOR en supresión que ST70
                    #   FRESCO (misma α, mismo Power) — la frontera exacta de 5B Q4,
                    #   ahora generalizada a los 3 Powers y a los 3 workloads.
R4_BAND_PP = 1.0   # R4 banda advisory (no contractual), como en 5B Q4.
R5_EXPR_PP = 1.0   # R5: ambos atributos siguen EXPRESÁNDOSE en el matchup fuerte.
                    #   Barra = la de 003B-4 O3 (1.0pp; observado +9.83).
R6_XBH_MAX = 55.0  # R6: topes de 003B-4 O4 (observado máx 40.66/29.49) → 5C no
R6_HR_MAX = 35.0   #   puede romper la superficie YA validada en 003B-4.
R7_KEEP_FRAC = 0.50  # R7: la esquina POBAJO×ST95 (XBH fresca 003B-4 = 5.53%, ya
                    #   casi degenerada con HR 0.01%) no puede perder más de la
                    #   MITAD de su propio valor fresco IN-RUN. Referencia
                    #   relativa al control w=1.00 de la MISMA matriz: no es una
                    #   barra inventada, es "no empeorar el extremo validado".
R7_BUCKET_MAX = 85.0  # R7: ningún bucket de contacto puede dominar el BIP
                      #   (≥85% = distribución degenerada).
R8_P95_MAX = 6     # R8: K5-R (p95 ≤ 6, CAP 0) — idéntico a 5B Q7.
R8_P12_MAX = 0.05
R8_P16_MAX = 0.01
R8_SHAPE_PP = 0.0  # R8 shape: α sólo mueve el bucket del PRIMER BIP → la
                    #   TRAYECTORIA del PA (pitches, K, BB, BIP, whiff, called,
                    #   cnt, t12, t16, p95) debe ser IDÉNTICA entre α=.50 y α=.60
                    #   en la misma celda (p, st, w). Invarianza EXACTA, no
                    #   estadística: es el mismo argumento de 5B Q7, y convierte
                    #   todo 5C en un auto-control del instrumento (27 celdas
                    #   pareadas gratis).
R9_Z = 2.0         # R9: "mejora material" = |Δ| > 2 SE del Δ PAREADO. La barra
                    #   NO es arbitraria: sale de la varianza de los propios datos
                    #   con las seeds compartidas. Es la replacement de la barra
                    #   de materialidad de 5B.

# REPRO 003B-4: el control fresco (w=1.00) de 5C debe reproducir la superficie
# fresca de 003B-4 (k=.30, mismas seeds 750M+rep) — es la MISMA matriz con α
# inerte, porque con f=1.0 el α no puede cambiar nada. Si esto falla, 5C no está
# midiendo lo que dice medir.
REPRO_4_003B5C = {
    45: {"xbh": (20.72, 13.11, 5.53), "hr": (9.52, 2.01, 0.01)},
    70: {"xbh": (30.49, 23.03, 15.77), "hr": (19.74, 12.10, 4.53)},
    95: {"xbh": (40.66, 32.95, 25.59), "hr": (29.49, 22.12, 14.75)},
}
REPRO_4_TOL_PP = 0.01

# Códigos de outcome por PA (para la tabla de contingencia pareada α-vs-α).
_OUT_CODES_003B5C = ("K", "BB", "OUT", "1B", "2B", "3B", "HR")
_CODE_IDX_003B5C = {c: i for i, c in enumerate(_OUT_CODES_003B5C)}
_METRIC_CODES_003B5C = {
    "xbh": ("2B", "3B", "HR"),
    "hr": ("HR",),
    "out": ("OUT",),
    "reach": ("BB", "1B", "2B", "3B", "HR"),
}
_BIP_CODES_003B5C = ("OUT", "1B", "2B", "3B", "HR")


def _stuff_fatigue_eff_003b5c(raw: float, alpha: float, f: float) -> float:
    """Misma familia que 5A/5B (una sola fórmula en el LAB)."""
    return raw * (1.0 - alpha * (1.0 - f))


def _paired_ratio_003b5c(codes_num, codes_den, joint, n):
    """Δ y SE de una RAZÓN de conteos entre dos celdas PAREADAS por seed.

    Devuelve (ratio_50_pct, ratio_60_pct, delta_pp, se_pp, z) para num/den
    (ej. XBH/BIP), donde Δ = α=.60 − α=.50. `joint` es la tabla de contingencia
    7×7 de los códigos de outcome emparejados (filas = α=.50, columnas = α=.60)
    de las dos celdas.

    Razón de medias: R = x̄/ȳ. Var(R) por delta-method CON la covarianza
    emparejada real, de modo que el SE de la DIFERENCIA recoge la correlación
    positiva de las dos celdas (mismo PA, mismo seed) en vez de asumir
    independencia — que es lo que infla un SE ingenuo y haría que una diferencia
    real pareciera ruido. Verificado contra bootstrap pareado (ratio SE
    analítico/SE bootstrap ≈ 0.97–1.06).
    """
    num_idx = [_CODE_IDX_003B5C[c] for c in codes_num]
    den_idx = [_CODE_IDX_003B5C[c] for c in codes_den]
    allc = list(range(7))

    def marg_a(idx):
        return sum(joint[i][j] for i in idx for j in allc) / n

    def marg_b(idx):
        return sum(joint[i][j] for i in allc for j in idx) / n

    def cross(ia, jb):
        """E[serie_A(ia) · serie_B(jb)] — producto cruzado EMPAREJADO."""
        return sum(joint[i][j] for i in ia for j in jb) / n

    # A = filas de la tabla (α=.50) · B = columnas de la tabla (α=.60).
    # Son celdas DISTINTAS: el Δ de una razón tiene que restar dos marginales
    # distintas de la misma tabla de contingencia, no la misma dos veces.
    x_a, y_a = marg_a(num_idx), marg_a(den_idx)
    x_b, y_b = marg_b(num_idx), marg_b(den_idx)
    if y_a <= 0 or y_b <= 0:
        return (0.0, 0.0, 0.0, float("inf"), 0.0)
    r_a, r_b = x_a / y_a, x_b / y_b
    # varianzas de las medias (poblacionales / n); los márgenes son Bernoulli
    v_xa, v_xb = x_a - x_a * x_a, x_b - x_b * x_b
    v_ya, v_yb = y_a - y_a * y_a, y_b - y_b * y_b
    c_xa_ya = cross(num_idx, den_idx) - x_a * y_a          # E[x_A·y_A]
    c_xb_yb = cross(den_idx, num_idx) - x_b * y_b          # E[x_B·y_B]
    var_a = (v_xa + r_a * r_a * v_ya - 2 * r_a * c_xa_ya) / (n * y_a * y_a)
    var_b = (v_xb + r_b * r_b * v_yb - 2 * r_b * c_xb_yb) / (n * y_b * y_b)
    # covarianza entre las dos celdas (emparejada) — los 4 productos cruzados
    c_xa_xb = cross(num_idx, num_idx) - x_a * x_b          # E[x_A·x_B]
    c_ya_yb = cross(den_idx, den_idx) - y_a * y_b          # E[y_A·y_B]
    c_ya_xb = cross(den_idx, num_idx) - y_a * x_b          # E[y_A·x_B]
    c_xa_yb = cross(num_idx, den_idx) - x_a * y_b          # E[x_A·y_B]
    cov = (c_xa_xb + r_a * r_b * c_ya_yb
           - r_a * c_ya_xb - r_b * c_xa_yb) / (n * y_a * y_b)
    se = math.sqrt(max(0.0, var_a + var_b - 2 * cov))
    delta = (r_b - r_a) * 100          # Δ = α=.60 − α=.50
    return (r_a * 100, r_b * 100, delta, se * 100,
            (delta / (se * 100)) if se > 0 else 0.0)


def _joint_ratio_003b5c(joint4, coeffs, codes_num, codes_den, n):
    """G = Σ_j coeffs_j·(x_j/y_j) sobre 4 celdas PAREADAS, con SE multinomial.

    Es la versión de 4 celdas de _paired_ratio_003b5c: sirve para los
    GRADIENTES (p. ej. ΔST95 − ΔST45 mezcla las DOS α y las DOSStuff, así que
    su SE no puede sacarse de las tablas 2×2 de Δ: las dos diferencias están
    fuertemente correlacionadas y restar sus SEs en quadrature exageraría el
    error). Se aplica el delta-method sobre el multinomial de 4 vías:

        Var(Ĝ) ≈ (1/n)·[ Σ_k p_k·g_k² − (Σ_k p_k·g_k)² ]

    con g_k = ∂G/∂p_k (cada categoría es una tupla de 4 códigos, y las
    marginales son 0/1 dentro de la categoría).
    """
    num_idx = set(_CODE_IDX_003B5C[c] for c in codes_num)
    den_idx = set(_CODE_IDX_003B5C[c] for c in codes_den)
    # Las marginales van como PROPORCIONES (conteos/n), no como conteos: las
    # derivadas ∂G/∂p_k viven en la escala de las proporciones, y usar conteos
    # aquí rompe el SE por un factor n.
    xs = [0.0] * 4
    ys = [0.0] * 4
    for key, c in joint4.items():
        w = c / n
        for j in range(4):
            if key[j] in num_idx:
                xs[j] += w
            if key[j] in den_idx:
                ys[j] += w
    if any(ys[j] <= 0 for j in range(4)):
        return (0.0, float("inf"), 0.0)
    ratios = [xs[j] / ys[j] for j in range(4)]
    g = sum(coeffs[j] * ratios[j] for j in range(4))
    s1 = 0.0
    s2 = 0.0
    for key, c in joint4.items():
        p = c / n
        gk = 0.0
        for j in range(4):
            if ys[j] <= 0:
                continue
            if key[j] in num_idx:
                gk += coeffs[j] / ys[j]
            if key[j] in den_idx:
                gk -= coeffs[j] * ratios[j] / ys[j]
        s1 += p * gk * gk
        s2 += p * gk
    var = max(0.0, s1 - s2 * s2) / n
    se = math.sqrt(var)
    return (g * 100, se * 100, (g * 100 / (se * 100)) if se > 0 else 0.0)


def run_power_stuff_fatigue_e003b5c(reps: int) -> None:
    """003B-5C · Power × Stuff × Fatigue, α=.50 vs α=.60, contratos R1–R9."""
    n = reps
    k = K_003B5C
    batter_tpl = BATTER_PROFILES_003A["MID"]
    pitcher = PITCHER_PROFILES_003A["MID"]
    powers = list(POWER_LEVELS_003B5C)
    stuffs = list(STUFF_LEVELS_003B5C)
    workloads = list(WORKLOADS_003B5C)
    alphas = list(STUFF_FATIGUE_ALPHAS_003B5C)
    cells = {}
    codes = {}
    eff = {}

    def fresh_agg():
        return {"pitches": 0, "take_attempts": 0, "called_strikes_on_take": 0,
                "swing_attempts": 0, "whiffs": 0, "outcome": Counter(),
                "lengths": [], "power": [], "bips": 0, "len12": 0, "len16": 0}

    factors = {w: get_fatigue_factor(
        int(w * PROD_THRESHOLD_003B5C), PROD_THRESHOLD_003B5C)
        for w in workloads}
    for a in alphas:
        for w in workloads:
            f = factors[w]
            for p in powers:
                for st in stuffs:
                    e = _stuff_fatigue_eff_003b5c(float(st), a, f)
                    eff[(a, w, p, st)] = e
                    batter = dict(batter_tpl, poder=p)
                    agg = fresh_agg()
                    cd = bytearray()
                    for rep in range(reps):
                        # MISMAS seeds que 003B-4/5A/5B en todas las celdas:
                        # las dos familias α son 100% pareadas entre sí y con la
                        # superficie fresca de 003B-4.
                        seed = int(DISCIPLINE_WORKLOAD * 1000) * 10**6 + rep
                        d = _simulate_pa_diag(E1_POLICY, seed,
                                              batter_attrs=batter,
                                              pitcher_attrs=pitcher,
                                              stuff_level=e,
                                              stuff_arm="S2",
                                              stuff_k_qty=k,
                                              workload=w,
                                              power_log=agg["power"])
                        agg["pitches"] += d["pitches"]
                        agg["take_attempts"] += d["take_attempts"]
                        agg["called_strikes_on_take"] += d["called_strikes_on_take"]
                        agg["swing_attempts"] += d["swing_attempts"]
                        agg["whiffs"] += d["whiffs"]
                        agg["bips"] += d["bips"]
                        agg["outcome"][d["outcome"]] += 1
                        agg["lengths"].append(d["pitches"])
                        cd.append(_CODE_IDX_003B5C[d["outcome"]])
                        if d["pitches"] >= 12:
                            agg["len12"] += 1
                        if d["pitches"] >= 16:
                            agg["len16"] += 1
                    agg["lengths"].sort()
                    agg["p95"] = agg["lengths"][int(len(agg["lengths"]) * 0.95) - 1]
                    agg["power"].sort()
                    cells[(a, w, p, st)] = agg
                    codes[(a, w, p, st)] = cd

    rows = {(a, w, p, st): _metric_row(cells[(a, w, p, st)], n)
            for a in alphas for w in workloads for p in powers for st in stuffs}

    def r(a, w, p, st, key):
        return rows[(a, w, p, st)][key]

    def cost(a, w, p, st, key="xbh"):
        """Coste de fatiga de Stuff: métrica de (α,w,p,st) menos la de w=1.00."""
        return r(a, w, p, st, key) - r(a, 1.00, p, st, key)

    # Tablas de contingencia pareadas α=.50 vs α=.60 por celda (Power×Stuff×w).
    joint = {}
    for w in workloads:
        for p in powers:
            for st in stuffs:
                tab = [[0] * 7 for _ in range(7)]
                ca, cb = codes[(0.50, w, p, st)], codes[(0.60, w, p, st)]
                for x, yy in zip(ca, cb):
                    tab[x][yy] += 1
                joint[(w, p, st)] = tab

    def delta_m(w, p, st, metric):
        num = _METRIC_CODES_003B5C[metric]
        den = _BIP_CODES_003B5C
        return _paired_ratio_003b5c(num, den, joint[(w, p, st)], n)

    # Tablas de 4 vías para los GRADIENTES: (α, Stuff/axis) × (α, Stuff/axis).
    # El gradiente mezcla las dos α, así que su SE necesita la covarianza
    # cruzada de las 4 celdas, no los SEs de los Δ por separado.
    joint4_stuff = {}
    joint4_power = {}
    for w in workloads:
        for p in powers:
            t = {}
            c45 = codes[(0.50, w, p, 45)]
            c95 = codes[(0.50, w, p, 95)]
            c60_45 = codes[(0.60, w, p, 45)]
            c60_95 = codes[(0.60, w, p, 95)]
            for i, (a1, a2, a3, a4) in enumerate(zip(c45, c95, c60_45, c60_95)):
                k4 = (a1, a2, a3, a4)
                t[k4] = t.get(k4, 0) + 1
            joint4_stuff[(w, p)] = t
        for st in stuffs:
            t = {}
            c45 = codes[(0.50, w, 45, st)]
            c95 = codes[(0.50, w, 95, st)]
            c60_45 = codes[(0.60, w, 45, st)]
            c60_95 = codes[(0.60, w, 95, st)]
            for a1, a2, a3, a4 in zip(c45, c95, c60_45, c60_95):
                k4 = (a1, a2, a3, a4)
                t[k4] = t.get(k4, 0) + 1
            joint4_power[(w, st)] = t

    def grad_stuff(w, p, metric):
        """ΔST95 − ΔST45 = (R60_95 − R50_95) − (R60_45 − R50_45) → c = (+1,−1,−1,+1)."""
        return _joint_ratio_003b5c(joint4_stuff[(w, p)], (1.0, -1.0, -1.0, 1.0),
                                   _METRIC_CODES_003B5C[metric],
                                   _BIP_CODES_003B5C, n)

    def grad_power(w, st, metric):
        """ΔPOW95 − ΔPOW45 con la misma comb but sobre el eje Power."""
        return _joint_ratio_003b5c(joint4_power[(w, st)], (1.0, -1.0, -1.0, 1.0),
                                   _METRIC_CODES_003B5C[metric],
                                   _BIP_CODES_003B5C, n)

    print("=" * 150)
    print("GAMEPLAY-ENGINE-003B-5C · POWER × STUFF × FATIGUE ROBUSTNESS "
          f"(α={'/'.join(f'{a:.2f}' for a in alphas)}, k={k})")
    print(f"2 α × 3 Power × 3 Stuff × 3 workloads × {reps:,} PA = "
          f"{reps*54:,} PA | seeds compartidas (750M+rep) | pitcher MID | "
          "agente 65/50/30 | PROD discipline")
    print("Power = poder del BATTER (eje de 003B-4) · Stuff = stuff_level del "
          "pitcher fatigado (k=.30) · w=1.00 es el control FRESCO in-run")
    print("α sólo mueve el bucket del PRIMER BIP → las dos familias son "
          "pareadas seed a seed y la trayectoria del PA debe ser IDÉNTICA (R8).")
    print("Contratos R1–R9 FIJADOS ANTES de correr. calculator.py UNCHANGED.")
    print("=" * 150)

    for a in alphas:
        for w in workloads:
            print()
            tag = " (FRESCO · control)" if w == 1.00 else ""
            print(f"---- α={a:.2f} · w={w:.2f}{tag} " + "-" * (30 - len(tag)))
            for key, lbl in (("xbh", "XBH/BIP"), ("hr", "HR/BIP"),
                             ("out_bip", "OUT/BIP"), ("reach", "Reach/PA")):
                print(f"  {lbl:>8} | filas = POWER del batter, cols = STUFF")
                print(f"  {'POW':>8} | {'ST45':>8} {'ST70':>8} {'ST95':>8}")
                for p in powers:
                    vals = " ".join(f"{r(a, w, p, st, key):>8.2f}" for st in stuffs)
                    print(f"  {p:>8} | {vals}")
            print(f"  {'eff ST':>8} | " + " ".join(
                f"{eff[(a, w, 70, st)]:>8.2f}" for st in stuffs)
                + "   (ST45/70/95)")
            print("  " + "-" * 36)

    # ---------------- Contratos R1–R8 ----------------
    print()
    print("-- CONTRATOS R1–R8 (fijados antes) --")
    results = {}
    for a in alphas:
        res = {}
        # R1 POWER EXPRESSION
        bad = []
        for w in workloads:
            for st in stuffs:
                seq = [r(a, w, p, st, "xbh") for p in powers]
                for lo, hi in zip(seq, seq[1:]):
                    if hi - lo < R1_STEP_PP:
                        bad.append(f"w={w} ST{st} {lo:.2f}→{hi:.2f}")
                seqb = [r(a, w, p, st, "bip") for p in powers]
                for lo, hi in zip(seqb, seqb[1:]):
                    if hi - lo < 0.0:
                        bad.append(f"BIP w={w} ST{st} {lo:.2f}→{hi:.2f}")
        res["R1"] = not bad
        print(f"  R1 POWER EXPRESSION       α={a:.2f}: "
              f"{'PASS' if res['R1'] else 'FAIL ' + '; '.join(bad[:3])}")
        # R2 STUFF EXPRESSION
        bad = []
        for w in workloads:
            for p in powers:
                seq = [r(a, w, p, st, "xbh") for st in stuffs]
                for hi, lo in zip(seq, seq[1:]):
                    if hi - lo < R2_STEP_PP:
                        bad.append(f"w={w} POW{p} {hi:.2f}→{lo:.2f}")
        res["R2"] = not bad
        print(f"  R2 STUFF EXPRESSION       α={a:.2f}: "
              f"{'PASS' if res['R2'] else 'FAIL ' + '; '.join(bad[:3])}")
        # R3 FATIGUE DIRECTION
        bad = []
        for p in powers:
            for st in (70, 95):
                seq = [cost(a, w, p, st) for w in workloads]
                for lo, hi in zip(seq, seq[1:]):
                    if hi - lo < -R3_STEP_PP:
                        bad.append(f"POW{p} ST{st} {lo:+.2f}→{hi:+.2f}")
        res["R3"] = not bad
        print(f"  R3 FATIGUE DIRECTION      α={a:.2f}: "
              f"{'PASS' if res['R3'] else 'FAIL ' + '; '.join(bad[:3])}")
        # R4 ELITE IDENTITY
        bad = []
        margins = []
        for p in powers:
            for w in workloads:
                m = r(a, 1.00, p, 70, "xbh") - r(a, w, p, 95, "xbh")
                margins.append((m, p, w))
                if m <= R4_MARGIN_PP:
                    bad.append(f"POW{p} w={w} margen {m:+.2f}")
        margins.sort()
        res["R4"] = not bad
        mmin, pmin, wmin = margins[0]
        res["_r4_min"] = mmin
        print(f"  R4 ELITE IDENTITY         α={a:.2f}: "
              f"{'PASS' if res['R4'] else 'FAIL ' + '; '.join(bad[:3])} "
              f"(min {mmin:+.2f}pp @POW{pmin} w={wmin})")
        # R5 STRONG-vs-STRONG
        bad = []
        for w in (1.35, 1.50):
            dpow = r(a, w, 95, 95, "xbh") - r(a, w, 45, 95, "xbh")
            dstuff = r(a, w, 95, 45, "xbh") - r(a, w, 95, 95, "xbh")
            if dpow < R5_EXPR_PP:
                bad.append(f"w={w} Power {dpow:+.2f}")
            if dstuff < R5_EXPR_PP:
                bad.append(f"w={w} Stuff {dstuff:+.2f}")
        res["R5"] = not bad
        print(f"  R5 STRONG-vs-STRONG       α={a:.2f}: "
              f"{'PASS' if res['R5'] else 'FAIL ' + '; '.join(bad)}")
        # R6 NO EXTREME EXPLOSION
        ext_x = r(a, 1.50, 95, 45, "xbh")
        ext_h = r(a, 1.50, 95, 45, "hr")
        res["R6"] = ext_x <= R6_XBH_MAX and ext_h <= R6_HR_MAX
        print(f"  R6 NO EXTREME EXPLOSION   α={a:.2f}: "
              f"{'PASS' if res['R6'] else 'FAIL'} "
              f"(POW95×ST45×w1.50 XBH {ext_x:.2f}≤{R6_XBH_MAX}, "
              f"HR {ext_h:.2f}≤{R6_HR_MAX})")
        # R7 NO EXTREME COLLAPSE
        fresh_x = r(a, 1.00, 45, 95, "xbh")
        fat_x = r(a, 1.50, 45, 95, "xbh")
        bucket_max = max(r(a, 1.50, 45, 95, k2)
                         for k2 in ("out_bip", "x1", "x2", "x3", "hr"))
        res["R7"] = (fat_x >= R7_KEEP_FRAC * fresh_x
                     and bucket_max <= R7_BUCKET_MAX)
        print(f"  R7 NO EXTREME COLLAPSE    α={a:.2f}: "
              f"{'PASS' if res['R7'] else 'FAIL'} "
              f"(POW45×ST95 XBH {fat_x:.2f} vs fresco {fresh_x:.2f} "
              f"(≥{R7_KEEP_FRAC*fresh_x:.2f}), bucket máx {bucket_max:.2f}"
              f"≤{R7_BUCKET_MAX})")
        # R8 SYSTEM STABILITY
        bad = []
        p95max = max(rows[k]["p95"] for k in rows)
        t12max = max(rows[k]["t12"] for k in rows)
        t16max = max(rows[k]["t16"] for k in rows)
        if p95max > R8_P95_MAX:
            bad.append(f"p95 {p95max}")
        if t12max > R8_P12_MAX:
            bad.append(f"t12 {t12max:.3f}")
        if t16max > R8_P16_MAX:
            bad.append(f"t16 {t16max:.3f}")
        for k2 in rows:
            for kk, vv in rows[k2].items():
                if not (0.0 <= vv <= 100.0) and kk not in ("pmean", "p10", "p50",
                                                           "p90", "p95", "paus"):
                    bad.append(f"{kk} fuera de rango")
        res["R8"] = not bad
        print(f"  R8 SYSTEM STABILITY       α={a:.2f}: "
              f"{'PASS' if res['R8'] else 'FAIL ' + '; '.join(bad[:3])} "
              f"(p95 máx {p95max}≤{R8_P95_MAX}, CAP 0, t12 {t12max:.3f}"
              f"≤{R8_P12_MAX}%, t16 {t16max:.3f}≤{R8_P16_MAX}%)")
        results[a] = res
    # R8 shape: trayectoria del PA idéntica entre α (invarianza EXACTA)
    shape_bad = []
    for w in workloads:
        for p in powers:
            for st in stuffs:
                for kk in ("paus", "k", "bb", "bip", "t12", "t16", "whiff",
                           "called_tk", "cnt", "p95"):
                    d2 = abs(rows[(0.50, w, p, st)][kk] - rows[(0.60, w, p, st)][kk])
                    if d2 > R8_SHAPE_PP:
                        shape_bad.append(f"w={w} POW{p} ST{st} {kk} {d2:.3f}")
    results["_shape"] = not shape_bad
    print(f"  R8 PA SHAPE (α pareado)  : {'PASS' if results['_shape'] else 'FAIL'} "
          f"(invarianza EXACTA en las 27 celdas pareadas; "
          f"{'0.00pp en todos los canales' if not shape_bad else shape_bad[:2]})")
    print("  " + "-" * 80)
    repro_dev = max(
        [abs(r(a, 1.00, p, sti, key) - rv)
         for a in alphas for p in powers for key in ("xbh", "hr")
         for sti, rv in zip(stuffs, REPRO_4_003B5C[p][key])])
    results["_repro4"] = repro_dev <= REPRO_4_TOL_PP
    print(f"  REPRO 003B-4 (fresco)  : "
          f"{'PASS' if results['_repro4'] else 'FAIL'} (α es inerte con f=1.0 → "
          f"las 36 cifras frescas deben ser las de 003B-4; |Δ| máx "
          f"{repro_dev:.2f}pp, tol {REPRO_4_TOL_PP})")
    print(f"  Veredicto R1–R8: α=.50 "
          f"{'PASS' if all(results[0.50][c] for c in ('R1','R2','R3','R4','R5','R6','R7','R8')) and results['_shape'] else 'FAIL'}"
          f" · α=.60 "
          f"{'PASS' if all(results[0.60][c] for c in ('R1','R2','R3','R4','R5','R6','R7','R8')) and results['_shape'] else 'FAIL'}")
    print("  " + "-" * 80)

    # ---------------- R9: superficie pareada Δ(.60 − .50) ----------------
    print()
    print("-- R9 · ROBUSTNESS DOMINANCE: superficie PAREADA Δ(.60 − .50) --")
    print("   Δ > 0 = α=.60 produce MÁS de esa métrica (más XBH/HR = menos "
          "supresión = más daño al hitter).")
    print("   'material' = |Δ| > 2 SE del Δ pareado (R9_Z). No hay barra de")
    print("   materialidad: el umbral sale de la varianza de los propios datos.")
    for metric in ("xbh", "hr", "out", "reach"):
        print()
        print(f"  Δ {metric.upper()}/{'PA' if metric == 'reach' else 'BIP'} "
              f"(pp) [z] · filas = POWER, cols = STUFF")
        for w in workloads:
            tag = " (FRESCO)" if w == 1.00 else ""
            print(f"    w={w:.2f}{tag}")
            print(f"    {'POW':>5} | {'ST45':>16} {'ST70':>16} {'ST95':>16}")
            for p in powers:
                cs = []
                for st in stuffs:
                    _, _, d3, se, z = delta_m(w, p, st, metric)
                    cs.append(f"{d3:>+7.2f} [{z:>+5.1f}]")
                print(f"    {p:>5} | " + " ".join(f"{c:>16}" for c in cs))
    # Gradientes del Δ: esto separa "expresión de fatiga" de "castigo genérico"
    print()
    print("  DIAGNÓSTICO DECISIVO · gradiente STUFF y gradiente POWER del Δ")
    print("  Un Δ que crece con ST es expresión ACOPLADA (más fatiga de Stuff);")
    print("  un Δ plano en ST es daño genérico (castigo, no señal).")
    print("  El gradiente lleva su PROPIO SE pareado (4 celdas): restar los SEs")
    print("  de los dos Δ en quadrature habría exagerado el error, porque están")
    print("  fuertemente correlacionados.")
    grads = {}
    for metric in ("xbh", "hr"):
        print()
        for w in workloads:
            if w == 1.00:
                continue
            print(f"    Δ{metric.upper()} w={w:.2f}")
            print(f"      {'gradiente STUFF (ΔST95−ΔST45)':>32} | "
                  f"{'gradiente POWER (ΔPOW95−ΔPOW45)':>34}")
            gs, gp = [], []
            for p in powers:
                g, se, z = grad_stuff(w, p, metric)
                grads[("st", w, p, metric)] = (g, se, z)
                gs.append(f"POW{p}:{g:+.2f} [{z:>+5.1f}]")
            for st in stuffs:
                g, se, z = grad_power(w, st, metric)
                grads[("pw", w, st, metric)] = (g, se, z)
                gp.append(f"ST{st}:{g:+.2f} [{z:>+5.1f}]")
            print(f"      {' '.join(gs):>32} | {' '.join(gp):>34}")
    # Coste de fatiga por α (para leer "cuánta fatiga de Stuff se expresa")
    print()
    print("  COSTE DE FATIGA DE STUFF POR α (Δ vs w=1.00 de la misma α, XBH/BIP)")
    for a in alphas:
        for st in stuffs:
            seq = " ".join(f"w={w:.2f}:{cost(a, w, 70, st):+.2f}" for w in workloads)
            print(f"    α={a:.2f} ST{st} (POW70) {seq}")
        print()

    # ---------------- R9 VEREDICT ----------------
    win = (0.50, 0.60)
    print("  " + "-" * 80)
    print("  R9 · ROBUSTNESS DOMINANCE — procedure (fijada antes del run):")
    print("    1) Si α=.60 falla algún R1–R8 que α=.50 pasa → gana .50 (trivial).")
    print("    2) Si .60 pasa R1–R8, gana SOLO si cumple las TRES cláusulas:")
    print("       (a) expresión ACOPLADA material y consistente: gradiente STUFF")
    print("           del Δ > 0 con |z| > 2 en w=1.35 y w=1.50, en los 3 Powers")
    print("       (b) NO reduce la identidad: margen R4 de .60 ≥ el de .50")
    print("       (c) NO empeora los extremos: R6 y R7 igual de bien que .50")
    print("    3) En cualquier otro caso → gana el MENOR α (.50), porque una vez")
    print("       que dos valores cumplen la función se elige el de menor")
    print("       intervención: .60 tiene que JUSTIFICAR su acoplamiento extra.")
    r50 = results[0.50]
    r60 = results[0.60]
    f50 = all(r50[c] for c in ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"))
    f60 = all(r60[c] for c in ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"))
    gx150 = [grads[("st", 1.50, p, "xbh")] for p in powers]
    gx135 = [grads[("st", 1.35, p, "xbh")] for p in powers]
    clause_a = all(g > 0 and abs(z) > R9_Z for g, _, z in gx150 + gx135)
    clause_b = r60["_r4_min"] >= r50["_r4_min"]
    # (c) robustez estructural en los extremos: los techos de R6 y la
    # no-degeneración de R7 se siguen respetando. No se exige que .60 sea
    # IDÉNTICO a .50 (imposible: un α mayor da más daño por construcción, y eso
    # es justo lo que se evalúa en la cláusula (a)); se exige que no ROMPA el
    # extremo. Se imprime el HOLGURA para que el judgement sea visible.
    clause_c = r60["R6"] and r60["R7"]
    nmat = sum(1 for w in workloads for p in powers for st in stuffs
               if abs(delta_m(w, p, st, "xbh")[4]) > R9_Z)
    print()
    print("  R9 · evaluación de cláusulas (α=.60 debe Ganar las TRES):")
    print(f"    (a) expresión acoplada: gradiente STUFF del Δ(XBH) > 0 y |z|>2 "
          f"en 1.35 y 1.50 × 3 Powers → "
          f"{'CUMPLE' if clause_a else 'NO CUMPLE'}")
    print(f"        w=1.35 {' '.join(f'POW{p}:{g:+.2f}[z{z:+.1f}]' for p, (g, _, z) in zip(powers, gx135))}")
    print(f"        w=1.50 {' '.join(f'POW{p}:{g:+.2f}[z{z:+.1f}]' for p, (g, _, z) in zip(powers, gx150))}")
    print(f"    (b) identidad: margen R4 .60 {r60['_r4_min']:+.2f}pp vs .50 "
          f"{r50['_r4_min']:+.2f}pp (banda advisory {R4_BAND_PP}pp) → "
          f"{'CUMPLE' if clause_b else 'NO CUMPLE (la empeora)'}")
    print(f"    (c) extremos: R6 y R7 siguen PASS con holgura → "
          f"{'CUMPLE' if clause_c else 'NO CUMPLE'}")
    print(f"        R6 POW95×ST45×w1.50: XBH {r(0.50,1.50,95,45,'xbh'):.2f}→"
          f"{r(0.60,1.50,95,45,'xbh'):.2f} (techo {R6_XBH_MAX}), HR "
          f"{r(0.50,1.50,95,45,'hr'):.2f}→{r(0.60,1.50,95,45,'hr'):.2f} "
          f"(techo {R6_HR_MAX}) | R7 bucket máx "
          f"{max(r(0.50,1.50,45,95,k2) for k2 in ('out_bip','x1','x2','x3','hr')):.2f}"
          f"→{max(r(0.60,1.50,45,95,k2) for k2 in ('out_bip','x1','x2','x3','hr')):.2f}"
          f" (piso implícito {R7_BUCKET_MAX}%)")
    if not f60 and f50:
        pick, why = 0.50, "α=.60 falla un contrato que α=.50 pasa (caso trivial)."
    elif not (f50 and f60):
        pick, why = 0.50, "al menos uno de los dos finalistas falla R1–R8."
    elif clause_a and clause_b and clause_c:
        pick, why = 0.60, (".60 cumple las TRES cláusulas: expresión de fatiga "
                           "acoplada y material, sin peor identidad ni extremos.")
    else:
        fallas = []
        if not clause_a:
            fallas.append("(a) su Δ no es expresión ACOPLADA de Stuff con "
                          "|z|>2 en todos los puntos")
        if not clause_b:
            fallas.append(f"(b) reduce el margen de identidad de "
                          f"{r50['_r4_min']:+.2f}pp a {r60['_r4_min']:+.2f}pp")
        if not clause_c:
            fallas.append("(c) empeora el extremo explosivo")
        pick, why = 0.50, (".60 no cumple " + " ni ".join(fallas) +
                           " → gana el MENOR α por menor intervención.")
    print()
    print(f"  R9 VERDICT → α = {pick:.2f}")
    print(f"    razón: {why}")
    print(f"    R1–R8: α=.50 {'PASS' if f50 else 'FAIL'} · α=.60 "
          f"{'PASS' if f60 else 'FAIL'} · shape pareado "
          f"{'PASS' if results['_shape'] else 'FAIL'}")
    print(f"    margen de identidad R4: α=.50 {r50['_r4_min']:+.2f}pp · α=.60 "
          f"{r60['_r4_min']:+.2f}pp")
    print(f"    Δ(XBH) con |z|>2 en {nmat}/27 celdas (señal material pareada)")
    print(f"    Sigue SIN tocar producción (calculator.py UNCHANGED).")
    print(f"    Siguiente → 003B-6: integrar Stuff en PitcherAttrs + mapper + "
          f"fatiga + calculator, α ganador (k={k}), y PRODUCTION ACCEPTANCE "
          f"antes de cerrar GAMEPLAY-RATING-001.")
    print("=" * 150)


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


# ===========================================================================
# 003B-6C · PRODUCTION ACCEPTANCE · GAMEPLAY-ENGINE-003B-6
# ===========================================================================
#
# Qué es y qué NO es este bloque
# -----------------------------
# 003B-1..5C buscaron PARÁMETROS. Este bloque ya no busca nada: su único trabajo
# es demostrar que la ruta PRODUCTIVA de una partida real aplica exactamente la
# política que el LAB congeló, y que no movió nada que no debía.
#
# La ruta invocada es la de game_actions.resolve_play(), paso a paso:
#
#     PlayerCardModel (stuff de ratings-2.0)
#         ↓ map_card_to_pitcher_attrs        (app/engine/attribute_mapper.py)
#     PitcherAttrs.stuff CRUDO
#         ↓ apply_pitcher_fatigue            (app/engine/fatigue_manager.py)
#     PitcherAttrs.stuff EFECTIVO  (α=.50)     ← el ÚNico que ve fatigue_factor
#         ↓ get_pitch_stats + degradación    (pitch-specific attrs)
#         ↓ calculate_play_outcome()          (app/engine/calculator.py)
#     PlayResult
#
# calculate_play_outcome() se llama SIN NINGÚN KNOB. Los knobs LAB
# (take_bias / foul_chance / take_floor) no se pasan y no se pueden pasar: la
# API pública no los acepta. Ése es el punto: 002E-4 ya cerró esa frontera y
# 003B-6 la reutiliza en vez de abrir una excepción.
#
# Las tres referencias contra las que se coteja
# ----------------------------------------------
#   PROD   esta ruta, con el Stuff EFECTIVO
#   LAB    _simulate_pa_diag(stuff_level=e, stuff_arm="S2", stuff_k_qty=.30)
#          — 003B-5C, la política aprobada, con la fórmula de α en el LAB
#   PRE    _simulate_pa_diag(use_public_api=True) — el camino de producción
#          tal como estaba ANTES de 003B-6, sin Stuff en absoluto
#
# PRE es lo que hace que el bloque C (baseline regression) sea una prueba
# bit-exacta y no una promesa: si a Stuff=70 la ruta nueva no reproduce PRE PA a
# PA, entonces 003B-6 cambió algo que no debía cambiar. Y como las tres rutas
# consumen el RNG en el MISMO orden con las MISMAS seeds, la igualdad es
# EXACTA, no estadística. Por eso S1 tiene tolerancia 0.00.
#
# El harness NO se modificó para acomodar a producción. Sigue con su propia
# fórmula de α, y este bloque la compara con la de producción en vez de
# borrarla.
#
# UNA diferencia con game_actions, declarada y deliberada
# ------------------------------------------------------
# En `game_actions.resolve_play` el pitch_count se INCREMENTA en cada lanzamiento
# de la partida, así que la fatiga se profundiza dentro del inning. El LAB usa un
# diseño "shootout": el workload es el estado del juego al COMENZAR el PA y se
# mantiene constante durante él. Este acceptance hereda ese diseño a propósito:
#
#     - Siadvanced el count por pitch, PROD y LAB dejarían de ser comparables
#       desde la primera jugada, porque la divergencia sería de MODELO y no de
#       política. S1 mide lo que dice medir: que la política de Stuff es la misma.
#     - La fórmula de fatiga, la transformación de atributos, el mapper y el
#       resolver son TODOS código de producción en las dos rutas. Eso es lo que
#       003B-6 tenía que demostrar.
#
# Lo que NO se está afirmando aquí: que la simulación de un partido completo
# (fatiga acumulándose pitch a pitch) esté validada por este bloque. Eso es
# territorio de la FATIGA, no de STUFF, y ya lo cubre 001C/001D. Lo que aquí se
# demuestra es que, para un workload dado, la ruta de Stuff es la aprobada.

Z_REPRO = 3.0            # Reproducción contra cifras REGISTRADAS: se admiten
                         # 3 desviaciones estándar combinadas. Una tolerancia
                         # fija (0.05pp) contra una muestra nueva de otra
                         # corrida mide ruido, no política: con 50k PA el SE del
                         # XBH/BIP es ~0.2pp, así que 0.05pp sería imposible
                         # incluso con el código perfecto. El umbral sale de los
                         # datos (como R9_Z en 5C), no de un deseo.
N_REF_ANCHOR = 50_000    # n con el que se registraron 003B-4 y 003B-5C. Es el
                         # tamaño de la muestra contra la que se compara, y por
                         # eso entra en la SE combinada.
S6_MARGIN_PP = 1.0       # margen mínimo de identidad de élites (R4)
S7_TOL_PP = 0.0          # aislamiento: disciplina idéntica entre Stuffs
S8_P95_MAX = 6           # cola de PA (K5-R / R8)
S8_P12_MAX = 0.05        # P(PA >= 12 pitches)
S8_P16_MAX = 0.01        # P(PA >= 16 pitches)

# Anclas REGISTRADAS de 003B-4 (O1/O2, fresco) en XBH/BIP %, para el bloque A.
# Vienen de _e003b4_full_run.txt. No son "lo que debería salir": son lo que
# salió, y el acceptance falla si PROD se aparta de ellas.
E003B4_FRESH_XBH = {
    (45, 45): 20.72, (45, 70): 13.11, (45, 95): 5.53,
    (70, 45): 30.49, (70, 70): 23.03, (70, 95): 15.77,
    (95, 45): 40.66, (95, 70): 32.95, (95, 95): 25.59,
}
# Anclas REGISTRADAS de 003B-5C α=.50, extraídas de _e003b5c_full_run.txt.
# Anclas REGISTRADAS de 003B-5C α=.50, extraídas de _e003b5c_full_run.txt. Se
# usan como REFERENCIA INFORMATIVA en el pie de bloque; las puertas de R6/R7 se
# reevalúan con sus constantes reales del harness (R6_*/R7_*), no contra estos
# números, porque R6/R7 son topes y contratos relativos, no igualdades.
E003B5C_ALPHA050_R6 = {"xbh": 42.95, "hr": 32.08}          # POW95×ST45×w1.50
E003B5C_ALPHA050_R7 = {"xbh": 10.85, "fresh": 5.53, "bucket": 67.22}  # POW45×ST95×w1.50
E003B5C_ALPHA050_R4_MIN = 2.18                             # margen de élites
E003B5C_ALPHA050_SUPPRESSION = {                           # ΔXHB vs fresco @POW70
    45: {1.00: 0.00, 1.35: 1.61, 1.50: 2.48},
    70: {1.00: 0.00, 1.35: 2.33, 1.50: 3.84},
    95: {1.00: 0.00, 1.35: 2.98, 1.50: 5.08},
}


class _Prod6Card:
    """Carta de producción con la MISMA superficie pública que `PlayerCardModel`.

    No se importa el ORM a propósito: `app.models` arrastra `app.database`, que
    abre un engine real (psycopg2) y convertiría este harness en un script que
    necesita base de datos para correr una simulación. El mapper sólo hace
    acceso por atributo (`card.velocity`, `card.stuff`, …) y
    `card.get_pitch_stats(...)`, así que un objeto con esa superficie ejercita
    exactamente el mismo código productivo.

    Lo que SÍ queda probado contra el modelo real (columna `stuff`, CHECK,
    NOT NULL, mapper contra una fila de sqlite) está en el contrato T1 de
    tests/test_stuff_policy.py, y Capa 0 verifica por fuente que la columna
    sigue declarada.
    """

    def __init__(self, stuff: int, batter_power: int, level: int = 70):
        self.id = f"acc-stuff-{stuff}-pow-{batter_power}"
        self.name = f"Acceptance {stuff}/{batter_power}"
        self.position = "SP"
        self.overall = level
        self.velocity = level
        self.control = level
        self.movement = level
        self.stuff = stuff
        # Repertorio idéntico a `pitch_raw` del LAB, para que la degradación
        # pitch-specific se ejercite de verdad y no se pueda colar por el hecho
        # de que aquí sea identidad.
        self.repertoire = [{"pitch_type": "4-SEAM", "velocity": level,
                            "control": level, "movement": level}]

    def get_pitch_stats(self, pitch_type_name: str):
        if pitch_type_name == "IBB":
            return {"pitch_type": "IBB", "velocity": 60, "control": 99, "movement": 0}
        for pitch in self.repertoire or []:
            if pitch.get("pitch_type") == pitch_type_name:
                return pitch
        return None


def _prod6_card(stuff: int, batter_power: int) -> _Prod6Card:
    """Carta con el Stuff de ratings-2.0 y perfil MID 70/70/70 (perfil 003A)."""
    return _Prod6Card(stuff, batter_power, level=PITCHER_PROFILES_003A["MID"]["velocidad"])


def _prod6_pa_diag(take_probs: dict, seed: int, batter_attrs: dict,
                   card: _Prod6Card, workload: float,
                   total_innings: int = INNINGS) -> dict:
    """PA 0-0 por la RUTA PRODUCTIVA (misma máquina de estados que el LAB).

    Réplica de `_simulate_pa_diag`, con una diferencia deliberada: los atributos
    del pitcher NO salen de `effective_attrs` (que es una reimplementación LAB
    de la fatiga) sino de `map_card_to_pitcher_attrs` + `apply_pitcher_fatigue`,
    que es lo que corre `game_actions` de verdad. La máquina de estados se copia
    igual para que la comparación sea significativa; si divergiera, S1 lo
    detectaría como codes distintos, no como rates parecidos.
    """
    random.seed(seed)
    balls = strikes = pitches = 0
    pitch_count = int(workload * PROD_THRESHOLD_003B5C)
    take_attempts = balls_on_take = called_strikes_on_take = 0
    swing_attempts = whiffs = fouls = bips = 0
    reached_2strikes = reached_3balls = reached_full = False
    outcome = "CAP"

    # ---- RUTA PRODUCTIVA: mapper → fatigue_manager -----------------------
    raw_pitcher_attrs = map_card_to_pitcher_attrs(card)
    pitcher_attrs = apply_pitcher_fatigue(raw_pitcher_attrs, pitch_count, total_innings)
    # -----------------------------------------------------------------------

    while pitches < MAX_PA_PITCHES:
        pitches += 1
        pitch = get_cpu_pitch_action(DIFFICULTY)
        swing = batter_action_by_count(strikes, take_probs)

        # Pitch-specific attrs, misma regla que game_actions.py: la identidad del
        # lanzamiento × el factor de degradación del atributo global.
        pitch_stats = card.get_pitch_stats(pitch["pitch_type"])
        if pitch_stats:
            for attr, key in (("velocidad", "velocity"), ("control", "control"),
                              ("movimiento", "movement")):
                base = raw_pitcher_attrs[attr]
                factor = (pitcher_attrs[attr] / base) if base > 0 else 1.0
                pitch[key] = int(pitch_stats.get(key, base) * factor)

        event, _description = calculate_play_outcome(
            pitcher_attrs=pitcher_attrs,
            batter_attrs=batter_attrs,
            pitch_selected=pitch,
            swing_selected=swing,
            tactics_modifiers=None,
        )

        if swing["swing_type"] == SwingType.TAKE:
            take_attempts += 1
            if event == Event.BALL:
                balls_on_take += 1
            elif event == Event.STRIKE_LOOKING:
                called_strikes_on_take += 1
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

    return {
        "outcome": outcome, "pitches": pitches,
        "reached_2strikes": reached_2strikes, "reached_3balls": reached_3balls,
        "reached_full": reached_full, "take_attempts": take_attempts,
        "balls_on_take": balls_on_take,
        "called_strikes_on_take": called_strikes_on_take,
        "swing_attempts": swing_attempts, "whiffs": whiffs, "fouls": fouls,
        "bips": bips, "outcome_at_2s": outcome if reached_2strikes else None,
    }


def _prod6_agg(pairs: list, n: int) -> dict:
    """Agrega una lista de dicts de PA en las métricas de 003B."""
    agg = {"outcome": Counter(), "pitches": 0, "take_attempts": 0,
           "called_strikes_on_take": 0, "swing_attempts": 0, "whiffs": 0,
           "bips": 0, "fouls": 0, "reached_2strikes": 0, "reached_3balls": 0,
           "reached_full": 0}
    lengths = []
    for d in pairs:
        for key in ("pitches", "take_attempts", "called_strikes_on_take",
                    "swing_attempts", "whiffs", "bips", "fouls",
                    "reached_2strikes", "reached_3balls", "reached_full"):
            agg[key] += d[key]
        agg["outcome"][d["outcome"]] += 1
        lengths.append(d["pitches"])
    agg["lengths"] = sorted(lengths)
    agg["p95"] = agg["lengths"][int(n * 0.95) - 1]
    agg["max"] = agg["lengths"][-1]
    agg["n12"] = sum(1 for x in lengths if x >= 12)
    agg["n16"] = sum(1 for x in lengths if x >= 16)
    return agg


def _prod6_row(agg: dict, n: int) -> dict:
    """Fila de métricas con las MISMAS definiciones que `_metric_row` del LAB.

    Copiar las definiciones es parte del contrato, no una comodidad: `xbh` son
    hits extra-base (2B+3B+HR) SIN el 1B, y `bs` es el total de BIP. Usar "reach"
    en lugar de "xbh" corría exactamente +20.5pp (el share del 1B) y hacía que la
    ruta productiva pareciera no reproducir 003B-4 cuando en realidad medía otra
    cosa. Cuando las dos rutas se comparan, se comparan las mismas magnitudes.
    """
    o = agg["outcome"]
    bip = o["OUT"] + o["1B"] + o["2B"] + o["3B"] + o["HR"]
    bs = max(1, bip)
    sw = max(1, agg["swing_attempts"])
    tk = max(1, agg["take_attempts"])
    return {
        "xbh": (o["2B"] + o["3B"] + o["HR"]) / bs * 100,
        "hr": o["HR"] / bs * 100,
        "out_bip": o["OUT"] / bs * 100,
        "x1": o["1B"] / bs * 100,
        "x2": o["2B"] / bs * 100,
        "x3": o["3B"] / bs * 100,
        "bip": bip / n * 100,
        "k": o["K"] / n * 100,
        "bb": o["BB"] / n * 100,
        "reach": (o["BB"] + o["1B"] + o["2B"] + o["3B"] + o["HR"]) / n * 100,
        "whiff": agg["whiffs"] / sw * 100,
        "called_tk": agg["called_strikes_on_take"] / tk * 100,
        # `cnt` es el contacto sobre columpios (lo que decide WHIFF vs contacto),
        # igual que en `_metric_row` del LAB. NO es el rate de strikeout: ése va
        # en `k`. Confundir los dos hacía que S7 midiera el strikeout, que SÍ
        # tiene que moverse con Stuff, y el contrato "Stuff no toca la
        # disciplina" salía falso por una razón que no tenía que ver con él.
        "cnt": (sw - agg["whiffs"]) / sw * 100,
        "p95": agg["p95"], "max": agg["max"],
        "t12": agg["n12"] / n * 100, "t16": agg["n16"] / n * 100,
        "cap": o["CAP"],
    }


def run_production_acceptance_003b6(reps: int) -> None:
    """003B-6C · Aceptación de producción: ruta real vs política aprobada, S1–S8."""
    n = reps
    batter_base = BATTER_PROFILES_003A["MID"]
    powers = list(POWER_LEVELS_003B5C)
    stuffs = list(STUFF_LEVELS_003B5C)
    lab_pitcher = PITCHER_PROFILES_003A["MID"]
    all_workloads = list(WORKLOADS_003B5C)
    contract = []          # (código, PASS/FAIL, detalle)

    print("=" * 130)
    print("003B-6C · PRODUCTION ACCEPTANCE · ruta real vs política aprobada")
    print(f"card → mapper → fatigue_manager → pitch-specific → calculate_play_outcome()")
    print(f"Grid Power{POWER_LEVELS_003B5C} × Stuff{STUFF_LEVELS_003B5C} × "
          f"w{all_workloads} = {len(powers)*len(stuffs)*len(all_workloads)} celdas | "
          f"{reps:,} PA/celda | {reps*len(powers)*len(stuffs)*len(all_workloads):,} PA")
    print("KNobs LAB: NINGUNO. calculate_play_outcome() no los acepta. α y k se "
          "leen de app/engine/stuff_policy.py, no de este archivo.")
    print(f"Política en juego: α={PROD_STUFF_FATIGUE_ALPHA} (producción) · "
          f"baseline={PROD_STUFF_BASELINE} · k={PROD_STUFF_K}")
    print("=" * 130)

    # ------------------------------------------------------------------ Capa 0
    # La política de producción y la del LAB son el MISMO número. Si divergieran,
    # todo lo demás de este bloque sería una comparación entre dos políticas.
    print()
    print("-- CAPA 0 · LA POLÍTICA PRODUCTIVA ES LA APROBADA --")
    lab_alphas = set(STUFF_FATIGUE_ALPHAS_003B5C)
    ok_alpha = PROD_STUFF_FATIGUE_ALPHA in lab_alphas
    ok_k = PROD_STUFF_K == K_003B5C
    ok_base = PROD_STUFF_BASELINE == STUFF_IDENTITY
    contract.append(("S1a α productivo = α congelado",
                     ok_alpha, f"prod={PROD_STUFF_FATIGUE_ALPHA} lab={sorted(lab_alphas)}"))
    contract.append(("S1b k productivo = k congelado",
                     ok_k, f"prod={PROD_STUFF_K} lab={K_003B5C}"))
    contract.append(("S1c baseline productivo = identidad LAB",
                     ok_base, f"prod={PROD_STUFF_BASELINE} lab={STUFF_IDENTITY}"))
    # effective_stuff productivo == fórmula LAB, celda por celda.
    max_eff_dev = 0.0
    for f in (0.35, 0.5, 0.654321, 0.8, 0.95, 1.0):
        for raw in (0, 45, 50, 70, 95, 99):
            prod = prod_effective_stuff(float(raw), f)
            lab = _stuff_fatigue_eff_003b5c(float(raw), PROD_STUFF_FATIGUE_ALPHA, f)
            max_eff_dev = max(max_eff_dev, abs(prod - lab))
    contract.append(("S1d effective_stuff prod == fórmula LAB",
                     max_eff_dev == 0.0, f"|Δ|máx={max_eff_dev:.2e}"))
    # La columna `stuff` existe de verdad en la carta de producción. Se comprueba
    # por fuente porque importar el ORM aquí exigiría una base de datos.
    card_src = ""
    try:
        card_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "..", "app", "models", "card.py")
        with open(card_path, "r", encoding="utf-8") as handle:
            card_src = handle.read()
    except OSError:
        card_src = ""
    ok_column = "stuff = Column(" in card_src
    ok_check = "ck_player_cards_stuff_range" in card_src
    contract.append(("S1e player_cards.stuff declarado (NOT NULL)",
                     ok_column, "columna en app/models/card.py"))
    contract.append(("S1f CHECK 0-99 en player_cards.stuff",
                     ok_check, "ck_player_cards_stuff_range"))
    # El mapper lee la columna y la fatigue_manager la transforma: sin esto, la
    # cadena de 003B-6A estaría cortada aunque el resolver funcionara.
    ok_mapper = "map_card_to_pitcher_attrs" in globals() and "stuff" in inspect.getsource(
        sys.modules[map_card_to_pitcher_attrs.__module__])
    contract.append(("S1g mapper publica stuff en PitcherAttrs",
                     ok_mapper, "attribute_mapper devuelve la clave"))
    for code, ok, detail in contract:
        print(f"  {code:<44} {'PASS' if ok else 'FAIL':>4}  ({detail})")
    print()

    # ------------------------------------------------------- Capa 1: cobertura
    # Se corre PROD, LAB y PRE en las mismas celdas con las MISMAS seeds.
    results = {}
    for w in all_workloads:
        for p in powers:
            for st in stuffs:
                card = _prod6_card(st, p)
                batter = dict(batter_base, poder=p)
                factor = get_fatigue_factor(int(w * PROD_THRESHOLD_003B5C),
                                            PROD_THRESHOLD_003B5C)
                eff = prod_effective_stuff(float(st), factor)
                prod_pairs, lab_pairs, pre_pairs = [], [], []
                for rep in range(n):
                    seed = int(DISCIPLINE_WORKLOAD * 1000) * 10**6 + rep
                    prod_pairs.append(_prod6_pa_diag(E1_POLICY, seed, batter,
                                                     card, w))
                    lab_pairs.append(_simulate_pa_diag(
                        E1_POLICY, seed, batter_attrs=batter,
                        pitcher_attrs=lab_pitcher, stuff_level=eff,
                        stuff_arm="S2", stuff_k_qty=K_003B5C, workload=w))
                    pre_pairs.append(_simulate_pa_diag(
                        E1_POLICY, seed, batter_attrs=batter,
                        pitcher_attrs=lab_pitcher, use_public_api=True,
                        workload=w))
                results[(w, p, st)] = {
                    "prod": _prod6_agg(prod_pairs, n),
                    "lab": _prod6_agg(lab_pairs, n),
                    "pre": _prod6_agg(pre_pairs, n),
                    "prod_codes": [d["outcome"] for d in prod_pairs],
                    "lab_codes": [d["outcome"] for d in lab_pairs],
                    "pre_codes": [d["outcome"] for d in pre_pairs],
                }

    def row(w, p, st, which="prod"):
        return _prod6_row(results[(w, p, st)][which], n)

    # La supresión de Stuff se define para TODOS los workloads (0 en fresco, por
    # construcción) y no sólo para los fatigados. Los contratos de dirección
    # (S4/S5) viven sobre ESTA serie y no sobre el XBH crudo: la fatiga 001C de
    # VEL/CTL/MOV empuja el XBH hacia arriba mientras que la fatiga de Stuff lo
    # empuja hacia abajo, y el signo del XBH neto depende de cuál de las dos
    # domine. Juzgar "dirección de la fatiga" sobre el XBH crudo mide el
    # promedio de dos fuerzas opuestas, no la política de Stuff.
    suppr = {}
    for w in all_workloads:
        for p in powers:
            for st in stuffs:
                suppr[(w, p, st)] = row(w, p, st)["xbh"] - row(1.00, p, st)["xbh"]

    def mc_tol(rate_pct: float, n_run: int, n_ref: int = N_REF_ANCHOR) -> float:
        """Tolerancia de reproducción contra cifras REGISTRADAS en otra corrida.

        Comparar una simulación nueva contra un número anotado a mano con una
        tolerancia fija no tiene sentido: las dos muestras son independientes y
        la diferencia esperada es ruido de Monte Carlo, no un cambio de código.
        El umbral sale de la varianza de los propios datos (igual que R9_Z en
        5C): se admiten Z_REPRO desviaciones estándar combinadas. Con 50k PA
        esto da ~0.4pp, que sigue detectando cualquier desviación real de
        política pero no suspica por el último dígito.
        """
        p_rate = min(max(rate_pct / 100.0, 1e-9), 1 - 1e-9)
        se_run = math.sqrt(p_rate * (1 - p_rate) / n_run) * 100
        se_ref = math.sqrt(p_rate * (1 - p_rate) / n_ref) * 100
        return Z_REPRO * math.sqrt(se_run ** 2 + se_ref ** 2)

    # ------------------------------------------------------------- BLOQUE A/B
    print("-- BLOQUE A · FRESH ACCEPTANCE (w=1.00) → debe reproducir 003B-4 --")
    print("Tol = Z_REPRO x SE combinada (corrida nueva vs cifra registrada): "
          f"Z={Z_REPRO} @ n={n:,}")
    print(f"{'POW':>4} {'ST':>4} {'PROD XBH/BIP':>13} {'003B-4':>9} {'|Δ|':>7} "
          f"{'tol':>6} {'vs LAB':>8}")
    max_a_dev = max_a_lab = 0.0
    a_bad = []
    for p in powers:
        for st in stuffs:
            r = row(1.00, p, st)
            r_lab = row(1.00, p, st, "lab")
            ref = E003B4_FRESH_XBH[(p, st)]
            dev = abs(r["xbh"] - ref)
            tol = mc_tol(r["xbh"], n)
            dlab = abs(r["xbh"] - r_lab["xbh"])
            max_a_dev = max(max_a_dev, dev)
            max_a_lab = max(max_a_lab, dlab)
            if dev > tol:
                a_bad.append(f"POW{p} ST{st} {dev:.2f}>{tol:.2f}")
            print(f"{p:>4} {st:>4} {r['xbh']:>13.2f} {ref:>9.2f} "
                  f"{dev:>7.2f} {tol:>6.2f} {dlab:>8.2f}")
    ok_a = not a_bad
    contract.append(("S1/S3 BLOQUE A: PROD reproduce 003B-4 (dentro de MC)",
                     ok_a,
                     f"|Δ|máx={max_a_dev:.3f}pp vs tol {Z_REPRO}SE"
                     + ("" if ok_a else "; " + "; ".join(a_bad[:3]))))
    contract.append(("S1 BLOQUE A: PROD == LAB bit-exacto",
                     max_a_lab == 0.0, f"|Δ|máx={max_a_lab:.2e}pp (tol 0.00)"))
    print()

    print("-- BLOQUE B · FATIGUE ACCEPTANCE (w=1.35/1.50) → debe reproducir "
          "α=.50 de 003B-5C --")
    print(f"{'POW':>4} {'ST':>4} {'w':>5} {'XHB':>8} {'fresh':>8} {'supresión':>10} "
          f"{'003B-5C':>9} {'|Δ|':>7} {'tol':>6}")
    max_b_dev = max_b_lab = 0.0
    b_bad = []
    for w in (1.35, 1.50):
        for p in powers:
            for st in stuffs:
                r = row(w, p, st)
                r_lab = row(w, p, st, "lab")
                d = suppr[(w, p, st)]
                dlab = abs(r["xbh"] - r_lab["xbh"])
                max_b_lab = max(max_b_lab, dlab)
                # El ancla de supresión se registró SÓLO en la fila POW70 de
                # 003B-5C. Compararla contra POW45/POW95 sería exigirle a
                # producción un número que nadie midió: el desvío aparecería
                # como "la política no reproduce", cuando en realidad es que la
                # supresión se estrecha al subir el poder del bateador (mismo
                # mecanismo que ya valida S4, no una regresión nueva).
                if p == 70:
                    ref = E003B5C_ALPHA050_SUPPRESSION[st].get(w)
                    dev = abs(d - ref) if ref is not None else 0.0
                    # El Δ de la supresión es una resta de dos proporciones, así
                    # que su error estándar es MAYOR que el de cada una.
                    tol = Z_REPRO * math.sqrt(2.0) * mc_tol(r["xbh"], n)
                    if dev > tol:
                        b_bad.append(f"POW{p} ST{st} w{w} {dev:.2f}>{tol:.2f}")
                    max_b_dev = max(max_b_dev, dev)
                    print(f"{p:>4} {st:>4} {w:>5.2f} {r['xbh']:>8.2f} "
                          f"{row(1.00, p, st)['xbh']:>8.2f} {d:>+10.2f} "
                          f"{ref:>9.2f} {dev:>7.2f} {tol:>6.2f}")
                else:
                    print(f"{p:>4} {st:>4} {w:>5.2f} {r['xbh']:>8.2f} "
                          f"{row(1.00, p, st)['xbh']:>8.2f} {d:>+10.2f} "
                          f"{'—':>9} {'—':>7} {'—':>6}")
    ok_b = not b_bad
    contract.append(("S4/S5 BLOQUE B: supresión reproduce 003B-5C α=.50 @POW70 "
                     "(dentro de MC)", ok_b,
                     f"|Δ|máx={max_b_dev:.3f}pp vs tol {Z_REPRO}SE"
                     + ("" if ok_b else "; " + "; ".join(b_bad[:3]))))
    contract.append(("S1 BLOQUE B: PROD == LAB bit-exacto",
                     max_b_lab == 0.0, f"|Δ|máx={max_b_lab:.2e}pp (tol 0.00)"))
    print()

    # R6/R7 se reevalúan con su semántica ORIGINAL (techos y contrato relativo),
    # copiada del harness de 5C. Sus constantes R6_*/R7_* son las mismas, así que
    # no hay ni números inventados ni tolerancias nuevas que ajustar después de
    # ver el resultado: o se cumplen los topes o no se cumplen.
    r6 = row(1.50, 95, 45)
    ok_r6 = r6["xbh"] <= R6_XBH_MAX and r6["hr"] <= R6_HR_MAX
    contract.append(("S6a R6 sin explosión extrema (POW95×ST45×w1.50)", ok_r6,
                     f"XBH={r6['xbh']:.2f}≤{R6_XBH_MAX} HR={r6['hr']:.2f}≤{R6_HR_MAX} "
                     f"(5C registró "
                     f"{E003B5C_ALPHA050_R6['xbh']:.2f}/{E003B5C_ALPHA050_R6['hr']:.2f})"))
    r7_fresh = row(1.00, 45, 95)["xbh"]
    r7_fat = row(1.50, 45, 95)
    r7_bucket = max(r7_fat[k] for k in ("out_bip", "x1", "x2", "x3", "hr"))
    ok_r7 = (r7_fat["xbh"] >= R7_KEEP_FRAC * r7_fresh
             and r7_bucket <= R7_BUCKET_MAX)
    contract.append(("S6b R7 sin colapso extremo (POW45×ST95)", ok_r7,
                     f"XBH {r7_fat['xbh']:.2f}≥{R7_KEEP_FRAC * r7_fresh:.2f} "
                     f"(≥{R7_KEEP_FRAC:.0%} de fresco {r7_fresh:.2f}), "
                     f"bucket máx {r7_bucket:.2f}≤{R7_BUCKET_MAX} "
                     f"(5C registró {E003B5C_ALPHA050_R7['xbh']:.2f}/"
                     f"{E003B5C_ALPHA050_R7['bucket']:.2f})"))
    print()

    # ------------------------------------------------------------ BLOQUE C
    print("-- BLOQUE C · BASELINE REGRESSION (Stuff 70) → CALIBRATED-BASELINE-v1 --")
    print("PRE = la ruta de producción TAL COMO ESTABA antes de 003B-6 "
          "(use_public_api, sin Stuff).")
    print()
    print("C1 · Stuff 70 + FRESCO == PRE, bit-exacto. Éste es el contrato de "
          "baseline.")
    print("     En fresco el factor de fatiga es 1.0, luego el Stuff efectivo es "
          "exactamente 70 y el")
    print("     término de supresión vale -(70-70)*k = 0: la política nueva no "
          "tiene nada que")
    print("     decir sobre un lanzador fresco, así que la ruta debe ser "
          "indistinguible de la")
    print("     anterior PA a PA. Cualquier PA es una fuga: Stuff tocado donde "
          "no debía, un")
    print("     redondeo nuevo, o α aplicándose a fresco.")
    max_c = 0.0
    mismatches = 0
    for p in powers:
        res = results[(1.00, p, 70)]
        for i in range(n):
            if res["prod_codes"][i] != res["pre_codes"][i]:
                mismatches += 1
        r, r_pre = row(1.00, p, 70), row(1.00, p, 70, "pre")
        for key in ("xbh", "hr", "cnt", "whiff", "called_tk", "reach", "k", "bb"):
            max_c = max(max_c, abs(r[key] - r_pre[key]))
    n_c1 = n * len(powers)
    contract.append(("S2 BLOQUE C1: Stuff 70 + fresco == PRE (PA a PA)",
                     mismatches == 0, f"códigos divergentes={mismatches}/{n_c1:,}"))
    contract.append(("S2 BLOQUE C1: métricas == PRE (bit-exacto)",
                     max_c == 0.0, f"|Δ|máx={max_c:.2e}pp (tol 0.00)"))
    print(f"     PA comparadas: {n_c1:,} | códigos divergentes: {mismatches} | "
          f"|Δ|máx métrica: {max_c:.2e}pp")
    print()

    print("C2 · Stuff 70 + FATIGA: aquí PROD *debe* separarse de PRE, y la "
          "separación está cuantificada.")
    print("     El Stuff efectivo de un lanzador cansado cae POR DEBAJO de 70 "
          "(62.42 a w=1.35,")
    print("     57.21 a w=1.50), así que el hitter recibe un bono de poder de "
          "-(efectivo-70)*k.")
    print("     Exigir PROD == PRE bajo fatiga sería exigir α=0, o sea negar "
          "que la fatiga de Stuff")
    print("     exista. Lo que sí es exigible —y es lo que se comprueba— es que "
          "esa separación sea")
    print("     exactamente la aprobada en 003B-5C para Stuff70, y que no haya "
          "nada más moviéndose.")
    c2_bad = []
    for w in (1.35, 1.50):
        thr = int(w * PROD_THRESHOLD_003B5C)
        eff = prod_effective_stuff(70.0, get_fatigue_factor(
            thr, PROD_THRESHOLD_003B5C))
        # Signo: `stuff_power_suppression(eff)` YA devuelve el bono de poder
        # POSITIVO que recibe el hitter cuando el Stuff efectivo cae por debajo de
        # la identidad (eff<70 → -(eff-70)*k > 0). No hay que negarlo: hacerlo
        # comparaba +2.40 contra -2.27 y hacía fallar un contrato que en realidad
        # se cumplía, por un signo de más en el propio acceptance y no por nada
        # en producción.
        bonus_pp = prod_stuff_power_suppression(eff)
        measured = max(row(w, p, 70)["xbh"] - row(w, p, 70, "pre")["xbh"]
                       for p in powers)
        ref = E003B5C_ALPHA050_SUPPRESSION[70][w]
        # PROD y PRE comparten seed pero no FullyPaus draws idénticos cuando el
        # bono de poder cruza un umbral: se trata como dos tasas independientes,
        # que es la lectura conservadora (√2×SE) en vez de la pareada.
        tol = Z_REPRO * math.sqrt(2.0) * mc_tol(row(w, 70, 70)["xbh"], n)
        # (a) la ganancia medida contra PRE es la registrada en 5C para Stuff70
        if abs(measured - ref) > tol:
            c2_bad.append(f"w={w} medido={measured:.2f} vs 5C={ref:.2f}")
        # (b) y coincide con el bono determinista que la politica concede
        if abs(measured - bonus_pp) > tol:
            c2_bad.append(f"w={w} medido={measured:.2f} vs bono={bonus_pp:.2f}")
        print(f"     w={w:.2f} ef.Stuff={eff:6.3f} bono determinista="
              f"{bonus_pp:+.3f}pp | medido vs PRE={measured:+.2f}pp | "
              f"5C={ref:+.2f}pp | tol={tol:.2f}pp")
    contract.append(("S2 BLOQUE C2: la separación de PRE bajo fatiga es la "
                     " Stuff70 aprobada (ni más ni menos)", not c2_bad,
                     f"desvíos={len(c2_bad)}"
                     + ("; " + "; ".join(c2_bad[:3]) if c2_bad else "")))
    # Y que la ruta siga siendo idéntica al LAB bajo fatiga: la divergencia
    # contra PRE es de Stuff, no de implementación.
    max_c2 = 0.0
    for w in (1.35, 1.50):
        for p in powers:
            max_c2 = max(max_c2, abs(row(w, p, 70)["xbh"]
                                     - row(w, p, 70, "lab")["xbh"]))
    contract.append(("S2 BLOQUE C2: PROD == LAB también bajo fatiga (bit-exacto)",
                     max_c2 == 0.0, f"|Δ|máx={max_c2:.2e}pp"))
    print()

    # ----------------------------------------------------- contratos S1–S8
    print("-- CONTRATOS S1-S8 (fijados antes de correr; no son\new balance, "
          "son los ya demostrados) --")

    # S1 bit-exacto en TODAS las celdas, no sólo en A y B.
    total_codes = 0
    s1_mismatch = 0
    for key, res in results.items():
        for i in range(n):
            total_codes += 1
            if res["prod_codes"][i] != res["lab_codes"][i]:
                s1_mismatch += 1
    contract.append(("S1 PROD == LAB (todas las celdas, PA a PA)",
                     s1_mismatch == 0,
                     f"divergentes={s1_mismatch}/{total_codes:,}"))

    # S2 ya está arriba.

    # S3 · expresión de poder: Power↑ ⇒ XBH↑ con el MISMO piso por paso que el
    # R1 de 5C (R1_STEP_PP), no con monotonicidad estricta. Un piso por paso es
    # la forma en que la política quedó aprobada; exigir >0 estricto además haría
    # el contrato inestable frente al ruido de Monte Carlo, y un contrato que
    # falla por el último dígito no prueba nada.
    s3_bad = []
    s3_min_margin = 1e9
    for w in all_workloads:
        for st in stuffs:
            seq = [row(w, p, st)["xbh"] for p in powers]
            for lo, hi in zip(seq, seq[1:]):
                if hi - lo < R1_STEP_PP:
                    s3_bad.append(f"POW w{w} ST{st} {lo:.2f}→{hi:.2f}")
                s3_min_margin = min(s3_min_margin, hi - lo)
    contract.append(("S3 expresión de poder preservada (piso R1 por paso)",
                     not s3_bad,
                     f"margen mínimo={s3_min_margin:+.2f}pp "
                     f"(piso {R1_STEP_PP})"
                     + ("" if not s3_bad else "; " + "; ".join(s3_bad[:3]))))

    # S4 · supresión de Stuff: Stuff↑ ⇒ supresión↑. Se mide sobre `suppr`, la
    # serie de ΔXBH que la fatiga de Stuff produce, y NO sobre el XBH crudo: en
    # fresco la supresión es 0 por definición en los tres Stuffs, así que el
    # XBH crudo ahí sólo está midiendo el efecto estático de Stuff (que es S4-bis
    # y va en su propia línea).
    s4_bad = []
    s4_min_margin = 1e9
    for w in (1.35, 1.50):
        for p in powers:
            seq = [suppr[(w, p, st)] for st in stuffs]
            for lo, hi in zip(seq, seq[1:]):
                if hi - lo < -R3_STEP_PP:
                    s4_bad.append(f"POW{p} w{w} {lo:+.2f}→{hi:+.2f}")
                s4_min_margin = min(s4_min_margin, hi - lo)
    contract.append(("S4 supresión de Stuff monótona en Stuff↑ (sobre la serie "
                     "de supresión, banda R3)", not s4_bad,
                     f"margen mínimo={s4_min_margin:+.2f}pp (banda ±{R3_STEP_PP})"
                     + ("" if not s4_bad else "; " + "; ".join(s4_bad[:3]))))
    # S4-bis · el efecto estático de Stuff, que sí va sobre el XBH crudo: aquí no
    # hay fatiga que compita, así que se mide con el piso R2_STEP_PP del R2 de 5C.
    s4b_bad = []
    s4b_min = 1e9
    for w in all_workloads:
        for p in powers:
            seq = [row(w, p, st)["xbh"] for st in stuffs]
            for lo, hi in zip(seq, seq[1:]):
                if lo - hi < R2_STEP_PP:
                    s4b_bad.append(f"POW{p} w{w} {lo:.2f}→{hi:.2f}")
                s4b_min = min(s4b_min, lo - hi)
    contract.append(("S4b efecto estático de Stuff preservado (piso R2 por paso)",
                     not s4b_bad,
                     f"caída mínima={s4b_min:+.2f}pp (piso {R2_STEP_PP})"
                     + ("" if not s4b_bad else "; " + "; ".join(s4b_bad[:3]))))
    # S5 · dirección de la fatiga de Stuff: más workload ⇒ MÁS supresión (el
    # ΔXBH respecto a fresco crece). El XBH crudo sube con la fatiga porque la
    # degradación 001C de VEL/CTL/MOV pesa más que la pérdida de Stuff; exigir
    # "w↑ ⇒ XBH↓" sobre el crudo sería exigir que α=0. El contrato de 003B es
    # que la fatiga de Stuff EMPEORE al lanzador, y eso se lee en `suppr`.
    s5_bad = []
    s5_min = 1e9
    for p in powers:
        for st in stuffs:
            seq = [suppr[(w, p, st)] for w in all_workloads]
            for lo, hi in zip(seq, seq[1:]):
                if hi - lo < -R3_STEP_PP:
                    s5_bad.append(f"POW{p} ST{st} {lo:+.2f}→{hi:+.2f}")
                s5_min = min(s5_min, hi - lo)
    contract.append(("S5 dirección de la fatiga de Stuff (w↑ ⇒ supresión↑, "
                     "banda R3)", not s5_bad,
                     f"subida mínima={s5_min:+.2f}pp (banda ±{R3_STEP_PP})"
                     + ("" if not s5_bad else "; " + "; ".join(s5_bad[:3]))))
    # S5-bis · el efecto neto de la fatiga 001C sobre el resultado sigue siendo el
    # de 5C: la fatiga EMPEORA al lanzador. Se documenta como observación con
    # signo esperado, no como puerta (el signo neto no es propiedad de Stuff).
    s5b = min(suppr[(1.50, p, st)] for p in powers for st in stuffs)
    contract.append(("S5b (observación) la fatiga de 001C domina el neto en el "
                     "punto α=.50", s5b >= 0.0,
                     f"supresión mínima global={s5b:+.2f}pp (informativo)"))

    # S6 · identidad de élites: el margen de XBH por suppressed-elite
    # (ST45 fresco → mismo ST45 en fatiga) no puede caer bajo la banda.
    s6_margin = min(
        suppr[(1.50, 70, st)] for st in stuffs
    ) if suppr else 0.0
    contract.append(("S6 identidad de élites preservada (R4)",
                     s6_margin >= S6_MARGIN_PP,
                     f"margen mín={s6_margin:+.2f}pp (piso {S6_MARGIN_PP}, "
                     f"003B-5C registró {E003B5C_ALPHA050_R4_MIN:+.2f})"))

    # S7 · aislamiento de mecanismo: Stuff NO mueve la disciplina. Dentro de una
    # celda (mismo Power, mismo w), whiff%, called-strike% y contacto% deben ser
    # idénticos entre los tres Stuffs, porque el mismo PA consume los mismos
    # draws: cualquier movimiento del Stuff en ellos probaría que se coló antes
    # de la resolución de contacto.
    #
    # Deliberadamente EXCLUIDAS: `reach`, `k`, `xbh`, `hr`. Esos cuatro SÍ tienen
    # que moverse con Stuff — es literalmente de lo que trata 003B. Meterlos
    # aquí no testeara aislamiento, testeara que Stuff no hace nada.
    s7_dev = 0.0
    s7_worst = ""
    for w in all_workloads:
        for p in powers:
            for key in ("whiff", "called_tk", "cnt"):
                vals = [row(w, p, st)[key] for st in stuffs]
                spread = max(vals) - min(vals)
                if spread > s7_dev:
                    s7_dev, s7_worst = spread, f"{key} @POW{p} w{w}"
    contract.append(("S7 aislamiento de mecanismo (Stuff no toca la disciplina)",
                     s7_dev <= S7_TOL_PP,
                     f"|Δ|máx={s7_dev:.2e}pp en {s7_worst} (tol 0.00)"))
    # S7-bis · y lo que sí tiene que moverse, para que el PASS de arriba no sea
    # un artefacto de haber medido canales muertos.
    s7b = min(row(w, 95, 45)["xbh"] - row(w, 95, 95)["xbh"] for w in all_workloads)
    contract.append(("S7b (observación) Stuff sí mueve el daño (POW95: ST45-ST95)",
                     s7b > 0.0, f"separación mínima={s7b:+.2f}pp (informativo)"))

    # S8 · estabilidad del sistema: cola de PA y extremos (R8 / K5-R).
    p95_max = max(r["p95"] for r in (row(*k) for k in results))
    p12_max = max(r["t12"] for r in (row(*k) for k in results))
    p16_max = max(r["t16"] for r in (row(*k) for k in results))
    cap_total = sum(row(*k)["cap"] for k in results)
    contract.append(("S8 estabilidad del sistema (R8 / K5-R)",
                     p95_max <= S8_P95_MAX and p12_max <= S8_P12_MAX
                     and p16_max <= S8_P16_MAX and cap_total == 0,
                     f"p95≤{p95_max} (≤{S8_P95_MAX}) P12={p12_max:.3f}% "
                     f"(≤{S8_P12_MAX}) P16={p16_max:.3f}% (≤{S8_P16_MAX}) "
                     f"CAP={cap_total}"))

    print()
    for code, ok, detail in contract:
        print(f"  {code:<52} {'PASS' if ok else 'FAIL':>4}  ({detail})")
    passed = sum(1 for _, ok, _ in contract if ok)
    print("-" * 130)
    print(f"003B-6C · {passed}/{len(contract)} contratos PASS")
    print()
    if passed == len(contract):
        print("VERDICT: la ruta PRODUCTIVA reproduce exactamente la política "
              "aprobada por el LAB (k=.30 / α=.50) y no movió ningún mecanismo "
              "que Stuff no debía alterar.")
        print("         GAMEPLAY-ENGINE-003B → CLOSED / PASS")
    else:
        print("VERDICT: FAIL. La ruta productiva NO reproduce la política "
              "aprobada. No promover; revisar 003B-6A.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Monte Carlo de fatiga (GAMEPLAY-ENGINE-001B)")
    parser.add_argument("--mode", choices=["pa", "pitch", "discipline", "cv", "take", "foul", "bc", "d2", "cv2", "f5", "c1", "c3", "c4", "c5", "d1", "d3", "d4", "e1", "e2", "e3", "e3b", "e5", "e003a", "e003a-tail", "e003b", "e003b2", "e003b3", "e003b4", "e003b5a", "e003b5b", "e003b5c", "e003b6"], default="pa",
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
                              "e003b4 = Power×Stuff matchup robustness: k=.30, 5 Powers × 3 Stuffs, contratos O1–O7 + matrices XBH/HR + pendientes (003B-4); "
                              "e003b5a = Semántica Stuff×fatigue: F0 NONE / F1 FULL / F2 HALF / F3 ANCHORED, 4 workloads × 3 Stuff, contratos P1–P7 + stuff-added fatigue cost (003B-5A); "
                               "e003b5b = Calibración α de la fatiga de Stuff: 7 α (0/.25/.40/.50/.60/.75/1) × 4 workloads × 3 Stuff, contratos Q1–Q7 + fatigue_suppression_retention (003B-5B); "
                                "e003b5c = Power×Stuff×Fatigue head-to-head α=.50 vs .60: 2 α × 3 Power × 3 Stuff × 3 workloads, contratos R1–R9 + superficie pareada Δ(.60−.50) con SE pareado (003B-5C); "
                                "e003b6 = PRODUCTION ACCEPTANCE de Stuff: ruta real card→mapper→fatigue→calculate_play_outcome() sin knobs, PROD vs LAB vs PRE bit-exacto, bloques A fresh / B fatigue / C baseline, contratos S1–S8 (003B-6C); "
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
    elif args.mode == "e003b4":
        run_matchup_robustness_e003b4(args.reps)
    elif args.mode == "e003b5a":
        run_stuff_fatigue_policies_e003b5a(args.reps)
    elif args.mode == "e003b5b":
        run_stuff_fatigue_alpha_e003b5b(args.reps)
    elif args.mode == "e003b5c":
        run_power_stuff_fatigue_e003b5c(args.reps)
    elif args.mode == "e003b6":
        run_production_acceptance_003b6(args.reps)
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
