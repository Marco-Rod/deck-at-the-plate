"""Contratos del trace aditivo del calculator (RUNTIME TELEMETRY P5-A).

El trace debe exponer la decisión del motor SIN alterar la resolución:
``calculate_play_outcome_with_trace`` tiene que devolver exactamente el mismo
``PlayResult`` que ``calculate_play_outcome`` (mismos draws, mismo orden) y
aportar, además, una distribución final ex-ante que sume 1 y el draw que
realizó el resultado.
"""

import random

from app.core.enums import Event
from app.engine import calculator
from app.engine.calculator import (
    calculate_play_outcome,
    calculate_play_outcome_with_trace,
)


PITCHER = {"velocidad": 70, "control": 65, "movimiento": 68, "stuff": 70.0}
BATTER = {"contacto": 60, "poder": 62, "vision": 58}
PITCH = {"pitch_type": "4-SEAM", "zone": 5, "velocity": 72, "control": 66, "movement": 64}


def _swing(swing_type, guessed_zone=None, guessed_pitch=None):
    return {
        "swing_type": swing_type,
        "guessed_zone": guessed_zone,
        "guessed_pitch": guessed_pitch,
    }


def _inputs(swing_type, *, guessed_zone=None, guessed_pitch=None, pitch=None, batter=None):
    return dict(
        pitcher_attrs=PITCHER,
        batter_attrs=batter or BATTER,
        pitch_selected=pitch or PITCH,
        swing_selected=_swing(swing_type, guessed_zone, guessed_pitch),
        tactics_modifiers=None,
    )


# ---------------------------------------------------------------------------
# 1. El trace no altera la resolución (bit-exactitud)
# ---------------------------------------------------------------------------

def test_trace_es_bit_exacto_con_la_api_de_produccion():
    scenarios = [
        _inputs("TAKE"),
        _inputs("TAKE", guessed_zone=5),
        _inputs("NORMAL"),
        _inputs("NORMAL", guessed_zone=5, guessed_pitch="4-SEAM"),
        _inputs("POWER"),
        # Bateador débil → power_score bajo; bateador fuerte → home runs.
        _inputs("NORMAL", batter={"contacto": 30, "poder": 40, "vision": 40}),
        _inputs("NORMAL", batter={"contacto": 90, "poder": 95, "vision": 90}),
    ]
    for index, inputs in enumerate(scenarios):
        for seed in range(25):
            random.seed(seed)
            plain = calculate_play_outcome(**inputs)
            random.seed(seed)
            traced = calculate_play_outcome_with_trace(**inputs)
            assert traced.result == plain, f"escenario {index} seed {seed}"


# ---------------------------------------------------------------------------
# 2. Distribución: forma, suma y cobertura
# ---------------------------------------------------------------------------

def test_distribucion_suma_uno_y_solo_eventos_canonicos():
    valid = {event.value for event in Event}
    for inputs in (_inputs("TAKE"), _inputs("NORMAL"), _inputs("POWER")):
        trace = calculate_play_outcome_with_trace(**inputs).trace
        distribution = trace["distribution"]
        assert distribution, "la distribución no puede ser vacía"
        assert set(distribution) <= valid
        assert abs(sum(distribution.values()) - 1.0) < 1e-9


def test_distribucion_take_es_binaria():
    trace = calculate_play_outcome_with_trace(**_inputs("TAKE")).trace
    assert set(trace["distribution"]) == {Event.STRIKE_LOOKING.value, Event.BALL.value}


def test_matchup_inputs_expone_la_decision_y_el_contexto_del_pitch():
    # El trace registra la decisión del bateador (guesses) y el contexto real
    # del pitch que el engine consumió para zone/pitch match (P5-B).
    inputs = _inputs("NORMAL", guessed_zone=7, guessed_pitch="SLIDER")
    trace = calculate_play_outcome_with_trace(**inputs).trace
    matchup = trace["matchup_inputs"]

    assert matchup["guessed_zone"] == 7
    assert matchup["guessed_pitch"] == "SLIDER"
    assert matchup["actual_zone"] == PITCH["zone"]
    assert matchup["actual_pitch"] == PITCH["pitch_type"]
    assert matchup["swing_type"] == "NORMAL"
    # Atributos efectivos que el engine usó.
    assert matchup["contact"] == BATTER["contacto"]
    assert matchup["power"] == BATTER["poder"]
    assert matchup["vision"] == BATTER["vision"]
    assert matchup["stuff"] == PITCHER["stuff"]


