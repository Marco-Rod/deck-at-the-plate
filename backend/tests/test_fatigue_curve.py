"""GAMEPLAY-ENGINE-001C — Fatigue Policy v2 (SMOOTH-0.55-F35).

Congela la política calibrada:
    threshold = round(100 * innings / 9)   {3: 33, 6: 67, 9: 100}
    w         = pitch_count / threshold
    factor    = 1.0                                        si w <= 1
    factor    = 0.35 + 0.65 * exp(-((w - 1) / 0.55) ** 2)  si w > 1
    attr      = max(1, int(attr * factor))

Pitcher representativo: Velocity=90, Control=80, Movement=85.

``compute_fatigue_level`` conserva la fórmula legacy (lineal +10%/extra, cap
100) y sólo comparte el onset con el engine. Deuda: GAMEPLAY-FATIGUE-CPU-001.

003B-6A (Stuff) se sumó a este contrato sin mover la curva
----------------------------------------------------------
``apply_pitcher_fatigue`` ahora publica además ``stuff`` (float), con la misma
curva de factor y α=.50. La tabla exacta de arriba NO cambió: los atributos de
001C se comparan por nombre de clave para que este archivo siga congelando la
curva y no el incidental "shape del dict". La semántica de Stuff tiene sus
propios contratos en tests/test_stuff_policy.py (003B-6B).
"""

import pytest

from app.engine.fatigue_manager import (
    FATIGUE_FLOOR,
    FATIGUE_SIGMA,
    STANDARD_GAME_INNINGS,
    STANDARD_PITCH_THRESHOLD,
    apply_pitcher_fatigue,
    compute_fatigue_level,
    get_fatigue_factor,
    get_pitch_threshold,
)
from app.engine.stuff_policy import STUFF_BASELINE, effective_stuff

REPRESENTATIVE = {"velocidad": 90, "control": 80, "movimiento": 85}
INNINGS = 9
THRESHOLD = 100  # get_pitch_threshold(9)

# Atributos físicos de 001C. ``stuff`` se excluye a propósito del fixture: este
# módulo congela la curva de VEL/CTL/MOV de 001C, y REPRESENTATIVE representa un
# pitcher de la era 001C (sin Stuff publicado), que es exactamente el caso que
# debe seguir funcionando con el fallback neutro.
_PHYSICAL_KEYS = ("velocidad", "control", "movimiento")


def _physical(result):
    """Proyecta el resultado de apply_pitcher_fatigue a los atributos de 001C."""
    return {key: result[key] for key in _PHYSICAL_KEYS}


# ---------------------------------------------------------------------------
# 0. Constantes de la política
# ---------------------------------------------------------------------------

def test_constantes_policy_v2():
    assert STANDARD_GAME_INNINGS == 9
    assert STANDARD_PITCH_THRESHOLD == 100
    assert FATIGUE_SIGMA == pytest.approx(0.55)
    assert FATIGUE_FLOOR == pytest.approx(0.35)


# ---------------------------------------------------------------------------
# 1. ¿CUÁNDO empieza? — threshold / scaling
# ---------------------------------------------------------------------------

def test_threshold_innings_conocidos():
    assert get_pitch_threshold(3) == 33
    assert get_pitch_threshold(6) == 67
    assert get_pitch_threshold(9) == 100


@pytest.mark.parametrize(
    ("innings", "expected"),
    [(1, 11), (2, 22), (4, 44), (5, 56), (7, 78), (8, 89), (12, 133), (18, 200)],
)
def test_threshold_escala_proporcional(innings, expected):
    assert get_pitch_threshold(innings) == expected


def test_threshold_rechaza_innings_invalidos():
    with pytest.raises(ValueError):
        get_pitch_threshold(0)
    with pytest.raises(ValueError):
        get_pitch_threshold(-3)


# ---------------------------------------------------------------------------
# 2. Curva SMOOTH — puntos congelados (valores hardcodeados, no recalculados)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("pitch_count", "expected_factor"),
    [
        (0, 1.0),
        (50, 1.0),
        (100, 1.0),
        (110, 0.9788636821),
        (125, 0.8786680830),
        (150, 0.6344410658),
        (200, 0.3738357663),
        (2000, 0.35),
    ],
)
def test_puntos_smooth_congelados(pitch_count, expected_factor):
    assert get_fatigue_factor(pitch_count, THRESHOLD) == pytest.approx(expected_factor, abs=1e-6)


