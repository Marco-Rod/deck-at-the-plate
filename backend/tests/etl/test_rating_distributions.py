"""Pruebas del builder de distribuciones sobre PlayerRatings."""

import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Player, PlayerRatings, RatingDistribution
from etl.services.rating_distributions import build_overall_rating_distribution


START = dt.date(2026, 8, 25)
END = dt.date(2026, 9, 2)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _add_pitcher_rating(
    db,
    mlb_id: int,
    overall: int,
    *,
    rating_model_version: str = "ratings-2.0",
    distribution_version: str = "dist-1.0",
    start: dt.date = START,
    end: dt.date = END,
):
    player = Player(mlb_id=mlb_id, full_name=f"Pitcher {mlb_id}", primary_position="P")
    db.add(player)
    db.flush()
    db.add(PlayerRatings(
        player_id=player.id,
        season=2026,
        role="PITCHER",
        rating_model_version=rating_model_version,
        distribution_version=distribution_version,
        data_start_date=start,
        data_end_date=end,
        velocity_rating=overall,
        control_rating=overall,
        movement_rating=overall,
        stuff_rating=overall,
        overall_rating=overall,
        input_hash=f"{mlb_id:064d}"[-64:],
    ))
    db.commit()


def _add_batter_rating(
    db,
    mlb_id: int,
    overall: int,
    *,
    rating_model_version: str = "ratings-2.0",
    distribution_version: str = "dist-1.0",
    start: dt.date = START,
    end: dt.date = END,
):
    player = Player(mlb_id=mlb_id, full_name=f"Batter {mlb_id}", primary_position="DH")
    db.add(player)
    db.flush()
    db.add(PlayerRatings(
        player_id=player.id,
        season=2026,
        role="BATTER",
        rating_model_version=rating_model_version,
        distribution_version=distribution_version,
        data_start_date=start,
        data_end_date=end,
        contact_rating=overall,
        power_rating=overall,
        vision_rating=overall,
        clutch_rating=overall,
        overall_rating=overall,
        input_hash=f"{mlb_id:064d}"[-64:],
    ))
    db.commit()


def _build(db, **overrides):
    arguments = {
        "season": 2026,
        "role": "pitcher",
        "data_start_date": START,
        "data_end_date": END,
        "rating_model_version": "ratings-2.0",
        "source_distribution_version": "dist-1.0",
        "performance_tier_model_version": "rarity-2.0",
    }
    arguments.update(overrides)
    return build_overall_rating_distribution(db, **arguments)


def test_construye_percentiles_de_poblacion_comparable_e_idempotente(db):
    for mlb_id, overall in enumerate((60, 70, 80, 90), start=1):
        _add_pitcher_rating(db, mlb_id, overall)
    _add_pitcher_rating(db, 10, 99, distribution_version="dist-2.0")
    _add_pitcher_rating(db, 11, 99, start=dt.date(2026, 8, 1))

    first = _build(db)
    assert first.status == "CREATED"
    row = db.query(RatingDistribution).one()
    assert row.population_size == 4
    assert row.population_histogram == {"60": 1, "70": 1, "80": 1, "90": 1}
    assert float(row.population_mean) == 75
    assert float(row.minimum) == 60
    assert float(row.p05) == 61.5
    assert float(row.p50) == 75
    assert float(row.p95) == 88.5
    assert float(row.maximum) == 90

    second = _build(db)
    assert second.status == "UNCHANGED"
    assert second.rating_distribution_id == first.rating_distribution_id
    assert db.query(RatingDistribution).count() == 1


def test_actualiza_poblacion_y_conserva_versiones_historicas(db):
    _add_pitcher_rating(db, 1, 60)
    first = _build(db)
    _add_pitcher_rating(db, 2, 90)
    updated = _build(db)
    assert updated.status == "UPDATED"
    assert updated.rating_distribution_id == first.rating_distribution_id
    assert updated.population_size == 2

    versioned = _build(db, performance_tier_model_version="performance-tier-2.1")
    assert versioned.status == "CREATED"
    assert db.query(RatingDistribution).count() == 2


def test_poblacion_vacia_no_crea_distribucion(db):
    result = _build(db)
    assert result.status == "SKIPPED_EMPTY"
    assert result.population_size == 0
    assert db.query(RatingDistribution).count() == 0


def test_batter_construye_histograma_real_separado_e_idempotente(db):
    expected_histogram = {
        "63": 1,
        "64": 4,
        "65": 1,
        "66": 3,
        "67": 17,
        "68": 17,
        "69": 33,
        "70": 50,
        "71": 42,
        "72": 23,
        "73": 17,
        "74": 9,
        "75": 5,
        "77": 1,
        "78": 2,
    }
    mlb_id = 1000
    for overall, frequency in expected_histogram.items():
        for _ in range(frequency):
            _add_batter_rating(db, mlb_id, int(overall))
            mlb_id += 1

    # No deben mezclarse otro rol, versión de distribución ni ventana.
    _add_pitcher_rating(db, 9001, 99)
    _add_batter_rating(db, 9002, 99, distribution_version="dist-2.0")
    _add_batter_rating(db, 9003, 99, start=dt.date(2026, 8, 1))

    first = _build(db, role="batter")
    assert first.status == "CREATED"
    row = db.query(RatingDistribution).filter_by(role="BATTER").one()
    assert row.population_size == 225
    assert row.population_histogram == expected_histogram
    assert "76" not in row.population_histogram
    assert sum(row.population_histogram.values()) == row.population_size
    assert float(row.minimum) == 63
    assert float(row.p50) == 70
    assert float(row.p95) == 74
    assert float(row.maximum) == 78

    second = _build(db, role="batter")
    assert second.status == "UNCHANGED"
    assert second.rating_distribution_id == first.rating_distribution_id


def test_rechaza_rol_y_ventana_no_soportados(db):
    with pytest.raises(ValueError, match="batter o pitcher"):
        _build(db, role="fielder")
    with pytest.raises(ValueError, match="posterior"):
        _build(db, data_start_date=END, data_end_date=START)