def test_distribucion_ibb_es_bola_segura():
    pitch = {"pitch_type": "IBB", "zone": 5}
    trace = calculate_play_outcome_with_trace(**_inputs("NORMAL", pitch=pitch)).trace
    assert trace["distribution"] == {Event.BALL.value: 1.0}
    assert trace["rng_value"] is None


def test_bip_class_distribution_particiona_la_uniforme():
    dist = calculator._bip_class_distribution(0.0, 100.0)
    assert abs(sum(dist.values()) - 1.0) < 1e-12
    # Anchos exactos de la partición de [0, 100] con los umbrales del motor.
    assert dist[Event.HOME_RUN.value] == 4 / 100
    assert dist[Event.HIT_3B.value] == 3 / 100
    assert dist[Event.HIT_2B.value] == 8 / 100
    assert dist[Event.HIT_1B.value] == 22 / 100
    assert dist[Event.OUT_GROUND.value] == 38 / 100
    assert dist[Event.OUT_FLY.value] == 25 / 100

    # Desplazamiento del rango completo por encima de 96 → sólo HOME_RUN.
    high = calculator._bip_class_distribution(120.0, 220.0)
    assert high[Event.HOME_RUN.value] == 1.0
    assert abs(sum(high.values()) - 1.0) < 1e-12


# ---------------------------------------------------------------------------
# 3. rng_value: rango, coherencia con el resultado y draw decisivo
# ---------------------------------------------------------------------------

def test_rng_value_en_intervalo_unitario_y_draw_decisivo():
    for seed in range(200):
        random.seed(seed)
        traced = calculate_play_outcome_with_trace(**_inputs("NORMAL"))
        trace = traced.trace
        rng = trace["rng_value"]
        draws = trace["draws"]
        assert draws, "un swing siempre consume al menos el draw de whiff"
        assert rng is not None and 0.0 <= rng < 1.0

        event = traced.result.event
        if event == Event.STRIKE_SWINGING.value:
            # El draw de whiff (uniform 0-100) fue el decisivo.
            assert draws[-1]["step"] == "whiff"
            assert rng == draws[-1]["value"] / 100.0
            assert rng * 100.0 < draws[-1]["threshold"]
        elif event == Event.FOUL.value:
            assert draws[-1]["step"] == "foul"
            assert rng == draws[-1]["value"]
        else:
            # Bola en juego: el último draw es el de BABIP.
            assert draws[-1]["step"] == "babip"
            assert rng == draws[-1]["value"] / 100.0


def test_rng_value_take_decide_el_strike_cantado():
    for seed in range(200):
        random.seed(seed)
        traced = calculate_play_outcome_with_trace(**_inputs("TAKE"))
        trace = traced.trace
        strike_prob = trace["distribution"][Event.STRIKE_LOOKING.value]
        rng = trace["rng_value"]
        assert 0.0 <= rng < 1.0
        es_strike = traced.result.event == Event.STRIKE_LOOKING.value
        assert es_strike == (rng < strike_prob)


# ---------------------------------------------------------------------------
# 4. La distribución analítica describe al engine real (frecuencia empírica)
# ---------------------------------------------------------------------------

def test_distribucion_predice_la_frecuencia_del_engine():
    inputs = _inputs("NORMAL", guessed_zone=2, guessed_pitch="SLIDER")
    trace = calculate_play_outcome_with_trace(**inputs).trace
    distribution = trace["distribution"]

    n = 20_000
    counts: dict[str, int] = {}
    for seed in range(n):
        random.seed(seed)
        event = calculate_play_outcome(**inputs).event
        counts[event] = counts.get(event, 0) + 1

    for event_key, prob in distribution.items():
        empirical = counts.get(event_key, 0) / n
        assert abs(empirical - prob) < 0.02, (
            f"{event_key}: empírico={empirical:.4f} analítico={prob:.4f}"
        )
