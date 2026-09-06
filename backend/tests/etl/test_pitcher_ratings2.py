"""Pruebas del ensamblador no persistente de pitcher ratings-2.0."""

import datetime as dt
from types import SimpleNamespace

from etl.services.pitcher_ratings2 import calculate_pitcher_ratings2
from etl.services.rating_math import round_rating


START = dt.date(2026, 8, 25)
END = dt.date(2026, 9, 2)


def _calculator(rating, calls, name):
    def calculate(db, **kwargs):
        calls.append((name, db, kwargs))
        return SimpleNamespace(rating=rating, detail=name)
    return calculate


def test_ensambla_sanchez_71_71_77_79_como_75_sin_modificar_componentes():
    calls = []
    calculators = {
        "velocity_calculator": _calculator(71, calls, "velocity"),
        "control_calculator": _calculator(71, calls, "control"),
        "movement_calculator": _calculator(77, calls, "movement"),
        "stuff_calculator": _calculator(79, calls, "stuff"),
    }
    db = object()
    result = calculate_pitcher_ratings2(
        db, mlb_id=650911, season=2026, data_start_date=START, data_end_date=END,
        **calculators,
    )
    assert result.velocity.rating == 71
    assert result.control.rating == 71
    assert result.movement.rating == 77
    assert result.stuff.rating == 79
    assert result.overall == 75
    assert result.rating_model_version == "ratings-2.0"
    assert [name for name, _db, _kwargs in calls] == ["velocity", "control", "movement", "stuff"]
    assert all(call_db is db for _name, call_db, _kwargs in calls)


def test_round_rating_sube_exactamente_los_medios():
    assert round_rating(74.5) == 75
    assert round_rating(72.49) == 72
    assert round_rating(72.50) == 73


def test_overall_no_disponible_si_falta_cualquier_atributo():
    result = calculate_pitcher_ratings2(
        object(), mlb_id=650911, season=2026, data_start_date=START, data_end_date=END,
        velocity_calculator=_calculator(71, [], "velocity"),
        control_calculator=_calculator(None, [], "control"),
        movement_calculator=_calculator(77, [], "movement"),
        stuff_calculator=_calculator(79, [], "stuff"),
    )
    assert result.overall is None
    assert result.unavailable_attributes == ["control"]
