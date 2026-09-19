"""GAMEPLAY-ENGINE-001B — Monte Carlo de fatiga (nivel pitch y PA completo).

Fuera de producción: no toca fatigue_manager.py ni calculator.py. Reproduce el
pipeline real de un pitch (CPU MEDIUM) y llama a calculate_play_outcome() tal
cual lo hace resolve_swing().

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
from app.engine.calculator import calculate_play_outcome
from app.engine.cpu_ai import get_cpu_pitch_action, get_cpu_swing_action

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


def _simulate_pa_diag(take_probs: dict, seed: int,
                      control: int = None, vision: int = None,
                      take_bias: float = None,
                      foul_chance: float = None) -> dict:
    """PA 0-0 → K/BB/BIP con diagnóstico de count y de disciplinas, SIN fatiga.

    Args:
        take_probs: TAKE por strikes {0:.., 1:.., 2:..}.
        seed:       semilla del PA.
        control:    override del Control del pitcher (002B); default MID=80.
        vision:     override de la Vision del batter (002B); default MID=70.
        take_bias:  override del baseline de strike_chance del TAKE (002C-B);
                    None → 0.65 (producción).
        foul_chance: override del % de FOUL sobre contactos (002C-C);
                    None → 35.0 (producción).
    """
    random.seed(seed)
    balls = 0
    strikes = 0
    pitches = 0
    pitch_count = int(DISCIPLINE_WORKLOAD * THRESHOLD)  # congelado → factor 1.0

    # Overrides 002B (factorial Control × Vision); resto MID fijo.
    pitcher_raw = dict(PITCHER_RAW)
    pitch_raw = dict(PITCH_RAW)
    batter_attrs = dict(BATTER)
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

        event, _description = calculate_play_outcome(
            pitcher_attrs=fatigued_pitcher,
            batter_attrs=batter_attrs,
            pitch_selected=pitch,
            swing_selected=swing,
            tactics_modifiers=None,
            take_bias=take_bias,
            foul_chance=foul_chance,
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
    """Fórmula analítica del calculator (línea L90-L100): strike_chance de un TAKE."""
    return max(0.25, min(0.85, 0.65 + (control - 50) * 0.003 - (vision - 50) * 0.002))


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
CV2_FIX = {"take_bias": 0.30, "foul_chance": 45.0}
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
                              foul_chance=CV2_FIX["foul_chance"])
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
        d = _simulate_pa_diag(take_probs, seed, take_bias=base)
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
# Solo varía el % de FOUL sobre los contactos (production = 35). NO toca el
# whiff model ni la regla zona+tipo (contacto limpio sin foul). Pregunta: ¿más
# contacto no-terminal produce counts profundos sin destruir K/BIP ni generar
# PA interminables? TAKE vuelve a CURRENT 0.65 para aislar C.
FOUL_SWEEP = {
    "C0": 35.0,  # producción (foul_chance=None→35)
    "C1": 45.0,
    "C2": 55.0,
    "C3": 65.0,
}


def run_foul_sweep(reps: int) -> None:
    """002C-C · Sweep de foul/contact (35/45/55/65%), TAKE CURRENT, MID/MID."""
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
            f"{name:<4} {foul:>6.0f} | "
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
        d = _simulate_pa_diag(take_probs, seed, foul_chance=foul)
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
# B2/B3 (take 0.40/0.30) × C1/C2 (foul 45/55) + fila PROD (0.65/35) como control.
# Pregunta: ¿B (bolas) y C (strikes/supervivencia) se compensan y producen una
# región con K significativo + BB expresable + BIP dominante + PA profundo?
BC_CELLS = {
    "PROD":   {"take": None,  "foul": None},  # producción: 0.65 / 35
    "B2-C1":  {"take": 0.40,  "foul": 45.0},
    "B2-C2":  {"take": 0.40,  "foul": 55.0},
    "B3-C1":  {"take": 0.30,  "foul": 45.0},
    "B3-C2":  {"take": 0.30,  "foul": 55.0},
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
D2_FIX = {"take_bias": 0.30, "foul_chance": 45.0}
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
                              foul_chance=D2_FIX["foul_chance"])
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
F5_FIX = {"take_bias": 0.30, "foul_chance": 45.0}


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

        event, _description = calculate_play_outcome(
            pitcher_attrs=fatigued_pitcher,
            batter_attrs=BATTER,
            pitch_selected=pitch,
            swing_selected=swing,
            tactics_modifiers=None,
            take_bias=F5_FIX["take_bias"],
            foul_chance=F5_FIX["foul_chance"],
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

        event, _description = calculate_play_outcome(
            pitcher_attrs=fatigued,
            batter_attrs=BATTER,
            pitch_selected=pitch,
            swing_selected=swing,
            tactics_modifiers=None,
            take_bias=F5_FIX["take_bias"],
            foul_chance=F5_FIX["foul_chance"],
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

        event, _description = calculate_play_outcome(
            pitcher_attrs=fatigued,
            batter_attrs=BATTER,
            pitch_selected=pitch,
            swing_selected=swing,
            tactics_modifiers=None,
            take_bias=F5_FIX['take_bias'],
            foul_chance=F5_FIX['foul_chance'],
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
    parser.add_argument("--mode", choices=["pa", "pitch", "discipline", "cv", "take", "foul", "bc", "d2", "cv2", "f5", "c1", "c3", "c4", "c5"], default="pa",
                        help="pa = PA completo (001B-4); pitch = pitch suelto (001B-3); "
                             "discipline = diagnóstico de count/disciplina sin fatiga (002A); "
                             "cv = factorial Control×Vision (002B); "
                             "take = baseline sweep de TAKE (002C-B); "
                             "foul = sweep de terminación foul/contact (002C-C); "
                             "bc = factorial TAKE×foul (002C-BC); "
                             "d2 = two-strike discipline sensitivity (002D); "
                             "cv2 = Control×Vision sobre candidato 002D (002C-CV); "
                             "f5 = full-PA sobre el PA calibrado 002 (001B-5); "
                             "c1 = distribución natural de workload, fatiga neutralizada (001C-1); "
                             "c3 = threshold × outing completo, SMOOTH (001C-3); "
                             "c4 = robustez por matchup, SMOOTH-100 (001C-4); "
                             "c5 = escala del threshold 3/6/9 innings (001C-5)")
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
    else:
        run_pa_level(args.reps)


if __name__ == "__main__":
    main()