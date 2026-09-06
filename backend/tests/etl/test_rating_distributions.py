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


def _build(db, **overrides):
    arguments = {
        "season": 2026,
        "role": "pitcher",
        "data_start_date": START,
        "data_end_date": END,
        "rating_model_version": "ratings-2.0",
        "source_distribution_version": "dist-1.0",
        "rarity_model_version": "rarity-2.0",
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

    versioned = _build(db, rarity_model_version="rarity-2.1")
    assert versioned.status == "CREATED"
    assert db.query(RatingDistribution).count() == 2


def test_poblacion_vacia_no_crea_distribucion(db):
    result = _build(db)
    assert result.status == "SKIPPED_EMPTY"
    assert result.population_size == 0
    assert db.query(RatingDistribution).count() == 0


def test_rechaza_rol_y_ventana_no_soportados(db):
    with pytest.raises(ValueError, match="role=pitcher"):
        _build(db, role="batter")
    with pytest.raises(ValueError, match="posterior"):
        _build(db, data_start_date=END, data_end_date=START)
