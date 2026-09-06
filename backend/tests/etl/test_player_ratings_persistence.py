"""Regresiones de persistencia idempotente para pitcher ratings-2.0."""

import datetime as dt
from dataclasses import dataclass

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Player, PlayerRatings
from etl.services.pitcher_ratings2 import PitcherRatings2Result
from etl.services.player_ratings import persist_pitcher_ratings2


START = dt.date(2026, 8, 25)
END = dt.date(2026, 9, 2)


@dataclass(frozen=True)
class FakeComponent:
    rating: int | None
    distribution_version: str = "dist-1.0"
    observed: float = 1.0
    sample_size: int = 91
    league_baseline: float = 0.5


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Player(mlb_id=650911, full_name="Cristopher Sanchez", primary_position="SP"))
    session.commit()
    yield session
    session.close()
    engine.dispose()


def _result(observed=1.0, control=71):
    return PitcherRatings2Result(
        mlb_id=650911,
        rating_model_version="ratings-2.0",
        velocity=FakeComponent(71, observed=observed),
        control=FakeComponent(control, observed=0.4),
        movement=FakeComponent(77, observed=1.5),
        stuff=FakeComponent(79, observed=0.3),
        overall=75 if control is not None else None,
    )


def test_created_unchanged_updated_por_inputs_efectivos(db):
    first = persist_pitcher_ratings2(
        db, _result(), season=2026, data_start_date=START, data_end_date=END
    )
    assert first.status == "CREATED"
    assert db.query(PlayerRatings).count() == 1
    row = db.query(PlayerRatings).one()
    assert (row.velocity_rating, row.control_rating, row.movement_rating, row.stuff_rating, row.overall_rating) == (71, 71, 77, 79, 75)

    second = persist_pitcher_ratings2(
        db, _result(), season=2026, data_start_date=START, data_end_date=END
    )
    assert second.status == "UNCHANGED"
    assert second.input_hash == first.input_hash

    # Cambia un input efectivo aunque los ratings redondeados sigan iguales.
    changed = persist_pitcher_ratings2(
        db, _result(observed=1.1), season=2026, data_start_date=START, data_end_date=END
    )
    assert changed.status == "UPDATED"
    assert changed.input_hash != first.input_hash
    assert db.query(PlayerRatings).count() == 1

    stable = persist_pitcher_ratings2(
        db, _result(observed=1.1), season=2026, data_start_date=START, data_end_date=END
    )
    assert stable.status == "UNCHANGED"
    assert stable.input_hash == changed.input_hash


def test_resultado_incompleto_no_se_persiste(db):
    persisted = persist_pitcher_ratings2(
        db, _result(control=None), season=2026, data_start_date=START, data_end_date=END
    )
    assert persisted.status == "SKIPPED_INCOMPLETE"
    assert db.query(PlayerRatings).count() == 0