def test_factor_depende_solo_del_ratio():
    """La curva es función de w = count/threshold, no del count absoluto."""
    for w in (1.10, 1.25, 1.50, 2.00):
        factors = [get_fatigue_factor(w * th, th) for th in (33, 67, 100)]
        assert all(abs(f - factors[0]) < 1e-12 for f in factors)


def test_factor_rechaza_threshold_invalido():
    with pytest.raises(ValueError):
        get_fatigue_factor(120, 0)


# ---------------------------------------------------------------------------
# 3. Contratos: identidad, frontera, floor y monotonía
# ---------------------------------------------------------------------------

def test_identidad_hasta_threshold():
    for count in (0, 1, 50, 99, 100):
        assert get_fatigue_factor(count, THRESHOLD) == 1.0
        result = apply_pitcher_fatigue(REPRESENTATIVE, count, INNINGS)
        # 001C: los tres atributos físicos intactos hasta el threshold.
        assert _physical(result) == REPRESENTATIVE
        # 003B-6A: en fresco el Stuff efectivo es la identidad EXACTA del crudo.
        # Sin esto, "idéntico hasta el threshold" sería cierto sólo para 3 de 4
        # atributos y el cuarto podría estar degradándose en silencio.
        assert result["stuff"] == STUFF_BASELINE


def test_degradacion_tras_threshold():
    assert get_fatigue_factor(101, THRESHOLD) < 1.0
    assert apply_pitcher_fatigue(REPRESENTATIVE, 101, INNINGS) != REPRESENTATIVE


def test_floor_y_monotonia():
    prev = None
    for count in range(0, 400):
        factor = get_fatigue_factor(count, THRESHOLD)
        assert FATIGUE_FLOOR <= factor <= 1.0
        if prev is not None:
            assert factor <= prev
        prev = factor
    assert get_fatigue_factor(10_000, THRESHOLD) == pytest.approx(FATIGUE_FLOOR)


# ---------------------------------------------------------------------------
# 4. Atributos efectivos — tabla exacta del pitcher representativo
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("pitch_count", "vel", "ctl", "mov"),
    [
        (100, 90, 80, 85),  # en threshold: intacto
        (110, 88, 78, 83),
        (125, 79, 70, 74),
        (150, 57, 50, 53),
        (200, 33, 29, 31),
        (2000, 31, 28, 29),  # cerca del floor (0.35)
    ],
)
def test_curva_smooth_pitcher_representativo(pitch_count, vel, ctl, mov):
    result = apply_pitcher_fatigue(REPRESENTATIVE, pitch_count, INNINGS)
    # Se comparan las tres claves físicas por nombre en vez de por igualdad de
    # dict completo. La igualdad de dict era más estricta, pero la hizo frágil
    # sin ganar fuerza: cuando 003B-6A añadió ``stuff`` al resultado, dejó de
    # poder distinguir "la curva cambió" de "el contrato de la política creció".
    # Nombrando las claves, un fallo señala la clave culpable.
    assert _physical(result) == {"velocidad": vel, "control": ctl, "movimiento": mov}
    # El Stuff sigue la MISMA curva (α=.50, misma fórmula que 001C pero sin
    # truncar): monótono decreciente y estrictamente por debajo del crudo tras
    # el threshold. En fresco vale exactamente el baseline.
    expected_stuff = effective_stuff(STUFF_BASELINE, get_fatigue_factor(pitch_count, THRESHOLD))
    assert result["stuff"] == pytest.approx(expected_stuff)


def test_atributos_minimo_1():
    for count in (150, 300, 10_000):
        result = apply_pitcher_fatigue(REPRESENTATIVE, count, INNINGS)
        assert all(value >= 1 for value in result.values())


# ---------------------------------------------------------------------------
# 5. Nivel reportado (UI / CPU): legacy lineal, comparte onset con el engine
# ---------------------------------------------------------------------------

def test_fatigue_level_onset_v2():
    # 9 innings: el onset ahora es 100 (antes 25)
    assert compute_fatigue_level(99, INNINGS) == 0.0
    assert compute_fatigue_level(100, INNINGS) == 0.0
    assert compute_fatigue_level(101, INNINGS) == pytest.approx(10.0)
    assert compute_fatigue_level(104, INNINGS) == pytest.approx(40.0)
    assert compute_fatigue_level(107, INNINGS) == pytest.approx(70.0)


def test_fatigue_level_lineal_y_cap_a_100():
    # La magnitud NO es el factor SMOOTH: sigue siendo +10%/extra con cap 100.
    assert compute_fatigue_level(110, INNINGS) == 100.0
    assert compute_fatigue_level(10_000, INNINGS) == 100.0
