"""
Tests de caracterización de app.core (enums + DTOs)
======================================================
Garantiza que los nuevos enums sean intercambiables con los literales string
que ya usa el resto del código (compatibilidad 100% con DB y API).
"""

import app.core as core
from app.core import enums, engine_types


def test_event_values_match_magic_strings():
    assert enums.Event.HOME_RUN.value == "HOME_RUN"
    assert enums.Event.STRIKE_SWINGING == "STRIKE_SWINGING"
    assert enums.Event("HIT_1B") == enums.Event.HIT_1B


def test_event_is_hit_classification():
    assert enums.Event.HIT_1B.is_hit
    assert enums.Event.HOME_RUN.is_hit
    assert not enums.Event.OUT_FLY.is_hit


def test_position_compatibility():
    assert enums.Position("SP") == enums.Position.STARTER
    assert enums.Position.CENTER_FIELD.is_fielder
    assert enums.Position.TWO_WAY.is_pitcher


def test_position_pitcher_generic_is_a_pitcher():
    """DATA-AUDIT-001: "P" debe clasificar como lanzador, no como bateador.

    Si "P" queda fuera de Position.is_pitcher, las 403 cartas con role=PITCHER
    y position="P" del catalogo activo devuelven is_batter=True y pueden entrar
    al lineup con vision/contact/power en 0.
    """
    assert enums.Position("P") == enums.Position.PITCHER
    assert enums.Position.PITCHER.is_pitcher
    assert "P" in enums.PITCHER_POSITIONS
    assert not enums.Position.PITCHER.is_fielder


def test_pitcher_positions_cover_every_pitcher_position():
    """Ninguna posicion lanzadora puede quedar fuera de la constante derivada."""
    expected = {"P", "SP", "RP", "SU", "CP", "CL", "TWP"}
    assert set(enums.PITCHER_POSITIONS) == expected
    for value in expected:
        assert enums.Position(value).is_pitcher


def test_no_position_is_both_pitcher_and_fielder():
    """Un puesto no puede lanzar y ser de campo a la vez (DH incluido)."""
    pitchers = {p for p in enums.Position if p.is_pitcher}
    fielders = {p for p in enums.Position if p.is_fielder}
    assert not pitchers & fielders


def test_runner_base_keys_match_state_data():
    assert {b.value for b in enums.RunnerBase} == {"1b", "2b", "3b"}


def test_pitch_and_swing_and_difficulty():
    assert enums.PitchType.IBB.value == "IBB"
    assert enums.SwingType.BUNT.value == "BUNT"
    assert enums.Difficulty.HARD.value == "HARD"
    assert enums.GameMode.PVE.value == "PVE"
    assert enums.PlayerRole.PITCHER.value == "PITCHER"


def test_play_result_is_a_tuple():
    r = engine_types.PlayResult("HOME_RUN", "¡HOME RUN!")
    event, description = r  # desempaquetado estilo call-site actual
    assert event == "HOME_RUN"
    assert description == "¡HOME RUN!"


def test_at_bat_result_is_a_tuple():
    r = engine_types.AtBatResult(True, False, "STRIKEOUT", "Strikeout!")
    at_bat_ended, inning_ended, event, description = r
    assert at_bat_ended is True
    assert inning_ended is False
    assert event == "STRIKEOUT"
    assert description == "Strikeout!"


def test_core_reexports_all_public_symbols():
    for symbol in [
        "Difficulty", "Event", "GameMode", "PitchType", "PlayerRole",
        "Position", "RunnerBase", "SwingType",
        "AtBatResult", "BatterAttrs", "PitchSelection", "PitcherAttrs",
        "PlayResult", "Runners", "SwingSelection", "TacticsModifiers",
    ]:
        assert hasattr(core, symbol) or symbol in core.__all__