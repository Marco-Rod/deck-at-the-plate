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