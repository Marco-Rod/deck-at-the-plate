"""Pruebas del batch tolerante a fallos de pitcher ratings-2.0."""

import datetime as dt
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import PitcherSeasonStats, Player, PlayerSeason
from etl.services.pitcher_ratings2_population import (
    generate_pitcher_ratings2_population,
    select_pitcher_ratings2_population,
)


START = dt.date(2026, 8, 25)
END = dt.date(2026, 9, 2)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    for mlb_id in (101, 102, 103):
        player = Player(mlb_id=mlb_id, full_name=f"Pitcher {mlb_id}", primary_position="P")
        session.add(player)
        session.flush()
        snapshot = PlayerSeason(
            player_id=player.id,
            season=2026,
            data_start_date=START,
            data_end_date=END,
        )
        session.add(snapshot)
        session.flush()
        session.add(PitcherSeasonStats(player_season_id=snapshot.id))
    # No debe seleccionarse: existe PlayerSeason pero no Analytics pitcher.
    extra = Player(mlb_id=104, full_name="No Analytics", primary_position="P")
    session.add(extra)
    session.flush()
    session.add(PlayerSeason(
        player_id=extra.id,
        season=2026,
        data_start_date=START,
        data_end_date=END,
    ))
    session.commit()
    yield session
    session.close()
    engine.dispose()


def _component(rating):
    return SimpleNamespace(rating=rating, distribution_version="dist-1.0")


def _calculator(_db, *, mlb_id, **_kwargs):
    if mlb_id == 103:
        raise RuntimeError("unexpected calculator failure")
    rating = None if mlb_id == 102 else 75
    return SimpleNamespace(
        velocity=_component(rating),
        control=_component(rating),
        movement=_component(rating),
        stuff=_component(rating),
        overall=rating,
    )


def test_created_incomplete_failed_y_segunda_corrida_unchanged(db):
    persisted_ids = set()

    def persister(_db, ratings, **_kwargs):
        identity = id(ratings)
        status = "UNCHANGED" if persisted_ids else "CREATED"
        persisted_ids.add(identity)
        return SimpleNamespace(status=status)

    first = generate_pitcher_ratings2_population(
        db,
        season=2026,
        data_start_date=START,
        data_end_date=END,
        calculator=_calculator,
        persister=persister,
    )
    assert (first.selected, first.completed) == (3, 1)
    assert (first.created, first.updated, first.unchanged) == (1, 0, 0)
    assert (first.skipped_incomplete, first.failed) == (1, 1)
    assert first.failures[0].mlb_id == 103

    second = generate_pitcher_ratings2_population(
        db,
        season=2026,
        data_start_date=START,
        data_end_date=END,
        calculator=_calculator,
        persister=persister,
    )
    assert (second.selected, second.completed) == (3, 1)
    assert (second.created, second.updated, second.unchanged) == (0, 0, 1)
    assert (second.skipped_incomplete, second.failed) == (1, 1)


def test_selector_usa_snapshot_exacto_y_limit_opcional(db):
    assert [row.mlb_id for row in select_pitcher_ratings2_population(
        db, season=2026, data_start_date=START, data_end_date=END
    )] == [101, 102, 103]
    assert [row.mlb_id for row in select_pitcher_ratings2_population(
        db, season=2026, data_start_date=START, data_end_date=END, limit=2
    )] == [101, 102]
    with pytest.raises(ValueError, match="mayor que cero"):
        select_pitcher_ratings2_population(
            db, season=2026, data_start_date=START, data_end_date=END, limit=0
        )
