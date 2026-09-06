"""Regresiones de las fórmulas de CardGenerationProfile."""

from decimal import Decimal
from datetime import date
from types import SimpleNamespace

import pytest

from etl.services.card_profiles import (
    _build_batter_profile,
    _build_pitcher_profile,
    _input_hash,
    _pitcher_profile_inputs,
    generate_profiles,
)


def test_pitcher_profile_acepta_numeric_como_decimal():
    pitcher = SimpleNamespace(
        avg_velocity=Decimal("96.25"),
        walks=8,
        batters_faced=120,
        whiff_rate=Decimal("0.287500"),
        strikeouts=35,
    )

    profile = _build_pitcher_profile(pitcher, [], "test")

    assert 0 <= profile["velocity_rating"] <= 99
    assert 0 <= profile["movement_rating"] <= 99
    assert 0 <= profile["overall_rating"] <= 99


def test_pitcher_profile_sin_bateadores_enfrentados_usa_fallback():
    pitcher = SimpleNamespace(
        avg_velocity=None,
        walks=0,
        batters_faced=0,
        whiff_rate=None,
        strikeouts=0,
    )

    profile = _build_pitcher_profile(pitcher, [], "test")

    assert profile["control_rating"] == 40


def test_batter_profile_acepta_numeric_como_decimal():
    batter = SimpleNamespace(
        contact_rate=Decimal("0.725000"),
        slg=Decimal("0.51000"),
        whiff_rate=Decimal("0.275000"),
        home_runs=24,
    )

    profile = _build_batter_profile(batter, "test")

    assert 0 <= profile["vision_rating"] <= 99
    assert 0 <= profile["overall_rating"] <= 99


def test_hash_de_arsenal_es_independiente_del_orden():
    pitcher = SimpleNamespace(
        avg_velocity=Decimal("94.25"),
        walks=2,
        batters_faced=91,
        whiff_rate=Decimal("0.280000"),
        strikeouts=8,
    )
    rows = [
        SimpleNamespace(pitch_type="SI", pitch_family="FASTBALL", batter_side="ALL", pitch_count=40),
        SimpleNamespace(pitch_type="CH", pitch_family="OFFSPEED", batter_side="ALL", pitch_count=37),
        SimpleNamespace(pitch_type="SL", pitch_family="BREAKING", batter_side="ALL", pitch_count=14),
    ]

    first = _pitcher_profile_inputs(
        pitcher,
        rows,
        rating_model_version="ratings-1.0",
        data_end_date=date(2026, 9, 2),
    )
    second = _pitcher_profile_inputs(
        pitcher,
        list(reversed(rows)),
        rating_model_version="ratings-1.0",
        data_end_date=date(2026, 9, 2),
    )

    assert _input_hash(first) == _input_hash(second)


def test_no_etiqueta_formulas_v1_como_ratings_2():
    with pytest.raises(ValueError, match="rating model no implementado"):
        generate_profiles(object(), season=2026, rating_model_version="ratings-2.0")
