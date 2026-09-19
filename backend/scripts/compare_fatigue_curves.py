"""GAMEPLAY-ENGINE-001B-2 — comparación matemática de curvas de fatiga.

CURRENT es la política legacy CONGELADA (réplica del apply_pitcher_fatigue
anterior a Fatigue Policy v2, 001C); LINEAR y SMOOTH son candidatos
experimentales definidos en este script. No importa helpers de producción: tras
001C-6 producción es SMOOTH v2 y ya no representa la curva CURRENT histórica.

La definición legacy está duplicada a propósito (espejo de
``simulate_fatigue_impact.py``) para no acoplar la reproducibilidad de los
experimentos a producción. Si se cambia una, cambiar la otra.

Workload normalizado = pitch_count / threshold, para poder comparar una misma
función en juegos de 3/6/9 innings.

Constantes de los candidatos (provisionales, LAB — decisión del simulador):
    LINEAR: factor = max(floor, 1 - slope*(w-1))        slope=0.8, floor=0.50
    SMOOTH: factor = floor + (1-floor)*exp(-(g/s)^p)    s=0.55, p=2, floor=0.35
        g = w - 1  (Weibull S: arranque suave, luego acelera, plató en floor)
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PITCHER = {"velocidad": 90, "control": 80, "movimiento": 85}
WORKLOAD_POINTS = [0.25, 0.50, 0.75, 1.00, 1.10, 1.25, 1.50]


# ---------------------------------------------------------------------------
# Política legacy CONGELADA (ver simulate_fatigue_impact.py). NO usar producción.
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



# ---------------------------------------------------------------------------
# Curvas candidatas (workload normalizado → factor multiplicativo)
# ---------------------------------------------------------------------------

def linear_factor(workload: float, slope: float = 0.8, floor: float = 0.50) -> float:
    """Degradación lineal progresiva + floor explícito."""
    if workload <= 1.0:
        return 1.0
    return max(floor, 1.0 - slope * (workload - 1.0))


def smooth_factor(workload: float, scale: float = 0.55, power: int = 2, floor: float = 0.35) -> float:
    """Curva S (Weibull) + floor explícito: suave al inicio, luego acelera."""
    if workload <= 1.0:
        return 1.0
    excess = workload - 1.0
    return floor + (1.0 - floor) * math.exp(-(excess / scale) ** power)


# ---------------------------------------------------------------------------
# Atributos efectivos
# ---------------------------------------------------------------------------

def current_attrs(workload: float, innings: int = 9) -> dict:
    """CURRENT legacy: política congelada, independiente de producción."""
    threshold = legacy_get_pitch_threshold(innings)
    pitch_count = int(workload * threshold)
    return legacy_apply_pitcher_fatigue(PITCHER, pitch_count, innings)


def candidate_attrs(factor_fn, workload: float) -> dict:
    factor = factor_fn(workload)
    return {key: max(1, int(value * factor)) for key, value in PITCHER.items()}


# ---------------------------------------------------------------------------
# Restricciones de diseño (property checks, sweep fino)
# ---------------------------------------------------------------------------

def check_properties(factor_fn, name: str) -> list[str]:
    """Verifica las restricciones sobre un barrido fino de workload."""
    problems: list[str] = []
    prev = None
    for i in range(50, 201):  # 0.5 .. 2.0 step 0.01
        w = i / 100.0
        f = factor_fn(w)
        if w <= 1.0 and f != 1.0:
            problems.append(f"workload {w:.2f} <= 1: factor {f:.4f} != 1.0")
        if w > 1.0 and f >= 1.0:
            problems.append(f"workload {w:.2f} > 1: factor {f:.4f} no baja")
        if f < 0.0:
            problems.append(f"workload {w:.2f}: factor {f:.4f} negativo")
        if prev is not None and f > prev + 1e-9:
            problems.append(f"workload {w:.2f}: factor sube ({prev:.4f} -> {f:.4f})")
        prev = f
    if problems:
        return [f"{name}: {p}" for p in problems[:5]]
    return [f"{name}: restricciones OK (identidad <=100%, monótona, no negativa)"]


def check_current_properties() -> list[str]:
    """Análogo para CURRENT usando attributos efectivos (solo lectura)."""
    problems: list[str] = []
    prev = None
    for i in range(50, 201):
        attrs = current_attrs(i / 100.0)
        total = sum(attrs.values())
        if prev is not None and total > prev + 1e-9:
            problems.append(f"workload {i/100:.2f}: atributos suben")
        prev = total
        for key, value in attrs.items():
            if value < 1:
                problems.append(f"workload {i/100:.2f}: {key} = {value} < 1")
    return problems or ["CURRENT: restricciones OK (monótona, floor>=1)"]


# ---------------------------------------------------------------------------
# Salida
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 100)
    print("GAMEPLAY-ENGINE-001B-2 · Comparación matemática de curvas de fatiga")
    print(f"Pitcher representativo: {PITCHER} | threshold legacy(9 innings) = {legacy_get_pitch_threshold(9)}")
    print("=" * 100)

    # Restricciones
    for label, problems in [
        ("CURRENT", check_current_properties()),
        ("LINEAR", check_properties(linear_factor, "LINEAR")),
        ("SMOOTH", check_properties(smooth_factor, "SMOOTH")),
    ]:
        for line in problems:
            print(f"  [{'OK' if 'OK' in line else 'FALLA'}] {line}")

    print()
    print(f"{'workload':>8} | {'CURRENT (pitch_count)':>30} | "
          f"{'LINEAR':>26} | {'SMOOTH':>26}")
    print(f"{'':>8} | {'factor   V   C   M ':>30} | "
          f"{'factor   V   C   M ':>26} | {'factor   V   C   M ':>26}")
    print("-" * 100)

    for w in WORKLOAD_POINTS:
        count = int(w * legacy_get_pitch_threshold(9))
        c = current_attrs(w)
        lf = linear_factor(w)
        l = candidate_attrs(linear_factor, w)
        sf = smooth_factor(w)
        s = candidate_attrs(smooth_factor, w)
        print(
            f"{w:>7.0%} | "
            f"{count:>4}  {c['velocidad']:>3} {c['control']:>3} {c['movimiento']:>3}    | "
            f"{lf:>6.2f} {l['velocidad']:>3} {l['control']:>3} {l['movimiento']:>3}  | "
            f"{sf:>6.2f} {s['velocidad']:>3} {s['control']:>3} {s['movimiento']:>3}"
        )

    print()
    print("Nota: CURRENT depende del pitch_count ABSOLUTO -> su cuesta varía con los")
    print("innings; LINEAR/SMOOTH dependen del workload normalizado -> misma función")
    print("en juegos de 3/6/9 innings.")


if __name__ == "__main__":
    main()