"""Regresiones de persistencia idempotente para batter ratings-2.0."""

import datetime as dt
from dataclasses import dataclass

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Player, PlayerRatings, PlayerSeason
from etl.services.batter_ratings2 import BatterRatings2
from etl.services.player_ratings import persist_batter_ratings2


START = dt.date(2026, 8, 25)
END = dt.date(2026, 9, 2)


@dataclass(frozen=True)
class FakeComponent:
    rating: int | None
    distribution_version: str = "dist-1.0"
    distribution_id: str = "distribution-1"
    observed: float = 0.5
    sample_size: int = 38
    league_baseline: float = 0.4
    stabilization: int = 40


@dataclass(frozen=True)
class FakeClutch:
    rating: int | None = 70
    source: str = "NEUTRAL_BASELINE_PENDING_SITUATIONAL_DATA"
    sample_size: int = 0
    model_version: str = "ratings-2.0"


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    player = Player(mlb_id=660271, full_name="Shohei Ohtani", primary_position="TWP")
    session.add(player)
    session.flush()
    session.add(PlayerSeason(
        player_id=player.id,
        season=2026,
        data_start_date=START,
        data_end_date=END,
    ))
    session.commit()
    yield session
    session.close()
    engine.dispose()


def _result(
    *,
    contact_observed: float = 0.64,
    distribution_id: str = "distribution-1",
    clutch_source: str = "NEUTRAL_BASELINE_PENDING_SITUATIONAL_DATA",
    power: int | None = 68,
) -> BatterRatings2:
    return BatterRatings2(
        mlb_id=660271,
        contact=FakeComponent(
            56, distribution_id=distribution_id, observed=contact_observed
        ),
        power=FakeComponent(power, distribution_id=distribution_id, observed=0.09),
        vision=FakeComponent(66, distribution_id=distribution_id, observed=0.30),
        clutch=FakeClutch(source=clutch_source),
        overall_rating=64 if power is not None else None,
        model_version="ratings-2.0",
        skipped_components=() if power is not None else ("power",),
    )


def _persist(db, result):
    return persist_batter_ratings2(
        db,
        result,
        season=2026,
        data_start_date=START,
        data_end_date=END,
    )


def test_persiste_shape_batter_y_es_idempotente(db):
    first = _persist(db, _result())
    assert first.status == "CREATED"
    row = db.query(PlayerRatings).filter_by(role="BATTER").one()
    assert (
        row.contact_rating,
        row.power_rating,
        row.vision_rating,
        row.clutch_rating,
        row.overall_rating,
    ) == (56, 68, 66, 70, 64)
    assert (
        row.velocity_rating,
        row.control_rating,
        row.movement_rating,
        row.stuff_rating,
    ) == (None, None, None, None)
    assert row.rating_model_version == "ratings-2.0"
    assert row.distribution_version == "dist-1.0"

    second = _persist(db, _result())
    assert second.status == "UNCHANGED"
    assert second.player_ratings_id == first.player_ratings_id
    assert second.input_hash == first.input_hash


@pytest.mark.parametrize(
    "changed",
    [
        _result(contact_observed=0.65),
        _result(distribution_id="rebuilt-distribution"),
        _result(clutch_source="SITUATIONAL_MODEL_TEST"),
    ],
    ids=("stat", "distribution-provenance", "clutch-provenance"),
)
def test_inputs_efectivos_actualizan_aunque_el_rating_no_cambie(db, changed):
    first = _persist(db, _result())
    updated = _persist(db, changed)
    assert updated.status == "UPDATED"
    assert updated.player_ratings_id == first.player_ratings_id
    assert updated.input_hash != first.input_hash
    assert db.query(PlayerRatings).filter_by(role="BATTER").count() == 1


def test_resultado_incompleto_no_crea_player_ratings(db):
    persisted = _persist(db, _result(power=None))
    assert persisted.status == "SKIPPED_INCOMPLETE"
    assert persisted.skipped_components == ("power",)
    assert db.query(PlayerRatings).count() == 0


def test_twp_conserva_ratings_de_pitcher_independientes(db):
    player = db.query(Player).filter_by(mlb_id=660271).one()
    pitcher = PlayerRatings(
        player_id=player.id,
        season=2026,
        role="PITCHER",
        rating_model_version="ratings-2.0",
        distribution_version="dist-1.0",
        data_start_date=START,
        data_end_date=END,
        velocity_rating=71,
        control_rating=71,
        movement_rating=77,
        stuff_rating=79,
        overall_rating=75,
        input_hash="p" * 64,
    )
    db.add(pitcher)
    db.commit()

    assert _persist(db, _result()).status == "CREATED"
    assert db.query(PlayerRatings).count() == 2
    db.refresh(pitcher)
    assert pitcher.input_hash == "p" * 64
    assert pitcher.overall_rating == 75
