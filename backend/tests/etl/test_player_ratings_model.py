"""Integridad estructural del contrato versionado PlayerRatings."""

import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Player, PlayerRatings


START = dt.date(2026, 8, 25)
END = dt.date(2026, 9, 2)
HASH = "a" * 64


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    player = Player(mlb_id=650911, full_name="Cristopher Sanchez", primary_position="SP")
    session.add(player)
    session.commit()
    yield session, player
    session.close()
    engine.dispose()


def _pitcher(player, **overrides):
    values = dict(
        player_id=player.id, season=2026, role="PITCHER",
        rating_model_version="ratings-2.0", distribution_version="dist-1.0",
        data_start_date=START, data_end_date=END,
        velocity_rating=71, control_rating=71, movement_rating=77, stuff_rating=79,
        overall_rating=75, input_hash=HASH,
    )
    values.update(overrides)
    return PlayerRatings(**values)


@pytest.mark.parametrize("column", ["contact", "power", "vision", "clutch", "velocity", "control", "movement", "stuff"])
@pytest.mark.parametrize("value", [-0.00001, 1.00001])
def test_evidence_range_enforced(db, column, value):
    session, player = db
    session.add(_pitcher(player, **{column + "_evidence": value}))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_acepta_pitcher_y_batter_completos(db):
    session, player = db
    session.add(_pitcher(player))
    batter = Player(mlb_id=660271, full_name="Shohei Ohtani", primary_position="TWP")
    session.add(batter)
    session.flush()
    session.add(PlayerRatings(
        player_id=batter.id, season=2026, role="BATTER",
        rating_model_version="ratings-2.0", distribution_version="dist-1.0",
        data_start_date=START, data_end_date=END,
        contact_rating=80, power_rating=90, vision_rating=75, clutch_rating=82,
        overall_rating=84, input_hash="b" * 64,
    ))
    session.commit()
    assert session.query(PlayerRatings).count() == 2


@pytest.mark.parametrize("overrides", [
    {"control_rating": None},
    {"contact_rating": 50},
    {"velocity_rating": 100},
    {"overall_rating": 39},
    {"input_hash": "short"},
])
def test_rechaza_filas_incompletas_mixtas_o_fuera_de_rango(db, overrides):
    session, player = db
    session.add(_pitcher(player, **overrides))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_identidad_versionada_no_sobrescribe_y_rechaza_duplicado(db):
    session, player = db
    session.add(_pitcher(player))
    session.add(_pitcher(player, rating_model_version="ratings-2.1", input_hash="c" * 64))
    session.commit()
    assert session.query(PlayerRatings).count() == 2

    session.add(_pitcher(player))
    with pytest.raises(IntegrityError):
        session.flush()
