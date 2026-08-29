"""
Pruebas de caracterización del acumulador de efectos tácticos
(lógica extraída de gameplay._apply_tactic_modifiers).
"""
from app.engine.tactic_resolver import (
    accumulate_tactic_effects,
    new_default_tactic_modifiers,
)


def test_default_modifiers_are_neutral():
    mods = new_default_tactic_modifiers()
    assert mods == {
        "batter_con": 1.0,
        "batter_pwr": 1.0,
        "batter_vis": 1.0,
        "pitcher_mov": 1.0,
    }


def test_default_modifiers_return_fresh_dict():
    a = new_default_tactic_modifiers()
    b = new_default_tactic_modifiers()
    assert a is not b
    a["batter_con"] = 99
    assert b["batter_con"] == 1.0


def test_batter_effects_accumulate_on_vision_contacto_poder():
    effects = [
        {"attribute": "vision", "value": 10},
        {"attribute": "contacto", "value": -5},
        {"attribute": "poder", "value": 20},
    ]
    mods = accumulate_tactic_effects(effects)
    assert mods["batter_vis"] == 1.1
    assert mods["batter_con"] == 0.95
    assert mods["batter_pwr"] == 1.2
    assert mods["pitcher_mov"] == 1.0


def test_pitcher_effects_accumulate_on_movimiento():
    effects = [{"attribute": "movimiento", "value": 15}]
    mods = accumulate_tactic_effects(effects, is_pitcher_tactic=True)
    assert mods["pitcher_mov"] == 1.15
    assert mods["batter_con"] == 1.0


def test_pitcher_tactic_ignores_batter_attributes():
    effects = [
        {"attribute": "vision", "value": 50},
        {"attribute": "movimiento", "value": 20},
    ]
    mods = accumulate_tactic_effects(effects, is_pitcher_tactic=True)
    assert mods["batter_vis"] == 1.0  # ignorado
    assert mods["pitcher_mov"] == 1.2


def test_batter_tactic_ignores_movimiento():
    effects = [{"attribute": "movimiento", "value": 50}]
    mods = accumulate_tactic_effects(effects)
    assert mods["pitcher_mov"] == 1.0


def test_effects_without_attribute_are_ignored():
    mods = accumulate_tactic_effects([{"value": 20}, {"attribute": "poder", "value": 10}])
    assert mods["batter_pwr"] == 1.1


def test_accumulate_over_existing_mods_mutates_and_returns_same_dict():
    mods = new_default_tactic_modifiers()
    result = accumulate_tactic_effects(
        [{"attribute": "poder", "value": 10}],
        mods=mods,
    )
    assert result is mods
    assert mods["batter_pwr"] == 1.1