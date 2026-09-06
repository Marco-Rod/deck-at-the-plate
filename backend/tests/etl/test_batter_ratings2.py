"""Pruebas del ensamblador de batter ratings-2.0."""

import datetime as dt
from types import SimpleNamespace

from etl.services.batter_ratings2 import calculate_batter_ratings2


START = dt.date(2026, 8, 25)
END = dt.date(2026, 9, 2)


def _calculator(name, rating, calls, result):
    def calculate(_db=None, **kwargs):
        calls.append((name, kwargs))
        return result
    calculate.rating = rating
    return calculate


def _assemble(ratings):
    calls = []
    results = {
        name: SimpleNamespace(rating=rating, provenance=f"{name}-detail")
        for name, rating in ratings.items()
    }
    calculators = {
        name: _calculator(name, rating, calls, results[name])
        for name, rating in ratings.items()
        if name != "clutch"
    }

    def clutch_calculator():
        calls.append(("clutch", {}))
        return results["clutch"]

    assembled = calculate_batter_ratings2(
        object(),
        mlb_id=660271,
        season=2026,
        data_start_date=START,
        data_end_date=END,
        distribution_version="dist-1.0",
        contact_calculator=calculators["contact"],
        power_calculator=calculators["power"],
        vision_calculator=calculators["vision"],
        clutch_calculator=clutch_calculator,
    )
    return assembled, results, calls


def test_ensambla_ohtani_con_pesos_exactos_y_conserva_trazabilidad():
    result, components, calls = _assemble({
        "contact": 56,
        "power": 68,
        "vision": 66,
        "clutch": 70,
    })

    assert result.overall_rating == 64
    assert result.model_version == "ratings-2.0"
    assert result.skipped_components == ()
    assert result.contact is components["contact"]
    assert result.power is components["power"]
    assert result.vision is components["vision"]
    assert result.clutch is components["clutch"]
    assert [name for name, _kwargs in calls] == ["contact", "power", "vision", "clutch"]
    for name, kwargs in calls[:3]:
        assert kwargs == {
            "mlb_id": 660271,
            "season": 2026,
            "data_start_date": START,
            "data_end_date": END,
            "distribution_version": "dist-1.0",
        }


def test_overall_punto_cinco_usa_round_half_up():
    result, _components, _calls = _assemble({
        "contact": 70,
        "power": 70,
        "vision": 72,
        "clutch": 70,
    })
    assert result.overall_rating == 71


def test_componente_incompleto_deja_overall_none_sin_renormalizar():
    result, components, _calls = _assemble({
        "contact": 56,
        "power": None,
        "vision": 66,
        "clutch": 70,
    })
    assert result.overall_rating is None
    assert result.skipped_components == ("power",)
    assert result.power is components["power"]
